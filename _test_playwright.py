import sys
import os
# Add current directory to path
sys.path.append(os.getcwd())

from toolset import navigation
from state_manager import state

def test_navigation():
    print("Testing Playwright Initialization...")
    try:
        navigation.init_browser()
        
        # Set a dummy state or use default
        print(f"Current State: {state.get_state()}")
        
        print("Fetching pathways...")
        pathways = navigation.get_possible_pathways()
        print(f"Pathways found: {len(pathways)}")
        for p in pathways:
            print(f" - {p['description']} (ID: {p['id']})")
            
        if len(pathways) > 0:
            print("SUCCESS: Pathways fetched via Playwright.")
        else:
            print("WARNING: No pathways found (might be expected depending on location or API key).")
            
    except Exception as e:
        print(f"FAILURE: {e}")
    finally:
        print("Closing browser...")
        navigation.close_browser()

if __name__ == "__main__":
    test_navigation()
