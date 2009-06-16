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
from pylons import config, app_globals as g
from paste.deploy.converters import asbool

from facebook import FacebookError
from facebook.wsgi import facebook

import uuid
import time

from wegive.lib.base import BaseController, render
import wegive.lib.helpers as h
import wegive.model as model
import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona, SocialNetwork, Transaction
import wegive.logic.facebook_platform as fb_logic
import wegive.logic.payments as fps_logic
import wegive.logic.user as user_logic

FPS_PROMO_ACTIVE = asbool(config['fps_free_processing_promo_is_active'])

log = logging.getLogger(__name__)
payment_log = logging.getLogger('payment-processing-event')

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
#
def log_payment_event(type, message, donation_id=None, transaction_id=None, caller_ref=None, fps_transaction_id=None, request_id=None, new_status=None):
    content = '%-4.4s %s %s %s %s %s %s "%s"' % (type, (donation_id or '-'), (transaction_id or '-'),
                                              (caller_ref or '-'), (fps_transaction_id or '-'), (request_id or '-'),
                                              (new_status or '-'), message)
    payment_log.info(content)
    log.debug(content)

class FacebookcanvasController(BaseController):
    
    def __init__(self):
        self.fps_client = g.fps_client
    
    def __before__(self):
        c.facebook = facebook
        c.canvas_url = config['fbapp_canvas_url']

    #@template('facebook/index')
    def index(self):
        realstart = start = time.time()
        
        log_fb_request(request)
        log.debug('time to log request: %.3f ms' % ((time.time() - start)*1000.0))
        
        #
        # TODOs for canvas page:
        #  - if not added, show message: "To send a gift, add this application"
        #  - if not added but received gift(s), show gifts and message "Add application and to profile to display gifts"
        #  - if added, and there are pending gifts, show these
        #
        
        current_user = None
        start = time.time()
        facebook.process_request()
        log.debug('time to do facebook.process_request(): %.3f ms' % ((time.time() - start)*1000.0))
        c.is_app_user = facebook.api_client.added
        if facebook.user:
            log.debug('user: %s' % facebook.user)
            current_user = facebook.user
        elif facebook.canvas_user:
            log.debug('canvas_user: %s' % facebook.canvas_user)
            current_user = facebook.canvas_user

        c.just_installed = (request.GET.get('installed') == '1')
        c.gift_count = None
        
        if current_user:
            start = time.time()

            """ Removing unnecessary Facebook API calls
            # TODO: need to handle "URLError: urlopen error" exceptions thrown from api calls
            info = facebook.api_client.users.getInfo([current_user], ['name', 'first_name', 'last_name', 'pic_square', 'locale'])[0]
            log.debug('name: %s, pic: %s, locale: %s' % (info['name'], info['pic_square'], info['locale']) )
            friends = facebook.api_client.friends.get(uid=current_user)
            friends = facebook.api_client.users.getInfo(friends, ['uid', 'name', 'pic_square', 'locale'])
            c.friends = friends
            log.debug('time to make facebook API calls: %.3f ms' % ((time.time() - start)*1000.0))
            """
            
            # TODO: we cannot store the first_name, last_name - the user needs to provide it to us
            # TODO: need a way to map existing Users to Facebook users
            
            start = time.time()
            session = meta.Session()
            
            # Look up current_user in UserPersona table
            #   if exists:
            #     - update 'is_app_user' status?
            #   if not exists:
            #     - add new row in User table (even if it ends up being a dummy)
            #     - add new row in UserPersona table
            fb_user = user_logic.get_fb_userpersona(session, current_user, create_if_missing=True)
            
            # update is_app_user if persisted value is inaccurate
            if fb_user.is_app_user != facebook.api_client.added:
                fb_user.is_app_user = facebook.api_client.added

            session.flush()
            
            if c.just_installed:
                c.gift_count = len(fb_user.user.received_gifts)
            
                fbml_start = time.time()
                if fb_user.is_app_user and not fb_logic.has_profile_fbml(current_user):
                    ALLOW_FBML_INIT_ON_FIRST_VISIT = True
                    if ALLOW_FBML_INIT_ON_FIRST_VISIT:
                        fb_logic.update_user_fbml_by_userpersona(fb_user)
                    else:
                        log.debug("Updating profile FBML on canvas-page views is currently de-fanged, so that I can properly test handling users w/o FBML!")
            
                log.debug('time for has_profile_fbml call: %.3f ms' % ((time.time() - fbml_start)*1000.0))
            
            # will commit new user if call to get_fb_userpersona added row
            session.commit()
        
        # query DB for list of gifts
        gifts_mkey = 'Cols.gifts-page1'
        mc_start = time.time()
        gifts = g.mc.get(gifts_mkey)
        log.debug('time for memcached calls: %.3f ms' % ((time.time() - mc_start)*1000.0))
        if gifts:
            log.debug('got gifts from memcached!')
            c.gifts = gifts
        else:
            gift_q = meta.Session.query(Gift)
            c.gifts = gift_q.filter_by(for_sale=True).order_by(Gift.created)[:15]
            g.mc.set(gifts_mkey, c.gifts, time=86400)
            log.debug('stored gifts in memcached!')
        
        # get list of charities that have registered thru CBUI as payment recipients
        charities_mkey = 'Cols.active-charities'
        mc_start = time.time()
        charities = g.mc.get(charities_mkey)
        log.debug('time for memcached calls: %.3f ms' % ((time.time() - mc_start)*1000.0))
        if charities:
            log.debug('got charities from memcached!')
            c.charities = charities
        else:
            charity_q = meta.Session.query(Charity)
            if FPS_PROMO_ACTIVE:
                c.charities = charity_q.filter(Charity.promo_recipient_token_id != None).order_by(Charity.created).all()
            else:
                c.charities = charity_q.filter(Charity.recipient_token_id != None).order_by(Charity.created).all()
            g.mc.set(charities_mkey, c.charities, time=86400)
            log.debug('stored charities in memcached!')
        
        log.debug('time for all DB calls: %.3f ms' % ((time.time() - start)*1000.0))
        
        c.form_uuid = uuid.uuid1().hex
        
        # for (offset, item) in enumerate(c.gifts):
        #    do something on item and offset
        # or: list comprehension: [c * i for (i, c) in enumerate(c.gifts)]
        
        log.debug('total time: %.3f ms' % ((time.time() - realstart)*1000.0))
        
        return render('/facebook/index.tmpl')

    def send_gift(self):
        """Render gift preview for user to review and then click 'Continue with donation'"""
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        if not c.is_app_user:
            c.error_msg = 'You need to add this app before you can send gifts.'
            return render('/facebook/send_gift.tmpl')
        
        current_user = facebook.user
        if not current_user:
            c.error_msg = 'Error getting your user info.'
            return render('/facebook/send_gift.tmpl')
        
        session = meta.Session()
        
        fb_user = user_logic.get_fb_userpersona(session, current_user)
        if fb_user is None:
            # TODO: make sure use has added app
            # TODO: make sure user exists
            
            c.error_msg = 'You need to add this app before you can send gifts.'
            return render('/facebook/send_gift.tmpl')
        
        # validate
        c.recipient_id = request.POST.get('friend_selector_id')
        charity_id = request.params.get('charity_val')
        gift_id = request.params.get('gift_id')
        c.message = request.params.get('message')
        c.donation_amt = request.params.get('amount','1.00')
        
        form_uuid = request.params.get('uuid')
        # TODO: store & lookup uuid in memcached, to see if user is resubmitting form.  at least log the UUID.

        if c.recipient_id:
            recipient_info = facebook.api_client.users.getInfo([c.recipient_id], ['name', 'pic_square', 'locale'])[0]
            log.debug('recipient name: %s, pic: %s, locale: %s' % (recipient_info['name'], recipient_info['pic_square'], recipient_info['locale']) )
            
            recipient_userpersona = user_logic.get_fb_userpersona(session, c.recipient_id, create_if_missing=True)
        
        gift_q = meta.Session.query(Gift)
        charity_q = meta.Session.query(Charity)

        charity = charity_q.get(charity_id)
        if charity is None:
            c.error_msg = 'Charity not found'
            return render('/facebook/send_gift.tmpl')
        c.charity_name = charity.name
        
        c.gift = gift_q.get(gift_id)
        
        # save (pending) donation info to DB or session or memcache or something
        donation = Donation(fb_user.user.id, recipient_userpersona.user.id, float(c.donation_amt), gift_id, charity_id)
        donation.message = c.message
        session.add(donation)
        session.flush()
        
        # TODO: to prevent form resubmission, commit, then redirect to review_gift page with donation ID??
        
        # compute parameters for request to Co-Branded FPS pages
        caller_ref = 'wgdonation_%d_%s' % (donation.id, uuid.uuid1().hex)
        reason = 'Donation to %s' % charity.name
        if FPS_PROMO_ACTIVE:
            recipient_token = charity.promo_recipient_token_id
        else:
            recipient_token = charity.recipient_token_id
        c.direct_url = fps_logic.get_cbui_url(caller_ref,
                                              reason,
                                              c.donation_amt,
                                              recipient_token=recipient_token,
                                              website_desc='We Give Facebook application')
        
        session.commit()
        log_payment_event('APP', 'Created donation', donation_id=donation.id, caller_ref=caller_ref, new_status='new')
        
        return render('/facebook/send_gift.tmpl')

    def wrap_it_up(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
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
        
        status = parameters.get('status')
        log.debug('Return status from CBUI: ' + status)
        
        if 'errorMessage' in request.GET:
            log.error('Error in return from CBUI: ' + request.GET['errorMessage'])
            c.error_msg = 'There was a problem with your payment authorization.'
            return render('/facebook/wrap_it_up.tmpl')
        
        if status == 'A':
            c.error_msg = 'You cancelled the donation.  The gift will not be sent.'
            return render('/facebook/wrap_it_up.tmpl')
        
        if not status in ['SA', 'SB', 'SC']:
            return("status not success")
        
        session = meta.Session()
        
        caller_reference = request.params.get('callerReference')
        donation_id = int(caller_reference.split('_')[1])
        donation = meta.Session.query(Donation).get(donation_id)
        if donation is None:
            log.error('Error in return from CBUI: donation information could not be found')
            log_payment_event('CBUI', 'Donation information could not be found', donation_id=donation_id, caller_ref=caller_reference, new_status='error')
            
            c.error_msg = 'Gift information could not be found.'
            return render('/facebook/wrap_it_up.tmpl')
        
        # Check if donation already has an associated transaction.  TODO: make sure it's a 'Pay' transaction?
        # This may be the case if a user refreshes the page or revisits it using the Back button
        if len(donation.transactions) != 0:
            log.debug('Found %d existing transactions for donation %d.' % (len(donation.transactions), donation.id))
            
            # retrieve the last transaction created
            transaction = donation.transactions[-1]
            log.debug('Last transaction for donation %d:\n%d\t%s\t%s\n%s\t%s\t%s' % (donation.id, transaction.id, transaction.fps_action, transaction.caller_reference, transaction.fps_transaction_id, transaction.fps_transaction_status, transaction.fps_status_code))
            
            c.donation = donation
            c.recipient_fb_uid = user_logic.get_network_uid(session, donation.recipient_id)
            c.payment_method = transaction.payment_method
            c.pay_status = transaction.fps_transaction_status

            return render('/facebook/wrap_it_up.tmpl')
            
        transaction = Transaction('Pay',donation.id, caller_reference)
        transaction.amount = donation.amount
        if FPS_PROMO_ACTIVE:
            transaction.recipient_token_id = donation.charity.promo_recipient_token_id
        else:
            transaction.recipient_token_id = donation.charity.recipient_token_id
        transaction.sender_token_id = request.params.get('tokenID')
        transaction.payment_method = {'SA':'ABT', 'SB':'ACH', 'SC':'CC'}[status]
        session.add(transaction)
        
        session.flush()
        donation.transaction_id = transaction.id
        log_payment_event('CBUI', 'Return from Co-branded pipeline; Created transaction', donation_id=donation.id, transaction_id=transaction.id, caller_ref=caller_reference, new_status='pending')
        
        # invoke Pay operation on Amazon FPS
        fps_response = fps_logic.pay_marketplace(transaction.sender_token_id,
                                                 transaction.recipient_token_id,
                                                 transaction.amount,
                                                 caller_reference,
                                                 charge_caller=True)

        # detect error response
        if hasattr(fps_response, 'errors'):
            fps_error = fps_response.errors.error
            log.debug("Error from FPS action 'Pay'\nCallerReference: %s\nRequestID: %s\nCode: %s\nMessage: %s" % (caller_reference,fps_response.requestID, fps_error.code, fps_error.message))
            # TODO: depending on whether this condition can be retried, display error to end-user
            # TODO: update transaction and donation entries?
            log_payment_event('FPS', "Error from FPS action 'Pay': [%s] %s" % (fps_error.code, fps_error.message), donation_id=donation.id, transaction_id=transaction.id, caller_ref=caller_reference, request_id=fps_response.requestID, new_status='failed')
            c.error_msg = 'Payment authorization was not successful.'
            return render('/facebook/wrap_it_up.tmpl')
        
        #log.debug("fps response dir: " + str(dir(fps_response)))
        transaction.fps_transaction_id = fps_response.payResult.transactionId
        transaction.fps_transaction_status = fps_response.payResult.transactionStatus
        request_id = fps_response.responseMetadata.requestId
        log.debug("Pay transaction status: %s, RequestID: %s" % (transaction.fps_transaction_status, request_id))
        log_payment_event('FPS', "Invoked FPS action 'Pay'", donation_id=donation.id, transaction_id=transaction.id, caller_ref=caller_reference, fps_transaction_id=transaction.fps_transaction_id, request_id=request_id, new_status=transaction.fps_transaction_status)
        
        if transaction.fps_transaction_status == 'Success':
            transaction.success_date = model.now()
            donation.transaction_status = 'paid'
        elif transaction.fps_transaction_status == 'Pending':
            transaction.last_attempt_date = model.now()
            donation.transaction_status = 'pending'
        elif transaction.fps_transaction_status == 'Failure':
            # TODO: handle more stuff here??
            donation.transaction_status = 'failed'
        
        # If 'Pay' operation succeeded, update donation and user profile FBML
        # This should only happen for Amazon balance transfers (ABT).  Other
        # payment methods require verification and start in 'Pending' status.
        if transaction.fps_transaction_status == 'Success':
            donation.delivered = True
            donation.transaction_status = 'paid'
            session.flush()
            fb_logic.update_user_fbml_by_wg_userid(donation.recipient_id)
        
        session.commit()
        
        c.donation = donation
        c.recipient_fb_uid = user_logic.get_network_uid(session, donation.recipient_id)
        c.payment_method = transaction.payment_method
        c.pay_status = transaction.fps_transaction_status
        
        donor_fb_uid = user_logic.get_network_uid(session, donation.donor_id)
        fb_logic.publish_feed_item(donor_fb_uid, c.recipient_fb_uid, donation.id, donation.gift.name, donation.charity.name)
        
        return render('/facebook/wrap_it_up.tmpl')

    def invite_sent(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        c.invitee_uid = request.params.get('invitee')
        return render('/facebook/invite_sent.tmpl')

    def allgifts(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        c.recipient_id = request.params.get('uid')
        if not c.recipient_id:
            c.error_msg = 'No user specified'
            return(c.error_msg)
        
        session = meta.Session()
        
        fb_user = user_logic.get_fb_userpersona(session, c.recipient_id)
        if fb_user is None or fb_user.user is None:
            c.error_msg = 'Unable to retrieve user of gifts.'
            return(c.error_msg)
        
        # TODO: add clause for privacy if viewer is also subject
        c.received_gifts = user_logic.decorate_with_fb_uid(fb_user.user.received_gifts, 'donor_id')
        
        if c.recipient_id == facebook.user:
            return render('/facebook/received.tmpl')
        else:
            return render('/facebook/allgifts.tmpl')

    def received(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        if not c.is_app_user:
            c.error_msg = 'You must authorize We Give before you can view your received gifts.'
            return(c.error_msg)
        
        current_user = facebook.user
        if not current_user:
            c.error_msg = 'Error getting your user info.'
            return(c.error_msg)
        
        session = meta.Session()
        
        fb_user = user_logic.get_fb_userpersona(session, current_user)
        if fb_user is None or fb_user.user is None:
            c.error_msg = 'You need to authorize the We Give app before you can view your received gifts.'
            return(c.error_msg)
        
        c.received_gifts = user_logic.decorate_with_fb_uid(fb_user.user.received_gifts, 'donor_id')
        
        return render('/facebook/received.tmpl')

    def sent(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        if not c.is_app_user:
            c.error_msg = 'You must authorize We Give before you can view your sent gifts.'
            return(c.error_msg)
        
        current_user = facebook.user
        if not current_user:
            c.error_msg = 'Error getting your user info.'
            return(c.error_msg)
        
        session = meta.Session()
        
        fb_user = user_logic.get_fb_userpersona(session, current_user)
        if fb_user is None or fb_user.user is None:
            c.error_msg = 'You need to authorize the We Give app before you can view your sent gifts.'
            return(c.error_msg)
        
        c.sent_gifts = user_logic.decorate_with_fb_uid(fb_user.user.sent_gifts, 'recipient_id')
        
        return render('/facebook/sent.tmpl')

    def gift(self):
        """Display one gift donation."""
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        """
        current_user = None
        if facebook.user:
            log.debug('user: %s' % facebook.user)
            current_user = facebook.user
        elif facebook.canvas_user:
            log.debug('canvas_user: %s' % facebook.canvas_user)
            current_user = facebook.canvas_user
        
        if not facebook.api_client.added:
            c.error_msg = 'You need to add this app before you can send gifts.'
            return render('/facebook/send_gift.tmpl')
        
        current_user = facebook.user
        if not current_user:
            c.error_msg = 'Error getting your user info.'
            return render('/facebook/send_gift.tmpl')
        """
        try:
            gift_id = int(request.params.get('id'))
            
            # get the gift donation info
            c.donation = meta.Session.query(Donation).get(gift_id)
            session = meta.Session()
            c.recipient_id = user_logic.get_network_uid(session, c.donation.recipient_id)
            c.donor_id = user_logic.get_network_uid(session, c.donation.donor_id)
        except Exception, err:
            log.debug(str(err))
            c.error_msg = 'Unable to find that gift.'
        
        c.show_welcome = (c.is_app_user == False and facebook.canvas_user == unicode(c.recipient_id))
        
        return render('/facebook/gift.tmpl')

    def mission(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        return render('/facebook/mission.tmpl')

    def help(self):
        log_fb_request(request)
        facebook.process_request()
        c.is_app_user = facebook.api_client.added
        
        return render('/facebook/help.tmpl')
    