import unittest
import ast
import os
import logging
import boto3
from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError
import json
import nr_thread_profile as src

class TestNRThreadProfile(unittest.TestCase):
    # def get_secret(self, secret_name: str) -> dict:
    #     """
    #         Returns a value from AWS SecretsManager given a secret name
    #         Parameters:
    #             secret_name (str): Name of AWS SecretsManager resource
    #         Returns:
    #             (dict): SecretString value(s)
    #     """
    #     session = boto3.session.Session()
    #     client = session.client(service_name='secretsmanager')

    #     try:
    #         secret_value_response = client.get_secret_value(SecretId=secret_name)
    #     except ClientError as e:
    #         if e.response['Error']['Code'] == 'ResourceNotFoundException':
    #             logging.error("The requested secret " + secret_name + " was not found")
    #         elif e.response['Error']['Code'] == 'InvalidRequestException':
    #             logging.error("The request was invalid due to:", e)
    #         elif e.response['Error']['Code'] == 'InvalidParameterException':
    #             logging.error("The request had invalid params:", e)
    #         elif e.response['Error']['Code'] == 'DecryptionFailure':
    #             logging.error("The requested secret can't be decrypted using the provided KMS key:", e)
    #         elif e.response['Error']['Code'] == 'InternalServiceError':
    #             logging.error("An error occurred on service side:", e)
    #         raise

    #     return json.loads(secret_value_response['SecretString'])


    def setUp(self):
        # try:
        #     self.__api_key = os.environ['NR_API_KEY']
        #     assert self.__api_key is not None
        # except (AssertionError, KeyError):
        #     try: 
        #         self.__api_key = self.get_secret('NRAutomation/NewRelicAPIKey')['api-key']
        #     except NoCredentialsError as nce:
        #         logging.debug('Could not retrieve credentials. Exiting.')
        #         raise SystemExit
        with open('./testEvents.txt', 'r') as stream:
            self.__test_events = ast.literal_eval(stream.read())
        pass

    ## Integration tests
    # def test_get_apm_guid_from_event_tag(self):
    #     # APM Tag Provided
    #     activated_tag = self.__test_events['activated-tag']
    #     self.assertEqual(src.get_apm_guid_from_event(activated_tag, self.__api_key), 'MTA5MjU5MXxBUE18QVBQTElDQVRJT058OTUwNjMyMTc')


    # def test_get_apm_guid_from_event_notag(self):
    #     # APM Tag Not Provided
    #     activated_notag = self.__test_events['activated-notag']
    #     self.assertEqual(src.get_apm_guid_from_event(activated_notag, self.__api_key), 'MTA5MjU5MXxBUE18QVBQTElDQVRJT058OTUwNjMyMTc')


    # def test_get_apm_guid_from_event_invalid(self):
    #     # No valid APM provided raises index error
    #     activated_no_apm = self.__test_events['activated-noAPM']
    #     with self.assertRaises(IndexError):
    #         src.get_apm_guid_from_event(activated_no_apm, self.__api_key)


    # def test_get_apm_guid_from_event_empty(self):
    #     # Empty event raises type error
    #     activated_no_apm = None
    #     with self.assertRaises(TypeError):
    #         src.get_apm_guid_from_event(activated_no_apm, self.__api_key)


    # def test_get_apm_guid_from_event_environment(self):
    #     # Production event in lower environment not allowed
    #     aws_env = os.getenv('AWS_ENVIRONMENT', 'Local')
    #     if aws_env.casefold()[0:4] != 'prod':
    #         production_apm = self.__test_events['production-apm']
    #         with self.assertRaises(AssertionError):
    #             src.get_apm_guid_from_event(production_apm, self.__api_key)


    # def test_get_guid_from_APM_name_valid(self):
    #     # Valid APM Name
    #     apm_name = self.__test_events['activated-tag']['detail']['tags.threadProfileAPM'][0]
    #     self.assertEqual(src.get_guid_from_APM_name(apm_name, self.__api_key), 'MTA5MjU5MXxBUE18QVBQTElDQVRJT058OTUwNjMyMTc')


    # def test_get_guid_from_APM_name_empty(self):
    #     # No APM Name
    #     apm_name = None
    #     with self.assertRaises(IndexError):
    #         src.get_guid_from_APM_name(apm_name, self.__api_key)


    def test_assert_environment_valid(self):
        apm_name = self.__test_events['activated-tag']['detail']['tags.threadProfileAPM'][0]
        raised = False
        try:
            src.assert_environment(apm_name)
        except AssertionError:
            raised = True
        self.assertFalse(raised)


    def test_assert_environment_invalid(self):
        apm_name = self.__test_events['production-apm']['detail']['alertPolicyNames'][0].split(':')[0]
        aws_env = os.getenv('AWS_ENVIRONMENT', 'Local')
        if aws_env.casefold()[0:4] != 'prod':
            with self.assertRaises(AssertionError):
                src.assert_environment(apm_name)


    def test_assert_alert_open_valid(self):
        activated_tag = self.__test_events['activated-tag']
        raised = False
        try:
            src.assert_alert_open(activated_tag)
        except AssertionError:
            raised = True
        self.assertFalse(raised)


    def test_assert_alert_open_invalid(self):
        closed = self.__test_events['closed']
        with self.assertRaises(AssertionError):
            src.assert_alert_open(closed)


    def tearDown(self):
        """Delete resources created by setUp"""
        pass

if __name__ == '__main__':
    unittest.main()
