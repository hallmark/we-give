# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""Facebook logic

Consists of logic that handles interaction with the Facebook Platform.
"""
import logging
from pylons import config
from paste.deploy.converters import asint

from facebook.wsgi import facebook as fb
from facebook import FacebookError
import simplejson

import wegive.lib.helpers as h
import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona, SocialNetwork, Transaction
import wegive.logic.user as user_logic

CANVAS_URL = config['fbapp_canvas_url']
TEMPLATE_BUNDLE_ID = asint(config['sent_gift_template_bundle_id'])

log = logging.getLogger(__name__)

def has_profile_fbml(fb_uid):
    """Check if a Facebook user already has FBML for the profile boxes"""
    # TODO: retry, e.g., for URLError: <urlopen error (54, 'Connection reset by peer')>
    try:
        fbml = fb.api_client.profile.getFBML(fb_uid, type=2)  # types: 1 = original style, 2 = profile_main
        #log.debug('getFBML response: ' + fbml)
    except FacebookError, err:
        if int(err.code) != 1:
            log.debug('Unexpected error code for getFBML: ' + str(err))
        return False
    return True

def update_user_fbml_by_userpersona(userpersona):
    facebook_uid = userpersona.network_user_id
    wg_user = userpersona.user
    
    _update_user_fbml(facebook_uid, wg_user)

def update_user_fbml_by_wg_userid(user_id):
    network = meta.Session.query(SocialNetwork).filter_by(name=u'Facebook').one()
    userpersona_q = meta.Session.query(UserPersona)
    fb_userpersona = userpersona_q.filter_by(network_id=network.id).filter_by(wg_user_id=user_id).first()
    
    if fb_userpersona:
        _update_user_fbml(fb_userpersona.network_user_id, fb_userpersona.user)
    else:
        log.error('update_user_fbml_by_wg_userid: cannot find Facebook UserPersona for user_id %d' % user_id)


def _update_user_fbml(facebook_uid, wg_user):
    received_gifts = user_logic.decorate_with_fb_uid(wg_user.received_gifts, 'donor_id')
    gift_count = len(received_gifts)
    
    if gift_count == 0:
        skinny_content = '<fb:ref handle="profileCommonStyles" /><fb:subtitle>&nbsp;<fb:action href="%s/">Give to a Friend</fb:action></fb:subtitle><div class="no_items">No gifts yet.</div>' % CANVAS_URL
        boxes_content = skinny_content
    else:
        top_gifts = received_gifts[:8]
        
        subtitle_fbml = '<fb:ref handle="profileCommonStyles" /><fb:subtitle><a href="%s/allgifts?uid=%d">%s</a><fb:action href="%s/">Give to a Friend</fb:action></fb:subtitle>' % (CANVAS_URL, facebook_uid, h.plural(gift_count, 'gift', 'gifts'), CANVAS_URL)
        
        gifts_buf = []
        for idx, donation in enumerate(top_gifts):
            if idx == 4:
                gifts_buf.append('<fb:wide>')
            gifts_buf.append('<div class="gift_box"><div class="gift_img"><a href="%s/gift?id=%d" title="%s"><img src="' % (CANVAS_URL, donation.id, donation.gift.name))
            gifts_buf.append(h.gift_image_url(donation.gift_id))
            gifts_buf.append('"></a></div><div class="gift_caption"><span class="caption_from">From:</span> <span class="caption_name"><fb:name uid="%s" firstnameonly="true" useyou="false" ifcantsee="Anon" /></span></div></div>' % donation.fb_uid)
            if idx < 4 and idx % 2 == 1:
                gifts_buf.append('<fb:narrow><div style="height: 1px; font-size: 1px; clear: both;">&nbsp;</div></fb:narrow>')
            if idx % 4 == 3:
                gifts_buf.append('<fb:wide><div style="height: 1px; font-size: 1px; clear: both;">&nbsp;</div></fb:wide>')
        if len(top_gifts) > 4:
            gifts_buf.append('</fb:wide>')
        
        gifts_fbml = ''.join(gifts_buf)
        
        skinny_content = subtitle_fbml + gifts_fbml
        boxes_content = subtitle_fbml + gifts_fbml
        #boxes_content = '<fb:wide>Wide content</fb:wide><fb:narrow>Narrow content</fb:narrow><br>Common content here.'
        #log.debug(boxes_content)
    
    try:
        set_fbml_res = fb.api_client.profile.setFBML(uid=facebook_uid, profile_main=skinny_content, profile=boxes_content)
        log.debug('setFBML response: ' + repr(set_fbml_res))
    except FacebookError, err:
        log.debug('Unexpected error calling facebook.setFBML: ' + str(err))

def publish_feed_item(donor_id, recipient_id, donation_id, gift_name, charity_name):
    data = '''{"gifthref":"%s/gift?id=%d",
               "sendhref":"%s/",
               "gift":"%s",
               "charity":"%s",
               "comments_xid":"wg-gift.%d"}''' % (CANVAS_URL, donation_id,
                                                  CANVAS_URL, gift_name.lower(),
                                                  charity_name, donation_id)
    try:
        log.debug('About to call feed.publishUserAction for donation %d.' % donation_id)
        publish_user_action_res = fb.api_client.feed.publishUserAction(template_bundle_id=TEMPLATE_BUNDLE_ID,
                                                                       template_data=data,
                                                                       target_ids=[recipient_id])
        log.debug('publishUserAction response: %r' % publish_user_action_res)
    except FacebookError, err:
        log.debug('Unexpected error calling feed.publishUserAction: ' + str(err))

def publish_stream_item(donor_id, recipient_id, donation):
    charity_name = donation.charity.name
    
    gifthref = "%s/gift?id=%d" % (CANVAS_URL, donation.id)
    if donation.stream_short_msg is None:
        message = 'Here is a meaningful gift.'
    else:
        message = donation.stream_short_msg
    
    properties = {}
    properties['Charity'] = {'text':charity_name, 'href':donation.charity.url}
    
    media = []
    giftimage = {}
    giftimage['type'] = 'image'
    giftimage['src'] = h.gift_image_url(donation.gift_id)
    giftimage['href'] = gifthref
    media.append(giftimage)
    
    attachment = {}
    attachment['name'] = donation.gift.name
    attachment['href'] = gifthref
    attachment['caption'] = 'This donation gift benefits %s.' % charity_name
    attachment['comments_xid'] = 'wg-gift.%d' % donation.id
    attachment['properties'] = properties
    attachment['media'] = media
    
    action_links = []
    send_gift_link = {}
    send_gift_link['text'] = 'Send a gift'
    send_gift_link['href'] = "%s/" % CANVAS_URL
    action_links.append(send_gift_link)
    
    log.debug('Publishing message to stream: %s' % message)
    
    try:
        stream_publish_res = fb.api_client.stream.publish(message=message,
                                                          action_links=simplejson.dumps(action_links),
                                                          attachment=simplejson.dumps(attachment),
                                                          target_id=recipient_id)
        log.debug('Stream.publish response: %r' % stream_publish_res)
        return stream_publish_res
    except FacebookError, err:
        log.debug('Unexpected error calling facebook Stream.publish: ' + str(err))
        return None
    
    
def set_ref_handle(handle, fbml):
    try:
        set_ref_res = fb.api_client.fbml.setRefHandle(handle=handle, fbml=fbml)
        log.debug('setFBML response: ' + repr(set_ref_res))
    except FacebookError, err:
        log.debug('Unexpected error calling facebook.setRefHandle: ' + str(err))
