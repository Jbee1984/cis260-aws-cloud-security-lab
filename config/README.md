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

**Side benefit (to verify):** Learner Lab stops running instances when a session's 4-hour timer runs out. That automatic stop should also be a `StopInstances` call, so this rule should alert on it too — and CloudTrail would show which identity made it. Check the next time a session times out.

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
