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
import wegive.logic.user as user_logic

from pylons import config, app_globals as g
from paste.deploy.converters import asbool

from wegive.lib.base import BaseController, render
#import wegive.lib.helpers as h

AWS_KEY_ID = config['AWS_KEY_ID']
AWS_SECRET_KEY = config['AWS_SECRET_KEY']
CBUI_RETURN_URL = config['fps_recip_token_return_url']
FPS_PROMO_ACTIVE = asbool(config['fps_free_processing_promo_is_active'])

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
        self.fps_client = g.fps_client

    def index(self):
        # do not display admin index page until it is ready
        redirect_to(controller='hub_site', action='index')
        #return render('/web/admin/index.tmpl')

    def exclude_ga(self):
        return render('/web/admin/exclude_ga.tmpl')

    def flush_memcached(self):
        gifts_mkey = 'Cols.gifts-page1'
        res = g.mc.delete(gifts_mkey)
        log.debug('Result for deleting page 1 of gifts from memcached: %d' % res)
        
        charities_mkey = 'Cols.active-charities'
        res = g.mc.delete(charities_mkey)
        log.debug('Result for deleting list of active charities from memcached: %d' % res)
        
        return 'done'

    def users(self):
        from wegive.model import meta
        session = meta.Session()
        c.user_table = h.literal(UserTable(session))
        c.user_table_value = UserTableFiller(session).get_value()
        return render('/web/admin/users.tmpl')

    def allocations(self):
        from facebook import FacebookError
        from facebook.wsgi import facebook
        
        notifications_per_day = facebook.api_client.admin.getAllocation(integration_point_name='notifications_per_day')
        announcement_notifications_per_week = facebook.api_client.admin.getAllocation(integration_point_name='announcement_notifications_per_week')
        requests_per_day = facebook.api_client.admin.getAllocation(integration_point_name='requests_per_day')
        emails_per_day = facebook.api_client.admin.getAllocation(integration_point_name='emails_per_day')
        email_disable_message_location = facebook.api_client.admin.getAllocation(integration_point_name='email_disable_message_location')

        log.debug('notifications_per_day: %d' % (notifications_per_day))
        return('notifications_per_day: %d<br>announcement_notifications_per_week: %d<br>requests_per_day: %d<br>emails_per_day: %d<br>email_disable_message_location: %d' % (notifications_per_day, announcement_notifications_per_week, requests_per_day, emails_per_day, email_disable_message_location))
        

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
        
        if FPS_PROMO_ACTIVE:
            recipient_pays = 'False'
        else:
            recipient_pays = 'True'
        parameters = {'callerReference': 'wgrecipient_%d_%s' % (c.charity.id, uuid.uuid1().hex),
                      'maxFixedFee': 0,
                      'maxVariableFee' : 0,
                      'paymentMethod' : 'CC,ACH,ABT',
                      'recipientPaysFee': recipient_pays,
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

    def register_charity(self):
        log_admin_req(request)
        code = request.params.get('sc')
        
        if code == 'Ql4mMWkfAsYgMnNprzadt7Yl3A8':
            charity_shortname = 'hpwell'
        else:
            charity_shortname = ''
        
        charity_q = meta.Session.query(Charity)
        c.charity = charity_q.filter_by(short_code=charity_shortname).first()
        if c.charity is None:
            c.error_msg = 'Charity not found'
            return render('/web/admin/reg_recipient_2.tmpl')
        
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
            return render('/web/admin/reg_recipient_return.tmpl')
        
        if not status == 'SR':
            return("status not success")
        
        caller_reference = request.params.get('callerReference')
        charity_id = int(caller_reference.split('_')[1])
        
        session = meta.Session()
        charity = meta.Session.query(Charity).get(charity_id)
        if charity is None:
            log.error('Error in return from CBUI: charity information could not be found')
            c.error_msg = 'Charity information could not be found.'
            return render('/web/admin/reg_recipient_return.tmpl')
        
        token_id = request.params.get('tokenID')
        if token_id is None:
            c.error_msg = 'No recipient token ID found.'
            return render('/web/admin/reg_recipient_return.tmpl')
        
        if FPS_PROMO_ACTIVE:
            charity.promo_recipient_token_id = token_id
        else:
            charity.recipient_token_id = token_id
        session.commit()
        
        # clear out relevant data from memcached
        charities_mkey = 'Cols.active-charities'
        if g.mc.delete(charities_mkey):
            log.debug('Cleared active charities from memcached')
        else:
            log.debug('Unable to clear active charities from memcached!')
        
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

    def touch_fb_userpersona(self):
        uid = request.params.get('uid')
        if uid is None:
            return 'Please specify uid'
        
        session = meta.Session()
        fb_user = user_logic.get_fb_userpersona(session, uid, create_if_missing=True)
        session.commit()
        return 'done'

    def set_ref_handle(self):
        handle = request.params.get('handle')
        if handle is None:
            return 'Please specify handle'
        handle = 'profileCommonStyles'
        fbml = '<style type="text/css">.gift_box{width: 80px; margin:0 5px 20px; float:left;} .gift_img{width: 64px; margin:0 auto;} .gift_caption{width: 80px; text-align: center; margin-top:2px;} .no_items{text-align:center; margin:10px auto;}</style>'
        
        import wegive.logic.facebook_platform as fb_logic
        fb_logic.set_ref_handle(handle, fbml)
        return 'done'
