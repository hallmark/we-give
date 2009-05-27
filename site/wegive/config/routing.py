# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""Routes configuration

The more specific and detailed routes should be defined first so they
may take precedent over the more generic routes. For more information
refer to the routes manual at http://routes.groovie.org/docs/
"""
from pylons import config
from routes import Mapper

def make_map():
    """Create, configure and return the routes Mapper"""
    map = Mapper(directory=config['pylons.paths']['controllers'],
                 always_scan=config['debug'])
    map.minimization = False
    map.sub_domains = True
    # TODO: explicit=True ?  p.210 in Pylons Book
    # book uses map.minimize.  is this a typo?
    
    fbsubdomain = config['app_conf']['pyfacebook.subdomain']
    
    # The ErrorController route (handles 404/500 error pages); it should
    # likely stay at the top, ensuring it can always be resolved
    map.connect('/error/{action}', controller='error')
    map.connect('/error/{action}/{id}', controller='error')

    # CUSTOM ROUTES HERE
    map.connect('/app/{action}', controller='facebookapp', conditions={'sub_domain':[fbsubdomain]})
    map.connect('/{action}', controller='facebookcanvas', conditions={'sub_domain':[fbsubdomain]})
    map.connect('/', controller='facebookcanvas', action='index', conditions={'sub_domain':[fbsubdomain]})
    map.connect('/fps/ipn', controller='ipn', action='process_ipn')
    map.connect('/{action}', controller='hub_site')
    map.connect('/', controller='hub_site', action='index')
    map.connect('/admin/{action}', controller='admin')
    map.connect('/admin/', controller='admin', action='index')

    map.connect('/{controller}/{action}')
    map.connect('/{controller}/{action}/{id}')

    return map
