# IR-01 — Unexpected inbound rule on the lab server's security group

| Field | Entry |
|---|---|
| Incident ID | IR-01 (controlled test TEST-01) |
| Date | 2026-10-02 |
| Severity | Low — planned test; the rule's source was the security group itself, so nothing was exposed to the internet |
| Status | ✅ Closed — **PASS** |
| Affected resource | Security group `cis260-target-sg` (attached to `cis260-target`) |
| Detection source | EventBridge rule `cis260-sg-changes` (CloudTrail `AuthorizeSecurityGroupIngress` / `RevokeSecurityGroupIngress`) → SNS email |
| Analyst | Jeremiah Banks |

## Summary
At 22:31:23 UTC an inbound rule allowing TCP 8080 (source: the group itself) was added to `cis260-target-sg`. An alert email arrived the same minute, and CloudTrail identified the caller as my lab session. I removed the rule at 22:41:07 UTC and confirmed the group was back to 0 inbound rules. The rule was open for 9 minutes 44 seconds, and only to members of the same group, never the internet.

## Timeline (UTC)
| Time | Event | Source |
|---|---|---|
| 22:18 | Baseline confirmed: 0 inbound rules | `2026-10-02_22_test1-sg-baseline.png` |
| 22:31:23 | Rule added: Custom TCP 8080, source `cis260-target-sg` (`sgr-0b9dcb7481490a2ec`) — CloudTrail `AuthorizeSecurityGroupIngress` (event ID b5ce2629-118d-4076-9af6-9ea4cbd731e2) | `2026-10-02_24_test1-rule-added.png` (22:32) |
| 22:31 | **Alert email received** (5:31 PM CDT) — `AuthorizeSecurityGroupIngress`, port 8080, my identity | `2026-10-02_32_alert-email-sg-authorize.png` |
| 22:41:07 | Rule removed (correction) — CloudTrail `RevokeSecurityGroupIngress` (event ID 70487a71-e80a-496a-ad32-090f70210322), my identity, resource `cis260-target-sg`, no error code | `2026-10-02_29_cloudtrail-revoke-sg.png` |
| 22:41 | **Second alert email** (5:41 PM CDT) — `RevokeSecurityGroupIngress` | `2026-10-02_33_alert-email-sg-revoke.png` |
| 22:41 | Retest: 0 inbound rules ("No security group rules found"), outbound unchanged | `2026-10-02_27_test1-sg-restored.png` |

**Detection time** (change → email): under 1 minute (22:31:23 UTC → email at 5:31 PM CDT).

## Investigation — the five questions
| Question | Answer | Where it came from |
|---|---|---|
| What changed? | Inbound rule TCP 8080 added to `cis260-target-sg` | CloudTrail `requestParameters.ipPermissions` |
| Who changed it? | `assumed-role/voclabs/…Jeremiah_Banks` (my lab session) | CloudTrail `userIdentity.arn` |
| When? | 2026-10-02 22:31:23 UTC | CloudTrail `eventTime` |
| From where? | Console (`userAgent`); source IP shown in the CloudTrail record (screenshot 29) | CloudTrail |
| Expected or unexpected? | Expected — planned test TEST-01 | Test plan |

## Correction and recovery
- Correction: removed the TEST-01 rule at 22:41:07 UTC (CloudTrail `RevokeSecurityGroupIngress`, my identity).
- Verification: confirmed. Inbound rules back to 0 (screenshot 27), `RevokeSecurityGroupIngress` recorded (screenshot 29), second alert email received at 5:41 PM CDT (screenshot 33).
- Later check: the same rule was added and removed again at 00:22–00:23 UTC on Oct 3 to test the readable alerts (ISSUE-03); the group ended at 0 inbound rules (screenshot 37).

## Lessons learned
- **Detection was fast, but correction was manual.** The email arrived within a minute; removing the rule depended on me and took about 10 minutes. That gap is why the next step is a case record for every alert (Lambda, TEST-06), so the investigation starts with the evidence already gathered.
- **The first alert was accurate but hard to read.** It was the raw JSON event. That led to ISSUE-03 and the one-sentence alerts.
- **If this change had not been planned,** I would:
  1. Check who made it (`userIdentity`) and from where (`sourceIPAddress`) against expected admins and change tickets.
  2. Look for related activity by the same identity in CloudTrail: other rule changes, new instances, new keys.
  3. Remove the rule.
  4. Treat it as a possible credential compromise and escalate if the identity or IP wasn't recognized.

## Evidence
| File | What it shows |
|---|---|
| `2026-10-02_23_eventbridge-sg-rule.png` | EventBridge rule configuration |
| `2026-10-02_24_test1-rule-added.png` | Inbound rule added |
| `2026-10-02_32_alert-email-sg-authorize.png` | Alert email (`AuthorizeSecurityGroupIngress`) |
| `2026-10-02_29_cloudtrail-revoke-sg.png` | CloudTrail record (Revoke); the Authorize record is inside the alert email |
| `2026-10-02_33_alert-email-sg-revoke.png` | Second alert email (`RevokeSecurityGroupIngress`) |
| `2026-10-02_27_test1-sg-restored.png` | Retest — 0 inbound rules |
