import threading
from playwright.sync_api import sync_playwright

class BrowserManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BrowserManager, cls).__new__(cls)
                cls._instance._playwright = None
                cls._instance._browser = None
                cls._instance._context = None
            return cls._instance

    def ensure_browser(self):
        """Ensures the browser is started."""
        with self._lock:
            if self._playwright is None:
                self._playwright = sync_playwright().start()
                self._browser = self._playwright.chromium.launch(headless=True)
                self._context = self._browser.new_context()
                print("Shared Playwright Browser Initialized.")

    def get_new_page(self):
        """Returns a new page from the shared context."""
        self.ensure_browser()
        with self._lock:
            return self._context.new_page()

    def close_all(self):
        """Closes the browser and stops Playwright."""
        with self._lock:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
            self._playwright = self._browser = self._context = None
            print("Shared Playwright Browser Closed.")

# Global singleton access
browser_manager = BrowserManager()
