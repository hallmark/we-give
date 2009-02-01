from wegive.tests import *

class TestFacebookappController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='facebookapp', action='index'))
        # Test response...
