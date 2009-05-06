import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from facebook import FacebookError
from facebook.wsgi import facebook

from wegive.lib.base import BaseController, render
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
            log.debug('user: %s' % facebook.user)
            log.debug('Authorized new user for We Give, user: %s' % facebook.user)
            # TODO: update row in UserPersona table
        
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
            log.debug('user: %s' % facebook.user)
            log.debug('Removing user with uid: %s' % facebook.user)
            # TODO: update row in UserPersona table
        
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
