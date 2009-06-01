# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from sprox.tablebase import TableBase
from sprox.fillerbase import TableFiller
from wegive.model import User, Charity
import wegive.model.meta as meta
from pylons import config, app_globals

from wegive.lib.base import BaseController, render
#import wegive.lib.helpers as h

AWS_KEY_ID = config['AWS_KEY_ID']
AWS_SECRET_KEY = config['AWS_SECRET_KEY']
CBUI_RETURN_URL = config['fps_recip_token_return_url']

log = logging.getLogger(__name__)

class UserTable(TableBase):
    __model__ = User
    __limit_fields__ = ['email', 'first_name', 'last_name', 'created']

class UserTableFiller(TableFiller):
    __model__ = User
    __limit_fields__ = ['id', 'email', 'first_name', 'last_name', 'created']

def log_admin_req(req):
    buf = '\n\n= = = = = = = = = = = = = = = = = = = = = = = = = = = = = = = ='
    buf += '\n=   Admin Request                                             ='
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

class AdminController(BaseController):

    def __init__(self):
        self.fps_client = app_globals.fps_client

    def index(self):
        return render('/web/admin/index.tmpl')

    def users(self):
        from wegive.model import meta
        session = meta.Session()
        c.user_table = h.literal(UserTable(session))
        c.user_table_value = UserTableFiller(session).get_value()
        return render('/web/admin/users.tmpl')

    def reg_recipient(self):
        charity_q = meta.Session.query(Charity)
        c.charities = charity_q.order_by(Charity.created)
        return render('/web/admin/reg_recipient.tmpl')

    def reg_recipient_2(self):
        charity_id = request.params.get('charity_val')
        
        charity_q = meta.Session.query(Charity)
        c.charity = charity_q.get(charity_id)
        if c.charity is None:
            c.error_msg = 'Charity not found'
            return(c.error_msg)
            #return render('/facebook/send_gift.tmpl')
        
        # compute parameters for request to Co-Branded FPS pipeline
        import urllib, urllib2
        import uuid
        
        parameters = {'callerReference': 'wgrecipient_%d_%s' % (c.charity.id, uuid.uuid1().hex),
                      'maxFixedFee': 0,
                      'maxVariableFee' : 0,
                      'paymentMethod' : 'CC,ACH,ABT',
                      'recipientPaysFee': 'False',
                      'callerKey': AWS_KEY_ID,
                      'pipelineName': 'Recipient',
                      'websiteDescription': 'We Give Foundation',
                      'returnURL': CBUI_RETURN_URL,
                      'version': '2009-01-09',
                      }
        parameters['awsSignature'] = self.fps_client.get_pipeline_signature(parameters)
        query_string = urllib.urlencode(parameters)
        c.fps_cbui_url = "%s?%s" % (config['fps_cbui_url'], query_string)
        log.debug("\nCBUI URL -----\n%s\n" % c.fps_cbui_url)
        
        return render('/web/admin/reg_recipient_2.tmpl')

    def reg_recipient_return(self):
        log_admin_req(request)

        # log transaction and/or request id
        
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
            return(c.error_msg)
        
        if not status == 'SR':
            return("status not success")
        
        caller_reference = request.params.get('callerReference')
        charity_id = int(caller_reference.split('_')[1])
        
        session = meta.Session()
        charity = meta.Session.query(Charity).get(charity_id)
        if charity is None:
            log.error('Error in return from CBUI: charity information could not be found')
            c.error_msg = 'Charity information could not be found.'
            return(c.error_msg)
        
        token_id = request.params.get('tokenID')
        if token_id is None:
            c.error_msg = 'No recipient token ID found.'
            return(c.error_msg)
        
        charity.recipient_token_id = token_id
        session.commit()
        
        c.charity = charity
        return render('/web/admin/reg_recipient_return.tmpl')

    def touch_fbml(self):
        uid = request.params.get('uid')
        if uid is None:
            return 'Please specify uid'
        import wegive.model.meta as meta
        from wegive.model import UserPersona, SocialNetwork
        import wegive.logic.facebook_platform as fb_logic
        network = meta.Session.query(SocialNetwork).filter_by(name=u'Facebook').one()
        userpersona_q = meta.Session.query(UserPersona)
        fb_userpersona = userpersona_q.filter_by(network_id=network.id).filter_by(network_user_id=uid).first()
        if fb_userpersona is None:
            return 'No record of FB user %s' % uid
        
        fb_logic.update_user_fbml_by_userpersona(fb_userpersona)
        return 'done'
