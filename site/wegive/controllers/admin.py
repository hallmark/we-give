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
from wegive.model import User

from wegive.lib.base import BaseController, render
#import wegive.lib.helpers as h

log = logging.getLogger(__name__)

class UserTable(TableBase):
    __model__ = User
    __limit_fields__ = ['email', 'first_name', 'last_name', 'created']

class UserTableFiller(TableFiller):
    __model__ = User
    __limit_fields__ = ['id', 'email', 'first_name', 'last_name', 'created']

class AdminController(BaseController):

    def index(self):
        return render('/web/admin/index.tmpl')

    def users(self):
        from wegive.model import meta
        session = meta.Session()
        c.user_table = h.literal(UserTable(session))
        c.user_table_value = UserTableFiller(session).get_value()
        return render('/web/admin/users.tmpl')

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
