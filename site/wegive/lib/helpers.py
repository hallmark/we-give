# -*- coding: utf-8 -*-
#
# All portions of the code written by Mark Ture are Copyright (c) 2009
# Mark Ture. All rights reserved.
##############################################################################
"""Helper functions

Consists of functions to typically be used within templates, but also
available to Controllers. This module is available to both as 'h'.
"""
# Import helpers as desired, or define your own, ie:
# from webhelpers.html.tags import checkbox, password

from webhelpers.html import literal
from webhelpers.html.converters import format_paragraphs, nl2br
from webhelpers.html.tags import stylesheet_link
from webhelpers.text import plural
from routes import url_for

def gift_image_url(gift_id):
    from pylons import config
    gift_url_pattern = config['gift_url_pattern']
    return gift_url_pattern % gift_id
    