### base/base.py

from abc import ABC, abstractmethod
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Logging setup ---
LOG_DIR = os.environ.get("AIRBOOK_SCRAPER_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "scraper.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logger = logging.getLogger("scraper")

# --- Utils and Exceptions ---
def mask_email_prefix(s: str) -> str:
    if not s:
        return None
    prefix, domain = s.split('@', 1)
    if len(prefix) < 4:
        return s
    masked = prefix[:3] + '*****' + prefix[-1]
    return f"{masked}@{domain}"

def raise_if_blank(args:dict):
    for arg_name, arg in args.items():
        if not arg:
            raise InvalidParameterError(f'Wrong usage: {arg_name} cannot be blank.')
        
def raise_auth_error_or_for_status(response, status_reason: dict, msg: str):
    if response.status_code in status_reason and status_reason[response.status_code].lower() in response.reason.lower():
        raise AuthenticationError(msg)
    else:
        response.raise_for_status()
        
def raise_scraping_error(locators, original_exception, extra_raise_condition = None):
    msg = f'{extra_raise_condition} and none of expected locators: {locators} were not found.' \
        if extra_raise_condition else f'None of expected locators: {locators} were not found.'
    raise ScrapingError(msg) from original_exception

class InvalidParameterError(Exception):
    """Thrown if wrong usage option is used."""
    pass

class AuthenticationError(Exception):
    """
        Thrown if authentication error during scraping initialization (wrong credentials, too many OTP input attempts etc.) 
        or if auth data is expired or nonvalid.
    """
    pass

class ScrapingError(Exception):
    """Thrown if expected selenium locators or auth data is not found."""
    pass

class BaseScraping(ABC):
    """Basic Selenium class for automated login."""

    def __init__(
        self, 
        email: str = None,
        password: str = None,
        browser_args: list | None = None,
        page_load_strategy: str | None = None
    ) -> None:
        self._email = email
        self._password = password
        self._browser_args = browser_args
        self._page_load_strategy = page_load_strategy
        self._driver = None
        logger.info("Instance initialized for %s", mask_email_prefix(self._email) or 'TOKEN-based session')

    def _init_driver(self):
        options = Options()
        if self._browser_args is not None:
            for argument in self._browser_args:
                options.add_argument(argument)
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                             "AppleWebKit/537.36 (KHTML, like Gecko) "
                             "Chrome/113.0.0.0 Safari/537.36")
        if self._page_load_strategy is not None:
            options.page_load_strategy = self._page_load_strategy
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        service = Service(log_path=os.devnull)

        self._driver = webdriver.Chrome(service=service, options=options)
        self._driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        logger.info("Selenium WebDriver started.")

    def authenticate_and_setup(self):
        """
        Unified method to start Selenium session and perform login explicitly.
        Should be called manually after instantiation.
        """
        logger.info("Authorization started for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
        self._init_driver()
        try:
            self._login()
            logger.info("Authorization successful for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
        except Exception as e:
            logger.exception("Authorization failed for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
            raise
        finally:
            self._driver.quit()
            logger.info("Selenium WebDriver closed.")

    @abstractmethod
    def _login(self):
        """Stub method. Implement this method in child class."""
        pass
    
    def _hide_locator(self, locator, timeout) -> None:
            driver = self._driver
            try:
                cookie_window = WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(locator)
                    )
            except TimeoutException as e:
                raise_scraping_error(locator, e)
            
            driver.execute_script("arguments[0].style.display = 'none';", cookie_window)

    def _is_locator_found(self, locator: tuple, timeout: float) -> bool:
        try:
            WebDriverWait(self._driver, timeout).until(EC.presence_of_element_located(locator))
        except TimeoutException:
            logger.warning("Locator not found: %s", locator)
            return False
        return True