import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from wegive.lib.base import BaseController, render
#from wegive import model

log = logging.getLogger(__name__)

class HelloController(BaseController):

    def index(self):
        # Return a rendered template
        #   return render('/template.mako')
        # or, Return a response
        result = '<html><body><h2>Request</h2>'
        result += '<h3>Headers</h3>'
        for key,value in request.headers.items():
            result += '%s: %r <br>'%(key, value)
        result += 'request.url: %s'%request.url
        result += '</body></html>'
        log.debug(result)
        
        return result

    def mock_fps(self):
        result = '<html><body><h2>Mock FPS Site</h2>'
        result += '<h3>Headers</h3>'
        for key,value in request.headers.items():
            result += '%s: %r <br>'%(key, value)
        result += 'request.url: %s'%request.url
        result += '</body></html>'
        log.debug(result)
        
        return result

