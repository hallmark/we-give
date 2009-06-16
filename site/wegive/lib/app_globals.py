# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
from pylons import config
from paste.deploy.converters import aslist

import fpys
import memcache


"""The application's Globals object"""

class Globals(object):
    """Globals acts as a container for objects available throughout the
    life of the application

    """
    def __init__(self):
        """One instance of Globals is created during application
        initialization and is available during requests via the
        'app_globals' variable

        """
        memcached_servers = aslist(config['memcached_servers'])
        self.mc = memcache.Client(memcached_servers, debug=0)
        
        self.fps_client = fpys.FlexiblePaymentClient(config['AWS_KEY_ID'],
                                                     config['AWS_SECRET_KEY'],
                                                     fps_url=config['fps_api_url'],
                                                     pipeline_url=config['fps_cbui_url'])
