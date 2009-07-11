# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""
Handle Amazon FPS Instant Payment Notifications (IPN).
"""
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to
from pylons import config, app_globals as g

from facebook import FacebookError
from facebook.wsgi import facebook

from wegive.lib.base import BaseController, render

import wegive.model as model
import wegive.model.meta as meta
from wegive.model import Transaction
import wegive.logic.facebook_platform as fb_logic
import wegive.logic.payments as fps_logic
import wegive.logic.user as user_logic

log = logging.getLogger(__name__)
payment_log = logging.getLogger('payment-processing-event')

def log_ipn_notification(req):
    buf = '\n\n= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='
    buf += '\n=   Instant Payment Notification                              ='
    buf += '\n\nrequest.url:\t%s\n'%req.url
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

def log_payment_event(type, message, donation_id=None, transaction_id=None, caller_ref=None, fps_transaction_id=None, request_id=None, new_status=None):
    content = '%-4.4s %s %s %s %s %s %s "%s"' % (type, (donation_id or '-'), (transaction_id or '-'),
                                              (caller_ref or '-'), (fps_transaction_id or '-'), (request_id or '-'),
                                              (new_status or '-'), message)
    payment_log.info(content)
    log.debug(content)

class IpnController(BaseController):
    
    def __init__(self):
        self.fps_client = g.fps_client

    def process_ipn(self):
        log_ipn_notification(request)
        
        # verify signature
        parameters = request.POST.copy()
        
        if 'signature' in parameters:
            sig = parameters['signature']
            del parameters['signature']
        else:
            log.debug("FPS signature not found")
            return("signature not found")
        
        log.debug('FPS sig: ' + sig);
        
        if not self.fps_client.validate_pipeline_signature(sig, None, parameters):
            transaction_id = request.POST.get('transactionId')
            log_payment_event('IPN', "Invalid signature", fps_transaction_id=transaction_id, new_status='error')
            return("invalid signature")
        
        transaction_status = request.POST.get('transactionStatus')
        if transaction_status is None:
            log.error('No transactionStatus found in IPN.')
            return('transactionStatus not found')
        
        transaction_id = request.POST.get('transactionId')
        if transaction_id is None:
            log.error('No transactionId found in IPN.')
            return('transactionId not found')
        
        status_code = request.POST.get('statusCode')
        status_message = request.POST.get('statusMessage')  # logged for failures
        buyer_name = request.POST.get('buyerName')
        caller_reference = request.POST.get('callerReference')
        
        # look up transaction in DB
        session = meta.Session()
        txn_q = meta.Session.query(Transaction)
        transaction = txn_q.with_lockmode('update').filter_by(fps_transaction_id=transaction_id).first()  # TODO: use one() and catch exceptions?
        if transaction is None:
            log.error('Transaction %s could not be found in DB' % transaction_id)
            log_payment_event('IPN', "Transaction could not be found in DB", fps_transaction_id=transaction_id, new_status='error')
            # TODO: record detailed info in case DB insert was not committed before IPN was received!
            return('transaction info not found')
        
        if transaction_status.upper() == 'FAILURE' or transaction_status.upper() == 'CANCELLED':
            log_payment_event('IPN', "Notification received: %s" % status_message,
                                fps_transaction_id=transaction_id,
                                donation_id=transaction.donation.id,
                                transaction_id=transaction.id,
                                caller_ref=caller_reference,
                                new_status=status_code)
        else:
            log_payment_event('IPN', "Notification received",
                                fps_transaction_id=transaction_id,
                                donation_id=transaction.donation.id,
                                transaction_id=transaction.id,
                                caller_ref=caller_reference,
                                new_status=status_code)
        
        if transaction_status.upper() == 'PENDING':
            # if status is pending, look up transaction in DB.
            # If info in DB:
            #  - transaction cannot be found, log error
            #  - status pending, capture buyer name to DB if needed
            #  - status succeeded, IPN must be out of order, log it
            if transaction.fps_transaction_status is None:
                log.debug('Found transaction that has no value for fps_transaction_status, ID: %s' % transaction_id)
                transaction.fps_transaction_status = 'Pending'
                session.commit()
            elif transaction.fps_transaction_status == 'Pending':
                if status_code is not None:
                    transaction.fps_status_code = status_code
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
                session.commit()
            elif transaction.fps_transaction_status == 'Success':
                log.debug('Received IPN for pending status out of order - txn already succeeded.  Ignoring.')
        
        elif transaction_status.upper() == 'SUCCESS':
            # if status is success, look up transaction in DB.
            # If:
            #  - transaction is pending, update to success and deliver gift
            #  - transaction is already success, log it (duplicate notification?)
            if transaction.fps_transaction_status is None or transaction.fps_transaction_status == 'Pending':
                transaction.fps_transaction_status = 'Success'
                if status_code is not None:
                    transaction.fps_status_code = status_code
                transaction.success_date = model.now()
                transaction.donation.delivered = True
                transaction.donation.transaction_status = 'paid'
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
                fb_logic.update_user_fbml_by_wg_userid(transaction.donation.recipient_id)
                # update estimated amount in multi-use token
                fps_logic.update_multiuse_token_estimate(session,
                                                         transaction.sender_token_id,
                                                         transaction.amount)
                # stash some info for the feed entry
                donor_fb_uid = user_logic.get_network_uid(session, transaction.donation.donor_id)
                recipient_fb_uid = user_logic.get_network_uid(session, transaction.donation.recipient_id)
                donation_id = transaction.donation.id
                gift_name = transaction.donation.gift.name
                charity_name = transaction.donation.charity.name
                session.commit()
                
                # try to send feed update
                user_session_mkey = "User-fb-sk.%s" % donor_fb_uid
                session_key = g.mc.get(user_session_mkey)
                if session_key:
                    log.debug('going to publish feed item, user session: %s' % session_key)
                    # publish feed item
                    facebook.api_client.user = donor_fb_uid
                    facebook.api_client.session_key = session_key
                    fb_logic.publish_feed_item(donor_fb_uid, recipient_fb_uid,
                                               donation_id, gift_name,
                                               charity_name)
                    
                    has_publish_stream = facebook.api_client.users.hasAppPermission(ext_perm='publish_stream')
                    #log.debug('has_publish_stream: %s' % has_publish_stream)
                    if has_publish_stream == 1:
                        # publish story to recipient's Wall and to News Feeds
                        post_id = fb_logic.publish_stream_item(donor_fb_uid, recipient_fb_uid,
                                                               transaction.donation)
                        if post_id is not None:
                            transaction.donation.fb_post_id = post_id
                            session.commit()
                    else:
                        log.debug("User %s does not have 'publish_stream' permission. Not publishing to stream." % donor_fb_uid)
                else:
                    log.debug('unable to find user session key in memcached')
                
            elif transaction.fps_transaction_status == 'Success':
                log.info('Transaction %s is already in Success state. ABT payment or duplicate IPN notification?' % transaction_id)
        
        elif transaction_status.upper() == 'FAILURE':
            if transaction.fps_transaction_status is None or transaction.fps_transaction_status == 'Pending':
                # TODO: log more info?
                transaction.fps_transaction_status = 'Failure'
                transaction.donation.transaction_status = 'failed'
                if status_code is not None:
                    transaction.fps_status_code = status_code
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
                session.commit()
            elif transaction.fps_transaction_status == 'Failure' or transaction.fps_transaction_status == 'Cancelled':
                log.debug('Transaction %s is already in Failure/Cancelled state. Duplicate IPN notification?' % transaction_id)
            elif transaction.fps_transaction_status == 'Success':
                log.error('Transaction %s is in Success state.  IPN notification received for FAILURE.  Status code: %s' % (transaction_id, status_code))
        
        elif transaction_status.upper() == 'CANCELLED':
            if transaction.fps_transaction_status is None or transaction.fps_transaction_status == 'Pending':
                # TODO: log more info?
                transaction.fps_transaction_status = 'Cancelled'
                transaction.donation.transaction_status = 'cancelled'
                # TODO: do we need to "undeliver" the gift if a user cancels a payment after it went through?
                if status_code is not None:
                    transaction.fps_status_code = status_code
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
                session.commit()
            elif transaction.fps_transaction_status == 'Failure' or transaction.fps_transaction_status == 'Cancelled':
                log.debug('Transaction %s is already in Failure/Cancelled state. Duplicate IPN notification?' % transaction_id)
            elif transaction.fps_transaction_status == 'Success':
                log.error('Transaction %s is in Success state.  IPN notification received for CANCELLED.  Status code: %s' % (transaction_id, status_code))
        
        return 'roger that'
