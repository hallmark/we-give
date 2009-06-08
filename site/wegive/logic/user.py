# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""User and UserPersona logic

Consists of logic that handles users and user personas.
"""
import logging
from pylons import config, app_globals

import wegive.model.meta as meta
from wegive.model import Charity, Donation, Gift, User, UserPersona, SocialNetwork, Transaction

log = logging.getLogger(__name__)

def decorate_with_fb_uid(user_list, id_name='user_id'):
    if user_list is None:
        return None
    session = meta.Session()
    for u in user_list:
        user_id = getattr(u, id_name)
        u.fb_uid = get_network_uid(session, user_id)
    return user_list
    
def get_network_uid(session, user_id, network_name=u'Facebook'):
    network = meta.Session.query(SocialNetwork).filter_by(name=network_name).one()

    userpersona_q = meta.Session.query(UserPersona)
    up = userpersona_q.filter_by(network_id=network.id).filter_by(wg_user_id=user_id).first()
    if up:
        return up.network_user_id
    else:
        return None
