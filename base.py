from __future__ import annotations

from abc import ABC, abstractmethod
import os
import logging
from typing import NoReturn, Literal

from requests import Response
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

LOG_DIR = os.environ.get("COMMON_HOST_LOG_DIR", "./logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "common-host-api.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("scraper")


class InvalidParameterError(Exception):
    """Represents invalid user input error."""


class AuthenticationError(Exception):
    """Represents authentication failure error."""


class ScrapingError(Exception):
    """Represents scraping failure error."""

def mask_email_prefix(s: str) -> str | None:
    if not s:
        return None
    prefix, domain = s.split('@', 1)
    if len(prefix) < 4:
        return s
    masked = prefix[:3] + '*****' + prefix[-1]
    return f"{masked}@{domain}"

def raise_if_blank(args: dict[str, object]) -> None:
    """Raise if any provided argument is blank or falsy.

    Args:
        args: Mapping of argument names to values.

    Returns:
        None
    """
    for arg_name, arg in args.items():
        if not arg:
            raise InvalidParameterError(f"Wrong usage: {arg_name} cannot be blank.")


def raise_auth_error_or_for_status(
    response: Response, status_reason: dict[int, str], msg: str
) -> None:
    """Raise AuthenticationError on specific status+reason or propagate HTTP error.

    Args:
        response: Requests response object.
        status_reason: Map of status code to expected reason substring.
        msg: Message for AuthenticationError.

    Returns:
        None
    """
    reason_ok = status_reason.get(response.status_code)
    if reason_ok and reason_ok.lower() in (response.reason or "").lower():
        raise AuthenticationError(msg)
    response.raise_for_status()


def raise_scraping_error(
    locators: tuple,
    original_exception: Exception,
    extra_raise_condition: str | None = None,
) -> NoReturn:
    """Always raise ScrapingError with context and original exception.

    Args:
        locators: Locator that was expected to be present.
        original_exception: Original exception to chain.
        extra_raise_condition: Additional context message.

    Returns:
        NoReturn
    """
    msg = (
        f"{extra_raise_condition} and none of expected locators: {locators} were not found."
        if extra_raise_condition
        else f"None of expected locators: {locators} were not found."
    )
    raise ScrapingError(msg) from original_exception


class BaseScraping(ABC):
    """Base Selenium helper for automated login flow."""

    def __init__(
        self,
        email: str | None = None,
        password: str | None = None,
        browser_args: list[str] | None = None,
        page_load_strategy: Literal["normal", "eager", "none"] | None = None,
    ) -> None:
        """Initialize minimal state to start WebDriver.

        Args:
            email: Login email for the target service.
            password: Login password for the target service.
            browser_args: Extra Chrome CLI arguments.
            page_load_strategy: Selenium page load strategy.
        """
        self._email = email
        self._password = password
        self._browser_args = browser_args
        self._page_load_strategy = page_load_strategy
        self._driver: WebDriver | None = None
        logger.info("Instance initialized for %s", mask_email_prefix(self._email) or 'TOKEN-based session')

    def _init_driver(self) -> None:
        """Create and configure Chrome WebDriver instance.

        Returns:
            None
        """
        options = Options()
        if self._browser_args:
            for argument in self._browser_args:
                options.add_argument(argument)

        # Set a consistent desktop user-agent for stability.
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/113.0.0.0 Safari/537.36"
        )
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        if self._page_load_strategy:
            options.page_load_strategy = self._page_load_strategy

        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(log_path=os.devnull)

        self._driver = webdriver.Chrome(service=service, options=options)
        # Hide webdriver flag to bypass basic bot checks.
        self._driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            },
        )
        logger.info("Selenium WebDriver started.")

    def authenticate_and_setup(self) -> None:
        """Run login flow and close the driver safely.

        Returns:
            None
        """
        logger.info("Authorization started for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
        self._init_driver()
        assert self._driver is not None

        try:
            self._login(self._driver)
            logger.info("Authorization successful for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
        except Exception as e:
            logger.exception("Authorization failed for %s", mask_email_prefix(self._email) or 'TOKEN-based session')
            raise
        finally:
            self._driver.quit()
            logger.info("Selenium WebDriver closed.")

    @abstractmethod
    def _login(self, driver: WebDriver) -> None:
        """Perform concrete login steps for a specific service.

        Args:
            driver: Active Selenium WebDriver.
        """

    def _hide_locator(
        self, driver: WebDriver, locator: tuple[str, str], timeout: float = 5.0
    ) -> None:
        """Hide element by CSS/DOM injection when it appears.

        Args:
            driver: Active Selenium WebDriver.
            locator: Selenium locator tuple (by, value).
            timeout: Wait time in seconds.

        Returns:
            None
        """
        cookie_window = None
        try:
            cookie_window = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException as e:
            raise_scraping_error(locator, e)

        # Hide the element to unblock interactions.
        driver.execute_script("arguments[0].style.display = 'none';", cookie_window)

    def _is_locator_found(
        self, driver: WebDriver, locator: tuple[str, str], timeout: float = 5.0
    ) -> bool:
        """Return True if locator is present within the timeout.

        Args:
            driver: Active Selenium WebDriver.
            locator: Selenium locator tuple (by, value).
            timeout: Wait time in seconds.

        Returns:
            True if element appears before timeout, else False.
        """
        try:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located(locator)
            )
        except TimeoutException:
            logger.warning("Locator not found: %s", locator)
            return False
        return True
