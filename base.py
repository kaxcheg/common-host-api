"""Common base class for scraping-based APIs."""

from abc import ABC, abstractmethod
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class InvalidParameterError(Exception):
    """Raised when incorrect parameters are provided."""
    pass

class AuthenticationError(Exception):
    """Raised on authentication failure."""
    pass

class ScrapingError(Exception):
    """Raised when scraping fails due to unexpected page structure or absence of elements."""
    pass

class BaseScraping(ABC):
    """
    Base class for APIs with Selenium-based authentication.
    Does not perform login automatically upon initialization.
    """

    def __init__(
        self,
        browser_args: list | None = None,
        page_load_strategy: str | None = None,
    ) -> None:
        """Initialize Selenium WebDriver without performing login."""
        options = Options()
        browser_args = browser_args or ['--disable-gpu', '--headless']
        for arg in browser_args:
            options.add_argument(arg)

        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        )
        if page_load_strategy:
            options.page_load_strategy = page_load_strategy

        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        service = Service(log_path=os.devnull)

        self.driver = webdriver.Chrome(service=service, options=options)

        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
        )

    @abstractmethod
    def authorize(self, *args, **kwargs):
        """
        Perform authorization, setting necessary auth attributes.
        Implementation must be provided in subclasses.
        """
        pass

    def quit_driver(self):
        """Close Selenium WebDriver."""
        self.driver.quit()

    def _is_locator_found(self, locator: tuple, timeout: float) -> bool:
        """Check if a Selenium locator exists within given timeout."""
        try:
            WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            return False
        return True
