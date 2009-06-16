# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""
Handles Facebook callback requests for authorizing or removing a user from the
We Give application.
"""
import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from facebook import FacebookError
from facebook.wsgi import facebook

from wegive.lib.base import BaseController, render
import wegive.logic.facebook_platform as fb_logic
import wegive.logic.user as user_logic
import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona,
#from wegive import model

log = logging.getLogger(__name__)

class FacebookappController(BaseController):

    def index(self):
        # Return a rendered template
        #   return render('/template.mako')
        # or, Return a response
        return 'Hello World'
    
    def authorize(self):
        result = 'Facebook request ==============='
        result += '\nrequest.url:\t%s\n'%request.url
        result += '\nHeaders -----\n'
        for key,value in request.headers.items():
            result += '%s: %r\n'%(key, value)
        result += '\nPOST params -----\n'
        for key,value in request.POST.items():
            result += '%s: %r\n'%(key, value)
        log.debug(result)
        
        facebook.process_request()
        if facebook.user:
            log.debug('Authorized new user for We Give, user: %s' % facebook.user)
            
            # Update/create row in UserPersona table and set is_app_user to True
            session = meta.Session()
            fb_user = user_logic.get_fb_userpersona(session, facebook.user, create_if_missing=True)
            fb_user.is_app_user = True
            
            if not fb_logic.has_profile_fbml(facebook.user):
                ALLOW_FBML_INIT_ON_AUTHORIZE = True
                if ALLOW_FBML_INIT_ON_AUTHORIZE:
                    fb_logic.update_user_fbml_by_userpersona(fb_user)
                else:
                    log.debug("Updating profile FBML on app authorize is currently de-fanged, so that handling users w/o FBML can be properly tested!")
            session.commit()
        
        """
        if facebook.check_session():
            log.debug('check_session is true')
            if facebook.uid:
                log.debug('Authorized new user for We Give, uid: %s' % facebook.uid)
        """

    def remove(self):
        result = 'Facebook request ==============='
        result += '\nrequest.url:\t%s\n'%request.url
        result += '\nHeaders -----\n'
        for key,value in request.headers.items():
            result += '%s: %r\n'%(key, value)
        result += '\nPOST params -----\n'
        for key,value in request.POST.items():
            result += '%s: %r\n'%(key, value)
        log.debug(result)
        
        facebook.process_request()
        if facebook.user:
            log.debug('Removing user with uid: %s' % facebook.user)
            
            # Update row in UserPersona table
            session = meta.Session()
            fb_user = user_logic.get_fb_userpersona(session, facebook.user)
            if fb_user:
                fb_user.is_app_user = False
                session.commit()
        
        """
        if facebook.check_session():
            log.debug('check_session is true')

        if facebook.uid:
            log.debug('uid: %s' % facebook.uid)
        
        fb_params = facebook.validate_signature(request.POST)
        if fb_params and 'user' in fb_params:
            uid = fb_params['user']
            log.debug('Removing user with uid: %s' % uid)
        """
