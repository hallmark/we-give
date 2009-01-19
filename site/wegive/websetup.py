"""Setup the WeGive application"""
import logging

from wegive.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    """Place any commands to setup wegive here"""
    load_environment(conf.global_conf, conf.local_conf)

    # Load the models
    from wegive.model import meta
    meta.metadata.bind = meta.engine

    # Create the tables if they aren't there already
    meta.metadata.create_all(checkfirst=True)
