from pylons import config

import fpys

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
        self.fps_client = fpys.FlexiblePaymentClient(config['AWS_KEY_ID'],
                                                     config['AWS_SECRET_KEY'])
