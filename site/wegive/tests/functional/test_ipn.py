from wegive.tests import *

class TestIpnController(TestController):

    def test_index(self):
        response = self.app.get(url(controller='ipn', action='index'))
        # Test response...
