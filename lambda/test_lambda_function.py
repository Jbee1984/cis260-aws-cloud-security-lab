# Offline tests for lambda_function.py.
# They replace boto3 with fake S3 and SNS clients, so they need no AWS account, no internet, and cost nothing.
# Run from the repository root:  python -m unittest discover -s lambda -v

import copy
import json
import os
import sys
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(HERE, "events")


class FakeS3:
    def __init__(self, fail=False):
        self.objects = {}
        self.fail = fail

    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail:
            raise RuntimeError("AccessDenied (simulated S3 failure)")
        self.objects[(Bucket, Key)] = Body


class FakeSNS:
    def __init__(self):
        self.messages = []

    def publish(self, TopicArn, Subject, Message):
        self.messages.append({"TopicArn": TopicArn, "Subject": Subject, "Message": Message})


# Stand-in for boto3: lambda_function.py calls boto3.client("s3") and boto3.client("sns") when it is imported.
fake_boto3 = types.ModuleType("boto3")
fake_boto3.client = lambda service: FakeS3() if service == "s3" else FakeSNS()
sys.modules["boto3"] = fake_boto3

# The same environment variables the real function gets in the Lambda console (AWS_REGION is set by Lambda itself).
os.environ.update({
    "AWS_REGION": "us-east-1",
    "LAB_ACCOUNT_ID": "235317051044",
    "TARGET_GROUP_ID": "sg-06e94ae52286f9f2e",
    "TARGET_INSTANCE_ID": "i-085a300c3d2a60c75",
    "MONITORED_RULE_NAME": "cis260-sg-changes",
    "TEST_BUCKET_NAME": "cis260-s3-control-test-jbanks",
    "INCIDENT_BUCKET": "cis260-incident-records-jbanks",
    "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:235317051044:cis260-security-alerts",
})
sys.path.insert(0, HERE)
import lambda_function  # noqa: E402  (must come after the fake boto3 is in place)


def load(name):
    with open(os.path.join(EVENTS, name), encoding="utf-8") as f:
        return json.load(f)


class IncidentProcessorTests(unittest.TestCase):
    def setUp(self):
        self.s3 = FakeS3()
        self.sns = FakeSNS()
        lambda_function.s3 = self.s3
        lambda_function.sns = self.sns

    def run_event(self, event):
        return lambda_function.lambda_handler(event, None)

    def assert_ignored(self, result, reason):
        self.assertEqual(result, {"status": "ignored", "reason": reason})
        self.assertEqual(self.s3.objects, {}, "an ignored event must not write evidence")
        self.assertEqual(self.sns.messages, [], "an ignored event must not send email")

    # --- events that belong to my lab are recorded and alerted ---

    def test_security_group_change_is_recorded_and_emailed(self):
        result = self.run_event(load("synthetic-sg-authorize.json"))
        key = "incidents/2026-10-22/AuthorizeSecurityGroupIngress-synthetic-0001-sg-authorize.json"
        self.assertEqual(result, {"status": "recorded", "key": key})
        self.assertIn(("cis260-incident-records-jbanks", key), self.s3.objects)
        self.assertEqual(len(self.sns.messages), 1)
        msg = self.sns.messages[0]
        self.assertEqual(msg["TopicArn"], "arn:aws:sns:us-east-1:235317051044:cis260-security-alerts")
        self.assertEqual(msg["Subject"], "CIS260 incident: AuthorizeSecurityGroupIngress")
        self.assertIn("AuthorizeSecurityGroupIngress succeeded", msg["Message"])
        self.assertIn("Resource: sg-06e94ae52286f9f2e", msg["Message"])
        self.assertIn("CloudTrail event ID: synthetic-0001-sg-authorize", msg["Message"])
        self.assertIn("From IP: 203.0.113.10", msg["Message"])

    def test_saved_record_is_the_complete_unchanged_event(self):
        event = load("synthetic-sg-authorize.json")
        result = self.run_event(event)
        body = self.s3.objects[("cis260-incident-records-jbanks", result["key"])]
        self.assertEqual(json.loads(body.decode("utf-8")), event)

    def test_instance_stop_is_recorded(self):
        result = self.run_event(load("synthetic-ec2-stop.json"))
        self.assertEqual(result["status"], "recorded")
        self.assertIn("Resource: i-085a300c3d2a60c75", self.sns.messages[0]["Message"])

    def test_disabling_the_monitored_alert_rule_is_recorded(self):
        result = self.run_event(load("synthetic-disable-rule.json"))
        self.assertEqual(result["status"], "recorded")
        self.assertIn("DisableRule succeeded", self.sns.messages[0]["Message"])
        self.assertIn("Resource: cis260-sg-changes", self.sns.messages[0]["Message"])

    def test_enabling_the_monitored_alert_rule_is_recorded(self):
        event = load("synthetic-disable-rule.json")
        event["detail"]["eventName"] = "EnableRule"
        event["detail"]["eventID"] = "synthetic-0007-enable-rule"
        self.assertEqual(self.run_event(event)["status"], "recorded")

    def test_versioning_change_on_test_bucket_is_recorded(self):
        result = self.run_event(load("synthetic-put-bucket-versioning.json"))
        self.assertEqual(result["status"], "recorded")
        self.assertIn("Resource: cis260-s3-control-test-jbanks", self.sns.messages[0]["Message"])

    def test_denied_call_is_reported_as_failed_not_as_a_change(self):
        self.run_event(load("synthetic-ec2-stop-denied.json"))
        self.assertIn("StopInstances FAILED (Client.UnauthorizedOperation)", self.sns.messages[0]["Message"])

    # --- events outside my lab are ignored, with no record and no email ---

    def test_other_security_group_is_ignored(self):
        self.assert_ignored(self.run_event(load("synthetic-sg-other-group.json")), "resource")

    def test_other_instance_is_ignored(self):
        event = load("synthetic-ec2-stop.json")
        event["detail"]["requestParameters"]["instancesSet"]["items"][0]["instanceId"] = "i-0000000000000000a"
        self.assert_ignored(self.run_event(event), "resource")

    def test_other_alert_rule_is_ignored(self):
        event = load("synthetic-disable-rule.json")
        event["detail"]["requestParameters"]["name"] = "some-other-rule"
        self.assert_ignored(self.run_event(event), "resource")

    def test_other_account_is_ignored(self):
        event = load("synthetic-sg-authorize.json")
        event["account"] = "111122223333"
        self.assert_ignored(self.run_event(event), "account")

    def test_other_region_is_ignored(self):
        event = load("synthetic-sg-authorize.json")
        event["region"] = "us-west-2"
        self.assert_ignored(self.run_event(event), "region")

    def test_unwatched_api_call_is_ignored(self):
        event = load("synthetic-sg-authorize.json")
        event["detail"]["eventName"] = "CreateTags"
        self.assert_ignored(self.run_event(event), "event")

    # --- missing or broken input does not crash the function ---

    def test_missing_request_parameters_is_ignored(self):
        event = load("synthetic-sg-authorize.json")
        event["detail"]["requestParameters"] = None
        self.assert_ignored(self.run_event(event), "resource")

    def test_empty_instance_list_is_ignored(self):
        event = load("synthetic-ec2-stop.json")
        event["detail"]["requestParameters"]["instancesSet"]["items"] = []
        self.assert_ignored(self.run_event(event), "resource")

    def test_missing_identity_and_ip_still_alerts_with_unknown(self):
        event = load("synthetic-sg-authorize.json")
        del event["detail"]["userIdentity"]
        del event["detail"]["sourceIPAddress"]
        self.run_event(event)
        self.assertIn("Who: unknown", self.sns.messages[0]["Message"])
        self.assertIn("From IP: unknown", self.sns.messages[0]["Message"])

    # --- failures and duplicates behave the way the documentation says ---

    def test_storage_failure_raises_and_sends_no_email(self):
        lambda_function.s3 = FakeS3(fail=True)
        with self.assertRaises(RuntimeError):
            self.run_event(load("synthetic-sg-authorize.json"))
        self.assertEqual(self.sns.messages, [], "no alert may claim evidence was saved when it was not")

    def test_same_event_twice_reuses_the_same_record_name(self):
        event = load("synthetic-sg-authorize.json")
        first = self.run_event(copy.deepcopy(event))
        second = self.run_event(copy.deepcopy(event))
        self.assertEqual(first["key"], second["key"])
        self.assertEqual(len(self.s3.objects), 1, "a retried event overwrites one record instead of adding a second")
        self.assertEqual(len(self.sns.messages), 2, "a retry can still send a second email (documented limitation)")


if __name__ == "__main__":
    unittest.main(verbosity=2)
