import unittest
import os
import sys
import shutil

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state_manager import StateManager
from toolset.browser_manager import browser_manager
from toolset.instance import StreetViewInstance

class TestGeoGuessrLibrary(unittest.TestCase):
    
    def test_state_manager_independence(self):
        """Verify that multiple StateManagers are independent."""
        sm1 = StateManager()
        sm2 = StateManager()
        
        sm1.update(heading=100)
        sm2.update(heading=200)
        
        self.assertEqual(sm1.heading, 100)
        self.assertEqual(sm2.heading, 200)
        self.assertNotEqual(sm1.heading, sm2.heading)

    def test_browser_manager_singleton(self):
        """Verify that BrowserManager is a singleton."""
        from toolset.browser_manager import BrowserManager
        bm1 = BrowserManager()
        bm2 = BrowserManager()
        self.assertIs(bm1, bm2)

    def test_streetview_instance_init(self):
        """Verify StreetViewInstance initialization and distinct output dirs."""
        test_dir = "test_run_unit"
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
            
        inst = StreetViewInstance(output_dir=test_dir)
        self.assertTrue(os.path.exists(test_dir))
        self.assertIsNotNone(inst.page)
        
        # Cleanup
        inst.close()
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

    def test_instance_navigation_logic(self):
        """Verify navigation updates instance state correctly."""
        inst = StreetViewInstance(output_dir="test_nav")
        initial_heading = inst.state.heading
        
        inst.pan(10)
        self.assertEqual(inst.state.heading, (initial_heading + 10) % 360)
        
        inst.tilt(5)
        self.assertEqual(inst.state.pitch, 4.24) # -0.76 + 5
        
        inst.close()
        if os.path.exists("test_nav"):
            shutil.rmtree("test_nav")

    @classmethod
    def tearDownClass(cls):
        """Shut down the browser after all tests."""
        browser_manager.close_all()

if __name__ == "__main__":
    unittest.main()
