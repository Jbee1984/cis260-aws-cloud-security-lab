# EventBridge event patterns

An **event pattern** is a filter. EventBridge compares every event on the default event bus against it; an event matches only if **every field in the pattern** matches, and inside a field, matching **any one value in the list** is enough.

Both rules: default event bus · region **us-east-1** · target **SNS topic `cis260-security-alerts`**.
A rule only sees events from its own region, so it must be in the same region as the resources it watches.

| Rule | Status |
|---|---|
| `cis260-ec2-api-changes` — EC2 stop/start | ✅ Verified 2026-10-02 — alert emails at 4:52 PM (StopInstances) and 4:54 PM (StartInstances) |
| `cis260-sg-changes` — security-group inbound changes | ✅ Verified 2026-10-02 — alert emails at 5:31 PM (Authorize) and 5:41 PM (Revoke) |

---

## Rule — `cis260-ec2-api-changes` (EC2 stop/start)

Description: *Email me when my CIS260 lab instance receives a stop or start request.*
File: [`eventbridge-ec2-api-changes.json`](eventbridge-ec2-api-changes.json)

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com"],
    "eventName": ["StopInstances", "StartInstances"],
    "requestParameters": {
      "instancesSet": {
        "items": {
          "instanceId": ["i-085a300c3d2a60c75"]
        }
      }
    }
  }
}
```

| Line | Meaning |
|---|---|
| `"source": ["aws.ec2"]` | The event is about the EC2 service. |
| `"detail-type": ["AWS API Call via CloudTrail"]` | The event is an API call that CloudTrail recorded — someone (or something) *asked* AWS to do it. |
| `"eventSource": ["ec2.amazonaws.com"]` | The call went to the EC2 API. |
| `"eventName": ["StopInstances", "StartInstances"]` | Only stop requests and start requests. Either one matches. |
| `"requestParameters" → "instancesSet" → "items" → "instanceId"` | Only when the request names **my** instance `cis260-target`. In the real CloudTrail event, `items` is a **list** (one request can stop several instances); EventBridge matches if **any** item in the list has this instance ID. |

**Target:** SNS topic `cis260-security-alerts`, input = the full matched event, published using **LabRole** (Learner Lab doesn't allow creating a new role for EventBridge).

**Why the CloudTrail version:** the alert *is* the API record, so the email already contains `userIdentity` (who asked), `eventTime` (when), and `sourceIPAddress` (from where). An alternative is EC2's own "EC2 Instance State-change Notification" event, which arrives without CloudTrail but doesn't say who caused the change.

**Side benefit:** the rule also sees what Learner Lab itself does to the instance.
- **Confirmed for starts (2026-10-22):** clicking Start Lab produced a `StartInstances` call by the lab's automation identity `sys4246727` at 23:43:48 UTC, and this rule emailed it ([ISSUE-02](../docs/issues.md#issue-02--learner-lab-session-expired-during-the-build)).
- **Not yet confirmed for stops:** Learner Lab stops running instances when a session's 4-hour timer runs out. That automatic stop should also be a `StopInstances` call, so this rule should alert on it too. I haven't captured evidence of a timer stop since the rule was created, so this stays unconfirmed.

## Rule — `cis260-sg-changes` (security-group inbound changes)

Description: *Email me when inbound rules are added to or removed from my CIS260 target security group.*

File: [`eventbridge-sg-change-rule.json`](eventbridge-sg-change-rule.json)

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["ec2.amazonaws.com"],
    "eventName": ["AuthorizeSecurityGroupIngress", "RevokeSecurityGroupIngress"],
    "requestParameters": {
      "groupId": ["sg-06e94ae52286f9f2e"]
    }
  }
}
```

| Line | Meaning |
|---|---|
| `"source"`, `"detail-type"`, `"eventSource"` | Same as above: an EC2 API call recorded by CloudTrail. |
| `"eventName": [...]` | Only **adding** an inbound rule (`AuthorizeSecurityGroupIngress`) or **removing** one (`RevokeSecurityGroupIngress`). |
| `"requestParameters" → "groupId"` | Only when the call targets **my** security group `cis260-target-sg`. |

**Why it matters:** an unexpected inbound rule is one of the most common ways a cloud server gets exposed. This rule turns that change into an email within minutes, and the email names who made it.

## Readable alerts — input transformer (ISSUE-03)

Both targets originally used **Matched events**, so each email was raw JSON. The fix (Event buses → default → Rules → the rule → **Edit** → Step 3 → **Additional settings** → **Configure target input** → **Input transformer**):

**`cis260-ec2-api-changes`** — input path:
```json
{
  "action": "$.detail.eventName",
  "instance": "$.detail.requestParameters.instancesSet.items[0].instanceId",
  "who": "$.detail.userIdentity.arn",
  "when": "$.detail.eventTime",
  "ip": "$.detail.sourceIPAddress"
}
```
Template:
```
"CIS260 ALERT: <action> was requested for EC2 instance <instance> by <who> at <when> (UTC) from IP <ip>. Check CloudTrail Event history for full details."
```

**`cis260-sg-changes`** — input path:
```json
{
  "action": "$.detail.eventName",
  "group": "$.detail.requestParameters.groupId",
  "port": "$.detail.requestParameters.ipPermissions.items[0].fromPort",
  "who": "$.detail.userIdentity.arn",
  "when": "$.detail.eventTime",
  "ip": "$.detail.sourceIPAddress"
}
```
Template:
```
"CIS260 ALERT: <action> changed an inbound rule (port <port>) on security group <group> by <who> at <when> (UTC) from IP <ip>. Check CloudTrail Event history for full details."
```

| Part | What it does |
|---|---|
| Input path | Picks single values out of the event with JSON paths (`$` = the whole event; `items[0]` = the first item in a list) |
| Template | A sentence with `<name>` placeholders; each name must match a key in the input path exactly |
| Quotes around the template | Make the output a plain text string, so SNS emails a sentence instead of JSON |

## The rules themselves are audited

Creating, changing, disabling, or deleting a rule is an API call too (`PutRule`, `DisableRule`, `DeleteRule` on events.amazonaws.com), so CloudTrail records it. Verified 2026-10-02: the creation of `cis260-sg-changes` appears as `PutRule` at 22:25:41 UTC with my identity. An attacker who switched off these alerts would leave the same kind of record.

## If an email does not arrive

1. **Wait.** CloudTrail-based events usually reach EventBridge within a few minutes.
2. **Region.** The rule must be in us-east-1, the same region as the resources.
3. **Rule monitoring.** EventBridge → Rules → the rule → **Monitoring**: `Invocations` rising means the rule matched; `FailedInvocations` rising means it matched but could not publish to SNS.
4. **Publishing permission.** The rule publishes using LabRole — LabRole needs `sns:Publish` on the topic. Also check the topic's **Access policy**.
5. **Topic encryption.** If the topic is encrypted with the AWS-managed key `aws/sns`, EventBridge cannot publish to it.
6. **Pattern typos.** Values are case-sensitive (`StopInstances`, `AuthorizeSecurityGroupIngress`). Use **Test pattern** in the rule editor with a sample event.

---

## Final-phase patterns (deployed 2026-10-22, targets = Lambda `cis260-incident-processor`)

All four Lambda-target rules were created and tested on 2026-10-22 ([test plan](../docs/test-plan.md), TEST-05 to TEST-07). The two Lambda rules reuse the patterns above unchanged: `cis260-lambda-sg` uses [`eventbridge-sg-change-rule.json`](eventbridge-sg-change-rule.json) and `cis260-lambda-ec2` uses [`eventbridge-ec2-api-changes.json`](eventbridge-ec2-api-changes.json). Two new patterns:

### `cis260-monitoring-integrity`: someone switched an alert rule off or on

File: [`eventbridge-monitoring-integrity.json`](eventbridge-monitoring-integrity.json)

```json
{
  "source": ["aws.events"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["events.amazonaws.com"],
    "eventName": ["DisableRule", "EnableRule"],
    "requestParameters": {
      "name": ["cis260-sg-changes"]
    }
  }
}
```

| Line | Meaning |
|---|---|
| `"source": ["aws.events"]` | The event is about EventBridge itself |
| `"eventSource": ["events.amazonaws.com"]` | The API call went to EventBridge |
| `"eventName": ["DisableRule", "EnableRule"]` | Switching a rule off, or back on |
| `"requestParameters" → "name"` | Only when the rule being switched is my security-group alert rule |

Why: see [control-improvement.md](../docs/control-improvement.md).

### `cis260-s3-control`: versioning changed on the empty test bucket (supplemental)

File: [`eventbridge-s3-control.json`](eventbridge-s3-control.json)

```json
{
  "source": ["aws.s3"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventSource": ["s3.amazonaws.com"],
    "eventName": ["PutBucketVersioning"],
    "requestParameters": {
      "bucketName": ["cis260-s3-control-test-jbanks"]
    }
  }
}
```

`PutBucketVersioning` is a bucket-level (management) API call, so the existing management trail records it. No S3 data events are needed.

### Checking the patterns

`python -m unittest discover -s lambda -v` includes 5 pattern tests ([`lambda/test_event_patterns.py`](../lambda/test_event_patterns.py)) that check each pattern matches its synthetic event and nothing else. In the console, the rule editor's **Test pattern** button is the final check.

## IAM reference policies — [`iam/`](iam/)

What LabRole *should* be split into in a real account (Learner Lab blocks creating roles, so these are documented, not deployed). Explained in [docs/least-privilege.md](../docs/least-privilege.md).

| File | For | Allows only |
|---|---|---|
| [`iam/lambda-incident-processor-policy.json`](iam/lambda-incident-processor-policy.json) | Lambda execution role | `s3:PutObject` on `cis260-incident-records-jbanks/incidents/*`, `sns:Publish` on the alert topic, writing its own logs |
| [`iam/lambda-trust-policy.json`](iam/lambda-trust-policy.json) | Who may assume that role | `lambda.amazonaws.com`, from my account only |
| [`iam/eventbridge-to-sns-policy.json`](iam/eventbridge-to-sns-policy.json) | Alert rules' target role | `sns:Publish` on `cis260-security-alerts` |
| (AWS managed) `AmazonSSMManagedInstanceCore` | The EC2 instance's role | What the SSM agent needs for Session Manager, nothing else |
