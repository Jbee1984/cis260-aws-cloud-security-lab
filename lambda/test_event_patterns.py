# Offline check that each EventBridge pattern in config/ matches the events it should, and only those.
# matches() implements only the exact-value matching these patterns use; EventBridge's own
# "Test pattern" button in the console is still the final check before saving a rule.
# Run from the repository root:  python -m unittest discover -s lambda -v

import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "..", "config")
EVENTS = os.path.join(HERE, "events")


def load(folder, name):
    with open(os.path.join(folder, name), encoding="utf-8") as f:
        return json.load(f)


def matches(pattern, event):
    """True if every field in the pattern matches the event (a list in the pattern means 'any of these')."""
    for field, wanted in pattern.items():
        if field not in event:
            return False
        value = event[field]
        if isinstance(wanted, dict):
            # A list in the event (like instancesSet.items) matches if any one element matches.
            candidates = value if isinstance(value, list) else [value]
            if not any(isinstance(c, dict) and matches(wanted, c) for c in candidates):
                return False
        else:
            values = value if isinstance(value, list) else [value]
            if not any(v in wanted for v in values):
                return False
    return True


class EventPatternTests(unittest.TestCase):
    def check(self, pattern_file, should_match, should_not_match):
        pattern = load(CONFIG, pattern_file)
        for name in should_match:
            self.assertTrue(matches(pattern, load(EVENTS, name)), f"{pattern_file} should match {name}")
        for name in should_not_match:
            self.assertFalse(matches(pattern, load(EVENTS, name)), f"{pattern_file} should not match {name}")

    def test_security_group_pattern(self):
        self.check("eventbridge-sg-change-rule.json",
                   ["synthetic-sg-authorize.json"],
                   ["synthetic-sg-other-group.json", "synthetic-ec2-stop.json", "synthetic-disable-rule.json"])

    def test_ec2_pattern(self):
        self.check("eventbridge-ec2-api-changes.json",
                   ["synthetic-ec2-stop.json", "synthetic-ec2-stop-denied.json"],
                   ["synthetic-sg-authorize.json", "synthetic-disable-rule.json"])

    def test_monitoring_integrity_pattern(self):
        self.check("eventbridge-monitoring-integrity.json",
                   ["synthetic-disable-rule.json"],
                   ["synthetic-sg-authorize.json", "synthetic-ec2-stop.json", "synthetic-put-bucket-versioning.json"])

    def test_s3_control_pattern(self):
        self.check("eventbridge-s3-control.json",
                   ["synthetic-put-bucket-versioning.json"],
                   ["synthetic-sg-authorize.json", "synthetic-disable-rule.json"])

    def test_every_config_file_is_valid_json(self):
        for root, _, files in os.walk(CONFIG):
            for name in files:
                if name.endswith(".json"):
                    with open(os.path.join(root, name), encoding="utf-8") as f:
                        json.load(f)


if __name__ == "__main__":
    unittest.main(verbosity=2)
