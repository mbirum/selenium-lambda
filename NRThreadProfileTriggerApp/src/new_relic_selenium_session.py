import logging
import os
from tenacity import retry
from tenacity import wait_random_exponential
from tenacity import stop_after_attempt
from tenacity.before_sleep import before_sleep_log
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

class NRSeleniumSession():
  """
  Represents a Selenium browser session on New Relic (https://one.newrelic.com)

  Attributes:
    driver (selenium.webdriver.Chrome): Selenium Chromium browser session object
    usr (str): Username for New Relic Login
    pwd (str): Password for New Relic Login
    page_wait (int): Seconds to wait for pages to respond (default is 20)
    headless (bool): Run chrome browser headless. Only relevant for local testing (default is True)
  Methods:
    login(): Logs in to New Relic, and redirect to homepage (https://one.newrelic.com)
    logout(): Logs out of New Relic
    teardown(): Kills browser session
    start_thread_profiler(app_guid): Starts thread profiler for specified APM guid, if no profiler is already running
  """
  __retry_parameters = dict(
                            stop=stop_after_attempt(3), 
                            wait=wait_random_exponential(multiplier=1, max=30),
                            before_sleep=before_sleep_log(logging.getLogger(), logging.DEBUG),
                            reraise = True
                          )


  def __init__(self, usr: str, pwd: str, page_wait: int = 20, headless: bool = True):
    """
    Parameters:
      driver (selenium.webdriver.Chrome): Selenium Chromium browser session object
      usr (str): Username for New Relic Login
      pwd (str): Password for New Relic Login
      page_wait (int): Seconds to wait for pages to respond (default is 20)
      headless (bool): Run chrome browser headless. Only relevant for local testing (default is True)
    """
    __chrome_options = Options()
    if 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
      __chrome_options.add_argument('--headless')
      __chrome_options.add_argument('--no-sandbox')
      __chrome_options.add_argument('--start-maximized')
      __chrome_options.add_argument('--start-fullscreen')
      __chrome_options.add_argument('--single-process')
      __chrome_options.add_argument('--disable-dev-shm-usage')
      __chrome_options.binary_location = "/opt/python/headless-chromium"
      self.driver = Chrome("/opt/python/chromedriver", options=__chrome_options)
    else:
    # Use local defaults if running outside of Lambda runtime
      if headless:
        __chrome_options.add_argument('--headless')
      __chrome_options.add_argument(f'--window-size={1280}x{1024}')
      self.driver = Chrome(options=__chrome_options)
    
    self.__pwd = pwd
    self.__usr = usr
    self.__page_wait = page_wait
    self.__login_url = f'https://login.newrelic.com/login?return_to=https%3A%2F%2Fone.newrelic.com%2F&login%5Bemail%5D={self.__usr}'
    self.__logout_url = 'https://rpm.newrelic.com/logout'
    self.__tp_base_url = 'https://one.newrelic.com/nr1-core/apm-troubleshooting/thread-profiler/'
  

  @retry(**__retry_parameters)
  def login(self):
    """
    Logs in to New Relic, and redirect to homepage (https://one.newrelic.com)
    Makes retry attempts if login fails
    Will clear existing sessions if New Relic active session limit has been reached

    Raises:
      TimeoutException: Attempts to log out, then raises exception if homepage not found after specified page wait time
    """
    self.driver.get(self.__login_url)
    self.driver.find_element(By.ID, "login_password").click()
    self.driver.find_element(By.ID, "login_password").send_keys(self.__pwd)
    self.driver.find_element(By.ID, "login_submit").click()

    if (self.driver.title.strip() == "Active session limit reached"):
      logging.info(f"Active session limit reached. Ending existing sessions for {self.__usr}")
      self.driver.find_element(By.ID, "end_sessions").click()
      self.driver.find_element(By.ID, "login_submit").click()
    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.CLASS_NAME, "nr1-SidebarList-list")))
    except TimeoutException as te:
      logging.debug(self.driver.page_source)
      self.logout()
      raise


  @retry(**__retry_parameters)
  def logout(self):
    """
    Logs out of current New Relic session

    Raises:
      AssertionError: If login page is not found after logout attempt
    """
    self.driver.get(self.__logout_url)
    assert self.driver.title.strip() == "Log in to New Relic"

  def teardown(self):
    """
    Kills selenium browser session
    """
    self.driver.quit()


  @retry(**__retry_parameters)
  def start_thread_profiler(self, app_guid: str):
    """
    Starts thread profiler for specified APM guid
    Cancels attempt if no profiler is already running, or if profile is already scheduled

    Parameters:
      apm_guid (str): New Relic Globally Unique Identifier (GUID) for specified application
    """
    self.driver.get(self.__tp_base_url + app_guid)
    WebDriverWait(self.driver, self.__page_wait).until(ec.frame_to_be_available_and_switch_to_it(0))

    # If last attempt state remains, clear the message
    if bool(self.driver.find_elements(By.CLASS_NAME, "start_profiler_link")):
      self.driver.find_element(By.CLASS_NAME, "start_profiler_link").click()

    # If profiler already running, exit
    if bool(self.driver.find_elements(By.ID, "cancel_profiler_running")):
      logging.warning(f'Thread profile already running for {app_guid}. Cancelling attempt')
      return
    if bool(self.driver.find_elements(By.ID, "cancel_profiler_scheduled")):
      logging.warning(f'Thread profile already scheduled {app_guid}. Cancelling atempt')
      return

    #Start profiler
    WebDriverWait(self.driver, self.__page_wait).until(ec.element_to_be_clickable((By.CLASS_NAME, "submit_button")))
    self.driver.find_element(By.CLASS_NAME, "submit_button").click()
    logging.info('Thread profile started')
