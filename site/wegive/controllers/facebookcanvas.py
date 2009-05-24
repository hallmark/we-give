# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""
Handles requests to the We Give Facebook application's canvas pages.

Canvas pages are the app's pages on Facebook that a user visits to send gifts,
view sent or received gifts, and find help.
"""
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from pylons import config, app_globals

from facebook import FacebookError
from facebook.wsgi import facebook

import fpys
import uuid

from wegive.lib.base import BaseController, render
#from wegive import model

AWS_KEY_ID = config['AWS_KEY_ID']
AWS_SECRET_KEY = config['AWS_SECRET_KEY']

log = logging.getLogger(__name__)

def log_fb_request(req):
    buf = 'Facebook request ==============='
    buf += '\nrequest.url:\t%s\n'%req.url
    buf += '\nHeaders -----\n'
    for key,value in req.headers.items():
        buf += '%s: %r\n'%(key, value)
    buf += '\nGET params -----\n'
    for key,value in req.GET.items():
        buf += '%s: %r\n'%(key, value)
    buf += '\nPOST params -----\n'
    for key,value in req.POST.items():
        buf += '%s: %r\n'%(key, value)
    log.debug(buf)

class FacebookcanvasController(BaseController):
    
    def __init__(self):
        self.fps_client = app_globals.fps_client
    
    def __before__(self):
        c.facebook = facebook

    #@template('facebook/index')
    def index(self):
        log_fb_request(request)
        
        """
        result = 'Facebook request ==============='
        result += '\nrequest.url:\t%s\n'%request.url
        result += '\nHeaders -----\n'
        for key,value in request.headers.items():
            result += '%s: %r\n'%(key, value)
        result += '\nPOST params -----\n'
        for key,value in request.POST.items():
            result += '%s: %r\n'%(key, value)
        log.debug(result)
        """
        
        
        """
        if facebook.uid:
            log.debug('uid: %s' % facebook.uid)
        
        if facebook.check_session():
            log.debug('check_session is true')
        elif facebook.canvas_user:
            log.debug('canvas_user: %s' % facebook.canvas_user)
            current_user = facebook.canvas_user
            info = facebook.users.getInfo([facebook.canvas_user], ['name', 'pic_square', 'locale'])[0]
            log.debug('name: %s, pic: %s, locale: %s' % (info['name'], info['pic_square'], info['locale']) )
            friends = facebook.friends.get(uid=facebook.canvas_user)
            friends = facebook.users.getInfo(friends, ['uid', 'name', 'pic_square', 'locale'])
            for friend in friends:
                log.debug('friend (%r): %s' % (friend['uid'], friend['name']) )
        else:
            log.debug('about to getSession...')
            facebook.auth.getSession()
            log.debug('...done with getSession.')
            
        if facebook.uid:
            log.debug('uid: %s' % facebook.uid)
            current_user = facebook.uid
        """
        
        #
        # TODOs for canvas page:
        #  - if not added, show message: "To send a gift, add this application"
        #  - if not added but received gift(s), show gifts and message "Add application and to profile to display gifts"
        #  - if added, and there are pending gifts, show these
        #
        
        current_user = None
        facebook.process_request()
        if facebook.user:
            log.debug('user: %s' % facebook.user)
            current_user = facebook.user
        elif facebook.canvas_user:
            log.debug('canvas_user: %s' % facebook.canvas_user)
            current_user = facebook.canvas_user
        
        if current_user:
            # TODO: need to handle "URLError: urlopen error" exceptions thrown from api calls
            info = facebook.api_client.users.getInfo([current_user], ['name', 'first_name', 'last_name', 'pic_square', 'locale'])[0]
            log.debug('name: %s, pic: %s, locale: %s' % (info['name'], info['pic_square'], info['locale']) )
            friends = facebook.api_client.friends.get(uid=current_user)
            friends = facebook.api_client.users.getInfo(friends, ['uid', 'name', 'pic_square', 'locale'])
            c.friends = friends
            
            # look up current_user in UserPersona table
            # if exists:
            #   - update 'added_wg' status?
            # if not exists:
            #   - add new row in User table (even if it ends up being a dummy)
            #   - add new row (network_user_id, added_wg)
            #
            # TODO: we cannot store the first_name, last_name - the user needs to provide it to us
            # TODO: need a way to map existing Users to Facebook users
            
            self._update_user_fbml_by_fbid(current_user)
        
        from wegive.model import meta, Gift, Charity
        
        # query DB for list of gifts
        session = meta.Session()
        c.gifts = session.query(Gift).filter_by(for_sale=True).order_by(Gift.created)[:24]
        
        c.charities = session.query(Charity).order_by(Charity.created)
        
        # URL for a gift:
        # images.wegivetofriends.org/dev/gifts/[id].png
        
        # for (offset, item) in enumerate(c.gifts):
        #    do something on item and offset
        # or: list comprehension: [c * i for (i, c) in enumerate(c.gifts)]
        
        return render('/facebook/index.tmpl')

    def _update_user_fbml_by_fbid(self, fb_uid):
        # TODO: get total number of gifts and enough recent gifts to fill up all the profile boxes
        
        skinny_content = '<fb:subtitle><a href="http://apps.facebook.com/test-we-give/allgifts?uid=">1 gift</a><fb:action href="http://apps.facebook.com/test-we-give/">Give to a Friend</fb:action></fb:subtitle>subtitled profile content'
        
        boxes_content = '<fb:wide>Wide content</fb:wide><fb:narrow>Narrow content</fb:narrow><br>Common content here.'
        
        set_fbml_res = facebook.api_client.profile.setFBML(uid=fb_uid, profile_main=skinny_content, profile=boxes_content)
        log.debug('setFBML response: ' + repr(set_fbml_res))
        
    def send_gift(self):
        log_fb_request(request)
        facebook.process_request()
        
        # validate
        c.recipient_id = request.POST.get('friend_selector_id')
        if c.recipient_id:
            recipient_info = facebook.api_client.users.getInfo([c.recipient_id], ['name', 'pic_square', 'locale'])[0]
            log.debug('recipient name: %s, pic: %s, locale: %s' % (recipient_info['name'], recipient_info['pic_square'], recipient_info['locale']) )
                
        from wegive.model import meta, Charity
        session = meta.Session()
        
        charity_id = request.params.get('charity_val')
        charity = session.query(Charity).filter_by(id=charity_id).one()
        c.charity_name = charity.name
        
        # compute parameters for request to Co-Branded FPS pages
        
        
        # save (pending) donation info to DB or session or memcache or something
        # TODO
        c.donation_id = 5
        c.donation_amt = request.params.get('amount','1.00')
        c.fps_url = 'https://authorize.payments-sandbox.amazon.com/cobranded-ui/actions/start'
        #c.fps_url = 'http://dev.wegivetofriends.org:8092/mock_fps'
        
        
        parameters = {'callerReference': "fpys_caller_" + uuid.uuid1().hex,
                      'paymentReason': "gift 5",
                      'transactionAmount': c.donation_amt,
                      'callerKey': AWS_KEY_ID,
                      'pipelineName': 'SingleUse',
                      'returnURL': 'http://apps.facebook.com/test-we-give/wrap_it_up'
                      }
        
        c.aws_key = AWS_KEY_ID
        c.fps_caller_ref = parameters['callerReference']
        c.fps_pymt_reason = parameters['paymentReason']
        c.fps_trans_amt = parameters['transactionAmount']
        c.fps_pipeline_name = parameters['pipelineName']
        c.fps_return_url = parameters['returnURL']
        #c.fps_version = parameters['version']
        

        c.aws_sig = self.fps_client.get_pipeline_signature(parameters)
        
        c.direct_url = self.fps_client.getPipelineUrl(parameters['callerReference'],
                                                      parameters['paymentReason'],
                                                      parameters['transactionAmount'],
                                                      parameters['returnURL'])
        log.debug("\nCBUI URL -----\n" + c.direct_url + "\n")
        
        # render page template for user to click 'Continue with donation'
        
        #c.error_msg = 'Charity not found'
        return render('/facebook/send_gift.tmpl')

    def wrap_it_up(self):
        log_fb_request(request)
        facebook.process_request()
        
        parameters = request.GET.copy()
        
        # verify CBUI return signature
        if 'awsSignature' in parameters:
            sig = parameters['awsSignature']
            log.debug("using params['awsSignature'] for FPS sig")
        elif 'signature' in parameters:
            sig = parameters['signature']
            log.debug("using params['signature'] for FPS sig")
            del parameters['signature']
            parameters['awsSignature'] = sig
        else:
            log.debug("FPS signature not found")
            return("signature not found")
        
        log.debug('FPS sig: ' + sig);
        
        if not self.fps_client.validate_pipeline_signature(sig, None, parameters):
            return("invalid signature")
        
        if not parameters.get('status') in ['SA', 'SB', 'SC']:
            return("status not success")
        
        return render('/facebook/wrap_it_up.tmpl')

    def received(self):
        c.received_gifts = {}
        
        return render('/facebook/received.tmpl')

    def sent(self):
        c.sent_gifts = {}
        
        return render('/facebook/sent.tmpl')

    def mission(self):
        
        return render('/facebook/mission.tmpl')

    def help(self):
        
        return render('/facebook/help.tmpl')
    