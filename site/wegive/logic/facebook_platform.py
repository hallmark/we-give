# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""Facebook logic

Consists of logic that handles interaction with the Facebook Platform.
"""
import logging

from facebook.wsgi import facebook as fb
from facebook import FacebookError

import wegive.lib.helpers as h
import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona, SocialNetwork, Transaction

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
    received_gifts = wg_user.received_gifts
    gift_count = len(received_gifts)
    
    if gift_count == 0:
        skinny_content = '<style>.no_items{text-align:center; margin:10px auto;}</style><fb:subtitle>&nbsp;<fb:action href="http://apps.facebook.com/test-we-give/">Give to a Friend</fb:action></fb:subtitle><div class="no_items">No gifts yet.</div>'
        boxes_content = skinny_content
    else:
        top_gifts = received_gifts[:4]
        
        subtitle_fbml = '<style>.gift_box{width: 90px; margin:10px 5px;}</style><fb:subtitle><a href="http://apps.facebook.com/test-we-give/allgifts?uid=%d">%s</a><fb:action href="http://apps.facebook.com/test-we-give/">Give to a Friend</fb:action></fb:subtitle>' % (facebook_uid, h.plural(gift_count, 'gift', 'gifts'))
        
        gifts_buf = []
        for gift in top_gifts:
            gifts_buf.append('<div class="gift_box"><img src="')
            gifts_buf.append(h.gift_image_url(gift.gift_id))
            gifts_buf.append('"></div>')
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
