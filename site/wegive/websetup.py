"""Setup the WeGive application"""
import logging
from pylons import config
from paste.deploy.converters import asbool

from wegive.config.environment import load_environment

log = logging.getLogger(__name__)

def setup_app(command, conf, vars):
    """Place any commands to setup wegive here"""
    load_environment(conf.global_conf, conf.local_conf)

    # Load the models
    from wegive.model import meta
    meta.metadata.bind = meta.engine

    # Create the tables if they aren't there already
    if asbool(config['debug']):
        meta.metadata.drop_all()
    meta.metadata.create_all(checkfirst=True)

    # add some test data if we're in debug mode
    if asbool(config['debug']):
        from wegive.model import User, Gift
        session = meta.Session()
        
        test_user_1 = User(u'test1@example.com', 'welcome1')
        test_user_2 = User(u'test2@example.com', 'welcome1')
        test_artist_1 = User(u'artist1@example.com', 'welcome1')
        session.add_all([test_user_1,test_user_2,test_artist_1])
        session.flush()
        
        test_gift_1 = Gift(test_artist_1.id, u'Test Gift 1', True)
        session.add(test_gift_1)
        
        session.add_all([Gift(test_artist_1.id, u'Test Gift 2', True),
                         Gift(test_artist_1.id, u'Test Gift 3', True),
                         Gift(test_artist_1.id, u'Test Gift 4', True),
                         Gift(test_artist_1.id, u'Test Gift 5', True),
                         Gift(test_artist_1.id, u'Test Gift 6'),
                         Gift(test_artist_1.id, u'Test Gift 7', True),
                         Gift(test_artist_1.id, u'Test Gift 8', True),
                         Gift(test_artist_1.id, u'Test Gift 9', True),
                         Gift(test_artist_1.id, u'Test Gift 10', True),
                         Gift(test_artist_1.id, u'Test Gift 11', True),
                         Gift(test_artist_1.id, u'Test Gift 12', True),
                         Gift(test_artist_1.id, u'Test Gift 13'),
                         Gift(test_artist_1.id, u'Test Gift 14', True),
                         Gift(test_artist_1.id, u'Test Gift 15', True),
                         Gift(test_artist_1.id, u'Test Gift 16', True),
                         Gift(test_artist_1.id, u'Test Gift 17', True),
                         Gift(test_artist_1.id, u'Test Gift 18', True),
                         Gift(test_artist_1.id, u'Test Gift 19', True),
                         Gift(test_artist_1.id, u'Test Gift 20', True),
                         Gift(test_artist_1.id, u'Test Gift 21', True),
                         Gift(test_artist_1.id, u'Test Gift 22', True),
                         Gift(test_artist_1.id, u'Test Gift 23', True),
                         Gift(test_artist_1.id, u'Test Gift 24', True),
                         Gift(test_artist_1.id, u'Test Gift 25', True),
                         Gift(test_artist_1.id, u'Test Gift 26', True),
                         Gift(test_artist_1.id, u'Test Gift 27', True),
                         Gift(test_artist_1.id, u'Test Gift 28', True),
                         Gift(test_artist_1.id, u'Test Gift 29', True),
                         Gift(test_artist_1.id, u'Test Gift 30', True),
                         Gift(test_artist_1.id, u'Test Gift 31', True),
                         Gift(test_artist_1.id, u'Test Gift 32', True),
                         Gift(test_artist_1.id, u'Test Gift 33', True),
                         Gift(test_artist_1.id, u'Test Gift 34', True),
                         Gift(test_artist_1.id, u'Test Gift 35', True)])
        session.commit()
        
        log.debug('added data:')
        for row in session.query(User).all():
            print row
        for row in session.query(Gift).all():
            print row