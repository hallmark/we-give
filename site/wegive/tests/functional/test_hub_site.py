from wegive.tests import *

class TestHubSiteController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='hub_site', action='index'))
        # Test response...
