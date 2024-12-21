#!/usr/bin/env python
# -*- coding: utf-8 -*-

from new_relic_selenium_session import NRSeleniumSession
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
import os


def main():

  # Get secrets
  try:
    nr_usr = os.environ['NR_USER']
    nr_pwd = os.environ['NR_PASSWORD']
    app_guid = os.environ['APP_GUID']
    jvm_regex = os.environ['JVM_REGEX']
  except (AssertionError, KeyError):
    print('ERROR - ' + 'Could not retrieve env vars. Exiting.')
    raise SystemExit

  # Start session 
  print('Starting selenium session')
  session = NRSeleniumSession(pwd=nr_pwd, usr=nr_usr)
  print(f'Successfully started selenium session: {session}')

  # Login 
  try:
    print(f'Logging in to New Relic as {nr_usr}')
    session.login()
    print(f'Logged in')
  except (TimeoutException, NoSuchElementException) as e:
    print('ERROR - ' + 'Could not log in. Ending session and cancelling profile.')
    session.teardown()
    raise SystemExit

  # Start Profile #
  try:
    print(f'Attempting to start thread profiler for {app_guid}')
    session.start_thread_profiler(app_guid, jvm_regex)
  except Exception as e:
    print('ERROR - ' + f'Thread profile not started: {e}')
    try:
      session.teardown()
      raise SystemExit
    except (TimeoutException, AssertionError):
      print('ERROR - ' + 'Could not log out of New Relic. Ending session.')
      session.teardown()
      raise SystemExit
  
  session.teardown()


if __name__ == "__main__":
    main()
