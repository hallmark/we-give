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
from pylons import config, app_globals

from wegive.lib.base import BaseController, render

import wegive.model as model
import wegive.model.meta as meta
from wegive.model import Transaction
import wegive.logic.facebook_platform as fb_logic

log = logging.getLogger(__name__)

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

class IpnController(BaseController):
    
    def __init__(self):
        self.fps_client = app_globals.fps_client

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
            return("invalid signature")
        
        transaction_status = request.POST.get('transactionStatus')
        if transaction_status is None:
            log.error('No transactionStatus found in IPN.')
            return('transactionStatus not found')
        
        transaction_id = request.POST.get('transactionId')
        if transaction_id is None:
            log.error('No transactionId found in IPN.')
            return('transactionId not found')
        
        buyer_name = request.POST.get('buyerName')
        
        # look up transaction in DB
        session = meta.Session()
        txn_q = meta.Session.query(Transaction)
        transaction = txn_q.filter_by(fps_transaction_id=transaction_id).first()  # TODO: use one() and catch exceptions?
        if transaction is None:
            log.error('Transaction %s could not be found in DB' % transaction_id)
            # TODO: record detailed info in case DB insert was not committed before IPN was received!
            return('transaction info not found')
        
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
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
            elif transaction.fps_transaction_status == 'Success':
                log.debug('Received IPN for pending status out of order - txn already succeeded.  Ignoring.')
        
        elif transaction_status.upper() == 'SUCCESS':
            # if status is success, look up transaction in DB.
            # If:
            #  - transaction is pending, update to success and deliver gift
            #  - transaction is already success, log it (duplicate notification?)
            if transaction.fps_transaction_status is None or transaction.fps_transaction_status == 'Pending':
                transaction.fps_transaction_status = 'Success'
                transaction.success_date = model.now()
                transaction.donation.pending = False
                # update buyer name if empty
                if transaction.buyer_name is None and buyer_name is not None:
                    transaction.buyer_name = buyer_name
                fb_logic.update_user_fbml_by_wg_userid(transaction.donation.recipient_id)
                session.commit()
            elif transaction.fps_transaction_status == 'Success':
                log.debug('Transaction %s is already in Success state. ABT payment or duplicate IPN notification?' % transaction_id)
        
        
        return 'roger that'
