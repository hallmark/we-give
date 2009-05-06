import logging

from pylons import request, response, session, tmpl_context as c
from pylons.controllers.util import abort, redirect_to

from wegive.lib.base import BaseController, render

log = logging.getLogger(__name__)


class AdminController(BaseController):

    def index(self):
        return render('/web/admin/index.tmpl')

