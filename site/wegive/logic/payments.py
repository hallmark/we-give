# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""Amazon Flexible Payments Service (FPS) logic

Consists of logic that handles interaction with the Amazon FPS Service.
"""
import logging
from pylons import config, app_globals

import fpys
import uuid
import xml.etree.ElementTree as ET
import urllib, urllib2

import wegive.lib.helpers as h
import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona, SocialNetwork, Transaction

AWS_KEY_ID = config['AWS_KEY_ID']
CBUI_RETURN_URL = config['fps_cbui_return_url']
CBUI_URL = config['fps_cbui_url']
FPS_API_VERSION = '2009-01-09'

log = logging.getLogger(__name__)

def get_cbui_url(caller_reference,
                 payment_reason,
                 transaction_amount,
                 recipient_token=None,
                 website_desc=None,
                 collect_shipping_address=False,
                 return_url=CBUI_RETURN_URL,
                 pipeline_name="SingleUse",
                 ):
    """Compute parameters for request to Co-Branded FPS pages"""
    fps_client = app_globals.fps_client
    
    parameters = {'callerReference': caller_reference,
                  'paymentReason': payment_reason,
                  'transactionAmount': transaction_amount,
                  'callerKey': AWS_KEY_ID,
                  'pipelineName': pipeline_name,
                  'returnURL': return_url,
                  'version': FPS_API_VERSION,
                  }
    
    # optional param
    if website_desc is not None:
        parameters['websiteDescription'] = website_desc
    if collect_shipping_address:
        parameters['collectShippingAddress'] = True
    
    # for marketplace transactions
    if recipient_token is not None:
        parameters['recipientToken'] = recipient_token
    
    parameters['awsSignature'] = fps_client.get_pipeline_signature(parameters)
    query_string = urllib.urlencode(parameters)
    url = "%s?%s" % (CBUI_URL, query_string)
    log.debug('FPS pipeline URL: %s' % url)
    return url

def pay_marketplace(sender_token,
                    recipient_token,
                    amount,
                    caller_reference,
                    charge_caller=False,
                    fixed_fee=0,
                    variable_fee=0):
    """Make Amazon FPS API call for Marketplace 'Pay' operation."""
    fps_client = app_globals.fps_client
    
    if charge_caller:
        charge_fee_to = 'Caller'
    else:
        charge_fee_to = 'Recipient'
    
    pay_params = {'Action': 'Pay',
                  'SenderTokenId': sender_token,
                  'RecipientTokenId': recipient_token,
                  'ChargeFeeTo': charge_fee_to,
                  'MarketplaceFixedFee.Value': fixed_fee,
                  'MarketplaceFixedFee.CurrencyCode': 'USD',
                  'MarketplaceVariableFee': variable_fee,
                  'TransactionAmount.Value': amount,
                  'TransactionAmount.CurrencyCode': 'USD',
                  'CallerReference': caller_reference,
                  }
    fps_response = fps_client.execute(pay_params)
    log.debug('Marketplace Pay response XML: ' + ET.tostring(fps_response.element))
    return fps_response

