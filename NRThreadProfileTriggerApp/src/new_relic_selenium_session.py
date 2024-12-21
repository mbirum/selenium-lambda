import os
import time
import re as jvm_matcher
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait
from chrome_local import LocalChrome
from chrome_containerized import ContainerizedChrome

class NRSeleniumSession():

  def __init__(self, usr: str, pwd: str, page_wait: int = 40):
    
    self.__pwd = pwd
    self.__usr = usr
    self.__page_wait = page_wait
    self.__login_url = f'https://login.newrelic.com/login?return_to=https%3A%2F%2Fone.newrelic.com%2F&login%5Bemail%5D={self.__usr}'
    self.__logout_url = 'https://rpm.newrelic.com/logout'
    self.__profiler_base_url = 'https://one.newrelic.com/nr1-core/apm-troubleshooting/thread-profiler/'

    is_local = False
    try:
      is_local = os.environ['SELENIUM_LOCAL']
    except (AssertionError, KeyError):
      print('SELENIUM_LOCAL not provided. Using server configuration')

    if is_local:
      self.driver = LocalChrome()
    else: 
      self.driver = ContainerizedChrome()
    
  
  def login(self):
    self.driver.get(self.__login_url)
    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.ID, "i0116")))
    except TimeoutException as te:
      print("Error while waiting for login page")
      raise
    self.driver.find_element(By.ID, "i0116").click()
    self.driver.find_element(By.ID, "i0116").send_keys(self.__usr)
    self.driver.find_element(By.ID, "idSIButton9").click()

    time.sleep(3)

    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.ID, "idA_PWD_ForgotPassword")))
    except TimeoutException as te:
      print(f'Error while waiting for password screen - {te}')
    self.driver.find_element(By.ID, "i0118").click()
    self.driver.find_element(By.ID, "i0118").send_keys(self.__pwd)
    self.driver.find_element(By.ID, "idSIButton9").click()

    time.sleep(3)

    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.ID, "KmsiCheckboxField")))
    except TimeoutException as te:
      print(f'Error while waiting for StaySignedIn screen - {te}')
    self.driver.find_element(By.ID, "idSIButton9").click()

    print("Done with login steps. Waiting for nr1-nr1-core")

    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.CLASS_NAME, "nr1-nr1-core")))
    except TimeoutException as te:
      print(f'Error while waiting for page after login - {te}')
      print('console log:')
      for log in self.driver.get_log('browser'):
        print(log)
      self.logout()
      raise


  def logout(self):
    print("Logging out")
    self.driver.get(self.__logout_url)
    assert self.driver.title.strip() == "Log in to New Relic"
    print("Logged out")

  def teardown(self):
    self.driver.quit()


  def start_thread_profiler(self, app_guid: str, jvm_regex: str):
    print("Getting thread profile page")

    # Get thread profile page
    self.driver.get(self.__profiler_base_url + app_guid)

    time.sleep(3)


    # Wait for 'Start a profiling session' text
    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Start a profiling session')]")))
    except TimeoutException as te:
      print('timeout while waiting for thread profile page')
      raise
    print("thread profiler page available. continuing...")
    time.sleep(3)


    # Wait for Next button
    try:
      WebDriverWait(self.driver, self.__page_wait).until(ec.visibility_of_element_located((By.XPATH, "//*[contains(text(), 'Next')]")))
    except TimeoutException as te:
      print(f'timeout while waiting for Next button')
      raise


    # Click Next
    self.driver.find_elements(By.CLASS_NAME, "wnd-CardBaseBody")[0].find_elements(By.CLASS_NAME, "wnd-StackItem")[1].find_elements(By.TAG_NAME, "button")[0].click()
    print("Next clicked")
    time.sleep(3)


    # Get Rows
    rows = self.driver.find_elements(By.CLASS_NAME, "wnd-CardBaseBody")[0].find_elements(By.CLASS_NAME, "wnd-DataTableBody")[0].find_elements(By.CLASS_NAME, "wnd-DataTableRow")
    print("JVM rows are available")
    for row in rows:
      jvm_name = row.find_elements(By.TAG_NAME, "span")[0].find_elements(By.CLASS_NAME, "wnd-DataTableAdditionalValueCell")[0].text
      match = jvm_matcher.search(jvm_regex, jvm_name)
      if match:
        # Click JVM
        row.find_elements(By.TAG_NAME, "input")[0].click()
        print(f'Clicked {jvm_name}')
        break        

    time.sleep(1)


    # Click Start	  
    self.driver.find_elements(By.CLASS_NAME, "wnd-CardBaseBody")[0].find_elements(By.CLASS_NAME, "wnd-Stack--directionHorizontal")[0].find_elements(By.TAG_NAME, "button")[0].click()
    print("Clicked Start")


    # Sleep until profiler is complete
    time.sleep(420)