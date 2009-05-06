import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from wegive.lib.base import BaseController, render

log = logging.getLogger(__name__)

class HubSiteController(BaseController):

    def index(self):
        # Return a rendered template
        #return render('/hub_site.mako')
        # or, return a response
        return render('/web/index.tmpl')
