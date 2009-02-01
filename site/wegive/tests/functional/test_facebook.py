from wegive.tests import *

class TestFacebookController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='facebook', action='index'))
        # Test response...
