import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from facebook import FacebookError
from facebook.wsgi import facebook

from wegive.lib.base import BaseController, render
#from wegive import model

log = logging.getLogger(__name__)

class FacebookcanvasController(BaseController):
    
    def __before__(self):
        c.facebook = facebook

    #@template('facebook/index')
    def index(self):
        # Return a rendered template
        #   return render('/template.mako')
        # or, Return a response
        #return 'Hello World'
        result = 'Facebook request ==============='
        result += '\nrequest.url:\t%s\n'%request.url
        result += '\nHeaders -----\n'
        for key,value in request.headers.items():
            result += '%s: %r\n'%(key, value)
        result += '\nPOST params -----\n'
        for key,value in request.POST.items():
            result += '%s: %r\n'%(key, value)
        log.debug(result)
        
        c.foo = 'test string'
        
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
        
        current_user = None
        facebook.process_request()
        if facebook.user:
            log.debug('user: %s' % facebook.user)
            current_user = facebook.user
        elif facebook.canvas_user:
            log.debug('canvas_user: %s' % facebook.canvas_user)
            current_user = facebook.canvas_user
        
        if current_user:
            info = facebook.api_client.users.getInfo([current_user], ['name', 'pic_square', 'locale'])[0]
            log.debug('name: %s, pic: %s, locale: %s' % (info['name'], info['pic_square'], info['locale']) )
            friends = facebook.api_client.friends.get(uid=current_user)
            friends = facebook.api_client.users.getInfo(friends, ['uid', 'name', 'pic_square', 'locale'])
            c.friends = friends
        
        
        return render('/facebook/index.tmpl')
