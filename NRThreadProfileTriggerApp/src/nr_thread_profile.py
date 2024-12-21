#!/usr/bin/env python
# -*- coding: utf-8 -*-

from new_relic_selenium_session import NRSeleniumSession
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
import logging
import logging.config
import os
import yaml
import requests


def assert_alert_open(nr_event: dict):
  """
  Asserts that only New Relic alert events with an 'ACTIVATED' state
  are acted upon
  Parameters:
      nr_event (dict): EventBridge payload from New Relic alert
  Raises:
      AssertionError: If event state is not 'activated' (case insensitive)
  """
  casefold_event = {k.casefold():v for k,v in nr_event['detail'].items()}
  event_state = casefold_event['state']
  try:
    assert event_state == 'ACTIVATED'
  except AssertionError:
    logging.warning(f'Event state is {event_state}. State must be "ACTIVATED" to start thread profile')
    raise


def assert_environment(apm_name: str):
  """
  Asserts that only lambda running in Prod AWS environment can start profile for
  Prod applications (based on APM name)
  Parameters:
      apm_name (str): New Relic APM Name
  Raises:
      AssertionError, IndexError: If apm_name doesn't start with 
                                  'prod' substring (case insensitive)
      AttributeError: If apm_name is None
  """
  aws_env = os.getenv('AWS_ENVIRONMENT', 'Local')
  try:
    if apm_name.casefold()[0:4] == 'prod':
      assert aws_env.casefold()[0:4] == 'prod'
  except (AssertionError, IndexError):
    logging.error(f'Permission denied. Cannot start thread profile for production app {apm_name} in environment {aws_env}')
    raise
  except AttributeError:
    logging.warning(f'apm_name not provided')
  pass


def get_guid_from_APM_name(apm_name: str, nr_gql_key: str) -> str:
  """
    Returns the New Relic Globally Unique Identifier (GUID) given an APM name
    Parameters:
        apm_name (str): New Relic APM Name
        nr_gql_key (str): New Relic API Key
    Returns:
        guid (str)
  """
  url = 'https://api.newrelic.com/graphql'
  query = f'''{{
              actor {{
                entitySearch(query: "name = \u0027{apm_name}\u0027 AND domain = \u0027APM\u0027") {{
                  results {{
                    entities {{
                      guid
                      name
                    }}
                  }}
                }}
              }}
            }}'''
  headers = {'Content-Type': 'application/json', 'API-Key': f'{nr_gql_key}'}
  r = requests.post(url, headers=headers, json={'query': query})
  logging.info(f'NerdGraph response: {r.text}')

  try:
    guid = r.json()['data']['actor']['entitySearch']['results']['entities'][0]['guid']
  except (KeyError, IndexError) as e:
    logging.error(f'APM name {apm_name} not found in NR: {e}')
    raise

  return guid


def get_apm_guid_from_event(nr_event: dict, nr_gql_key: str) -> str:
  """
  Returns the New Relic Globally Unique Identifier (GUID) given an
  AWS EventBridge event payload from a New Relic alert workflow
  Parameters:
      nr_event (dict): EventBridge payload from New Relic alert
      nr_gql_key (str): New Relic API Key
  Returns:
      guid (str)
  """
  try:
    casefold_event = {k.casefold():v for k,v in nr_event['detail'].items()}
  except (TypeError, KeyError) as e:
    logging.error(f'Not a valid event: {e}')
    raise
  logging.debug(f'Casefold event: {casefold_event}')
  apm_name_tag = casefold_event['tags.threadprofileapm'][0] if 'tags.threadprofileapm' in casefold_event else None
  logging.info(f'APM Name from apm tag: {apm_name_tag}')
  apm_name_policy = casefold_event['alertpolicynames'][0].split(':')[0]
  logging.info(f'APM Name from alertPolicyNames field: {apm_name_policy}')
  
  guid = None
  if apm_name_tag is not None:
    logging.info(f'Retrieving guid for APM Name from apm tag: {apm_name_tag}')
    try:
      assert_environment(apm_name_tag)
      guid = get_guid_from_APM_name(apm_name_tag, nr_gql_key)
      logging.info(f'Using guid {guid} to start thead profile for {apm_name_tag}')
    except AssertionError:
      logging.warning(f'Cannot start profile for production apm tag value in current environment: {apm_name_tag}')
    except (KeyError, IndexError):
      logging.warning(f'Could not retrieve guid for apm_name field value: {apm_name_tag}')
  
  if guid is None:
    logging.info(f'Retrieving guid for APM Name from alertPolicyNames field: {apm_name_policy}')
    try:
      assert_environment(apm_name_policy)
      guid = get_guid_from_APM_name(apm_name_policy, nr_gql_key)
      logging.info(f'Using guid {guid} to start thead profile for {apm_name_tag}')
    except AssertionError:
      logging.error(f'Cannot start profile for production alertpolicynames field value in current environment: {apm_name_policy}')
      raise
    except (KeyError, IndexError):
      logging.error(f'Could not retrieve guid for alertpolicynames field value: {apm_name_policy}')
      raise
    
  try:
    assert guid
  except AssertionError as ae:
    logging.error(f'Guid not found. Could not start thread profile')
    raise

  return guid


def main(event: dict, context: dict=None):
  """
  Event handler for Lambda events. Starts a New Relic thread profile for the 
  application specified by the New Relic alert event payload
  Parameters:
      event (dict): EventBridge payload from New Relic alert
      context (dict): New Relic API Key
  """
  # Logging setup #
  with open('./logging.yaml', 'r') as stream:
    config = yaml.load(stream, Loader=yaml.FullLoader)
  logging.config.dictConfig(config)

  logging.debug(f'Event: {event}')
  logging.debug(f'Context: {context}')


  # Check if this is an alert open or close event #
  try:
    assert_alert_open(event)
  except AssertionError as ae:
    logging.info(f'Alert close event. Exiting. : {ae}')
    raise SystemExit

  # Get secrets #
  try:
    nr_pwd = os.environ['NR_PASSWORD']
    nr_usr = os.environ['NR_USER']
    api_key = os.environ['NR_API_KEY']
    assert None not in (nr_pwd, nr_usr, api_key)
  except (AssertionError, KeyError):
    logging.error('Could not retrieve credentials. Exiting.')
    raise SystemExit

  # Get APM GUID #
  logging.info('Getting apm guid from event')
  try:
    app_guid = get_apm_guid_from_event(nr_event=event, nr_gql_key=api_key)
  except (KeyError, IndexError, TypeError, AssertionError):
    logging.error('Could not get apm guid from event. Exiting.')
    raise SystemExit

  # Start session #
  run_headless = True
  logging.info('Starting selenium session')
  session = NRSeleniumSession(pwd=nr_pwd, usr=nr_usr, headless=run_headless)
  logging.info(f'Successfully started selenium session: {session}')

  # Login #
  try:
    logging.info(f'Logging in to New Relic as {nr_usr}')
    session.login()
    logging.info(f'Logged in to New Relic as {nr_usr}')
  except (TimeoutException, NoSuchElementException) as e:
    logging.error('Could not log in. Ending session and cancelling profile.')
    session.teardown()
    raise SystemExit

  # Start Profile #
  try:
    logging.info(f'Attempting to start thread profiler for {app_guid}')
    session.start_thread_profiler(app_guid)
  except Exception as e:
    logging.error(f'Thread profile not started: {e}')
    logging.info(f'Logging out of New Relic')
    try:
      session.logout()
      session.teardown()
      raise SystemExit
    except (TimeoutException, AssertionError):
      logging.error('Could not log out of New Relic. Ending session.')
      session.teardown()
      raise SystemExit
  
  # Logout & exit browser #
  logging.info(f'Logging out of New Relic')
  try:
    session.logout()
  except (TimeoutException, AssertionError):
    logging.error('Could not log out of New Relic. Ending session.')
  session.teardown()


if __name__ == "__main__":
    sample_event = {
      'version': '0', 'id': 'dbd0e7c4-3c1b-4f20-23c8-8c024e04a722', 'detail-type': 'NewRelicEvent', 
      'source': 'aws.partner/newrelic.com/1092591/StartNewRelicThreadProfile', 'account': '850996745251', 'time': '2022-10-17T17:19:53Z', 
      'region': 'us-east-2', 'resources': [], 
      'detail': {
        'id': '2c111856-2829-4235-a26b-85511bf74c08', 
        'issueUrl': 'https://radar-api.service.newrelic.com/accounts/1/issues/0ea2df1c-adab-45d2-aae0-042b609d2322?notifier=SLACK&action=', 
        'tags.threadProfileAPM': ['DEV_MCC_DPIM-MDM_5777'], 
        'title': "Monitor failed for location nw_cpm_prod005_01 on 'PROD_CSB_KnowledgeAdvanced_7979:AutomatedTesting'", 
        'priority': 'CRITICAL', 'impactedEntities': ['PROD_CSB_KnowledgeAdvanced_7979:AutomatedTesting'], 'totalIncidents': 1, 'state': 'ACTIVATED', 
        'trigger': 'STATE_CHANGE', 'isCorrelated': False, 'createdAt': 1666026872359, 'updatedAt': 1666026987511, 'sources': ['newrelic'], 
        'alertPolicyNames': ['PROD_CSB_KnowledgeAdvanced_7979:Email'], 'alertConditionNames': ['P&C Automated testing failed'], 
        'workflowName': 'DBA Team workflow'
      }
    }
    main(sample_event)
