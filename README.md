# common-host-api

**Base Selenium helper for automated login flow**

## Overview

A small utility library for building automated login flows for host dashboards. It provides a typed base class powered by Selenium that encapsulates browser setup, consistent logging, error handling, and helper utilities.

## Features

- Centralized logging with Python logging; logs written to `./logs/common-host-api.log` by default
- Input validation helper `raise_if_blank` for required arguments
- Error helpers: `raise_auth_error_or_for_status` and `raise_scraping_error` for consistent failures
- Abstract base class `BaseScraping` configures headless Chrome and ensures driver teardown
- Utilities: `mask_email_prefix` for safe logs; helpers to hide blocking pop-ups and detect elements

## Installation

```bash
pip install git+https://github.com/kaxcheg/common-host-api.git
```

## Usage

```python
from common_host_api.base import BaseScraping

class ExampleHost(BaseScraping):
    def _login(self, driver):
        # 1) Navigate to login page, enter credentials and submit
        # 2) Extract tokens/cookies as needed
        pass

host = ExampleHost(email="user@example.com", password="mySecret")
host.authenticate_and_setup()  # runs the login flow and closes the browser
```

## Requirements

Python 3.12+, Selenium 4.25+, Requests 2.32+