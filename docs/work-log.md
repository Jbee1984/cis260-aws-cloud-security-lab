# Work log

Times are shown in local time (CDT, UTC−5) and UTC, because AWS records everything in UTC.
Each entry records the goal, what changed and why, evidence, problems, budget, and the next task.

---

## 2026-10-02 (Fri) — Build day: network, server access, logging, alerting

**Goal:** finish the foundation, logging, and alerting promised for the midterm, then run the first two controlled tests.
**Learner Lab session started:** 10:28 AM CDT (15:28 UTC) — taken from the `sessionContext.creationDate` field in my own CloudTrail records.

| Time (CDT) | Time (UTC) | What I did | Why | Evidence |
|---|---|---|---|---|
| 11:23 AM | 16:23 | Created internet gateway `cis260-Lab-igw` and attached it to `cis260-security-VPC` | Gives the VPC a path to AWS public service endpoints | `2026-10-02_01_gateway-attached.png` |
| 11:29 AM | 16:29 | Created route table `cis260-lab-rt` with route 0.0.0.0/0 → internet gateway | Without a default route, traffic for addresses outside 10.26.0.0/16 has nowhere to go | `2026-10-02_02_route-table-routes.png` |
| 11:32 AM | 16:32 | Explicitly associated `cis260-lab-subnet` (10.26.1.0/24) with `cis260-lab-rt` | A custom route table only applies to subnets associated with it | `2026-10-02_03_subnet-association.png` |
| 11:44 AM | 16:44 | Created security group `cis260-target-sg` with **no inbound rules** | Nothing on the internet can start a connection to the server; no SSH | `2026-10-02_04_security-group-inbound.png` |
| 11:45 AM | 16:45 | Replaced the default "all traffic" outbound rule with **HTTPS (TCP 443) only** | Least privilege — Session Manager only needs outbound HTTPS | `2026-10-02_05_security-group-outbound.png` |
| 12:11 PM | 17:11 | Launched `cis260-target` (t3.micro, Amazon Linux 2023, role LabRole, IMDSv2 required); all 3 status checks passed | Small, low-cost target with the lab-provided role that allows Systems Manager | `2026-10-02_06_ec2-running.png` |
| 12:16 PM | 17:15 | Connected with Session Manager; ran `whoami` (→ `ssm-user`), `cat /etc/os-release`, `date -u` | Proves access works with zero inbound rules and no SSH keys | `2026-10-02_07_session-manager-connected.png` |
| 12:31 PM | 17:31 | CloudTrail console showed **AccessDeniedException** | — see [ISSUE-01](issues.md#issue-01--cloudtrail-console-accessdeniedexception) | `2026-10-02_issue-01_cloudtrail-access-denied.png` |
| 12:39 PM | 17:39 | Trail `cis260-management-trail` created: management events, multi-region, delivering to the S3 bucket, status **Logging** | Event history only keeps 90 days and can't be exported as evidence; a trail keeps a permanent copy in S3 | `2026-10-02_08_cloudtrail-logging.png` |
| 12:42 PM | 17:42 | First CloudTrail log file delivered to S3 | Delivery verified, not just "logging enabled" | `2026-10-02_09_cloudtrail-log-delivery.png` |
| 12:45 PM | 17:45 | Downloaded and read the log file: 7 records, including `GetBucketVersioning` by my lab role and 4 `AccessDenied` console calls | Confirms I can answer who / what / when / which resource from the evidence | [redacted sample](../evidence/logs/2026-10-02_cloudtrail-sample-redacted.json) |
| 12:59 PM | 17:59 | Verified **Block all public access: On** and the bucket policy (only CloudTrail may write, only for my trail) | Evidence storage must never be public | `2026-10-02_10_s3-block-public-access.png` |
| 1:01 PM | 18:01 | Verified default encryption **SSE-S3** (SSE-C blocked) | Logs encrypted at rest | `2026-10-02_11_s3-default-encryption.png` |
| 1:03 PM | 18:03 | Verified **versioning: Enabled** | Evidence can't be silently overwritten or deleted | `2026-10-02_12_s3-versioning.png` |
| 1:34 PM | 18:34 | Created SNS topic `cis260-security-alerts`; email subscription **Confirmed** | Alert delivery channel | `2026-10-02_13_sns-subscription-confirmed.png` |
| 1:36 PM | 18:36 | Published manual test message **SNS-01**; email received | Proves the subscription works (not yet a real AWS-triggered alert) | `2026-10-02_14_sns-test-email.png` |
| ~2:28 PM | ~19:28 | Learner Lab session reached its 4-hour limit; the lab showed a red status dot and timer 0:00 at 3:40 PM | — see [ISSUE-02](issues.md#issue-02--learner-lab-session-expired-during-the-build) | Learner Lab page |
| TODO | TODO | Started a new Learner Lab session (Start Lab) | The previous session had expired | — |
| 4:24 PM | 21:24 | Created EventBridge rule `cis260-ec2-api-changes` (CloudTrail `StopInstances`/`StartInstances` for `cis260-target`), Enabled | A real stop/start request should now produce an email | `2026-10-02_15_eventbridge-ec2-rule.png` |
| 4:26 PM | 21:26 | Verified the rule target: SNS topic `cis260-security-alerts`, input = matched event, role LabRole | EventBridge needs permission to publish; LabRole provides it | `2026-10-02_16_eventbridge-sns-target.png` |
| 4:47 PM | 21:47 | Created VPC Flow Log `cis260-subnet-flowlog`: all traffic, 1-minute aggregation, to S3 bucket `cis260-flowlogs-jbanks-20261002`; state Active | Network-traffic evidence for Test 3 (rejected vs. allowed traffic) | `2026-10-02_17_vpc-flow-log.png` |
| 4:54 PM | 21:54 | **TEST-02:** stopped `cis260-target` from the EC2 console; state Stopped, public IPv4 released | Controlled outage | `2026-10-02_18_test2-instance-stopped.png` |
| 4:56 PM | 21:56 | **TEST-02 correction:** started `cis260-target`; state Running, status checks initializing, new public IPv4 assigned | Recovery | `2026-10-02_19_test2-instance-running.png` |
| 4:58 PM | 21:58 | **TEST-02 retest:** Session Manager reconnected; `date -u` = 21:58:10 UTC, `whoami` → `ssm-user`; private address unchanged after stop/start, public address changed | Access recovered with no inbound rules | `2026-10-02_20_test2-session-manager-reconnected.png` |
| 5:11 PM | 22:11 | Created CloudWatch alarm `cis260-cpu-high`: CPUUtilization > 10 for 1 datapoint within 5 minutes; actions enabled; Insufficient data at 22:11:08 UTC, then **OK** at 22:12:01 UTC once the first datapoints arrived | First metric alarm, for Test 4 (controlled CPU load) | `2026-10-02_21_cloudwatch-cpu-alarm.png` |
| 5:36 PM | 21:57 | Found the `StartSession` record (ssm.amazonaws.com) in CloudTrail Event history for the 21:57:56 UTC reconnect — my identity, read-only false | Proves Session Manager access is audited, not just allowed | `2026-10-02_25_cloudtrail-startsession.png` |
| 5:37 PM | 21:54:30 | Found `StartInstances` in CloudTrail Event history: my identity, ec2.amazonaws.com, resource `cis260-target` | Shows who restarted the server and exactly when | `2026-10-02_26_cloudtrail-startinstances.png` |
| 6:50 PM | — | **ISSUE-03 fix:** changed `cis260-ec2-api-changes` target input from Matched events to an input transformer (readable one-line alert) | Raw JSON alerts were hard to read; the alert should be usable by anyone | `2026-10-02_34_eventbridge-ec2-transformer.png` |
| 7:11 PM | — | **ISSUE-03 fix:** same input-transformer change on `cis260-sg-changes` | Both alert rules now send readable alerts | `2026-10-02_35_eventbridge-sg-transformer.png` |
| 7:22 PM | 00:22 (Oct 3) | **ISSUE-03 retest:** added the 8080 test rule again; the alert email now arrives as one readable sentence | Fix verified for `cis260-sg-changes` | `2026-10-02_36_readable-alert-sg-authorize.png` |
| 7:23 PM | 00:23 (Oct 3) | Removed the 8080 test rule; readable RevokeSecurityGroupIngress alert received; security group back to 0 inbound rules | Fix verified both ways for `cis260-sg-changes`; cleanup | `2026-10-02_37_readable-alert-sg-revoke.png` |
| 7:29 PM | 00:29 (Oct 3) | Stopped `cis260-target` (end-of-day cleanup); readable StopInstances alert received | ISSUE-03 verified for both rules; instance stopped | `2026-10-02_38_readable-alert-ec2-stop.png` |
| 7:30 PM | 00:30 (Oct 3) | Started `cis260-target` again; readable StartInstances alert received | Both EC2 actions confirmed in the new readable format | `2026-10-02_39_readable-alert-ec2-start.png` |
| TODO | — | Stop the instance (or End Lab, which stops it automatically — check who the alert names), record the final credit | Shutdown | — |
| 6:11 PM | — | Found all four automatic alert emails: StopInstances 4:52 PM, StartInstances 4:54 PM, AuthorizeSecurityGroupIngress 5:31 PM, RevokeSecurityGroupIngress 5:41 PM — each within a minute of the action | **Both alert rules verified end to end; TEST-01 and TEST-02 PASS** | `2026-10-02_30` to `_33_alert-email-*.png` |
| 5:18 PM | 22:18 | **TEST-01 baseline:** `cis260-target-sg` has no inbound rules | Starting point for the security-group test | `2026-10-02_22_test1-sg-baseline.png` |
| 5:45 PM | 22:41:07 | Found `RevokeSecurityGroupIngress` in CloudTrail for the rule removal — my identity, resource `cis260-target-sg` | Exact time and identity for the correction | `2026-10-02_29_cloudtrail-revoke-sg.png` |
| 5:41 PM | 22:41 | **TEST-01 correction + retest:** removed the TCP 8080 test rule; `cis260-target-sg` back to 0 inbound rules (1 outbound) | Restore the baseline; no test rule left behind | `2026-10-02_27_test1-sg-restored.png` |
| 5:32 PM | 22:32 | **TEST-01 change:** added inbound rule Custom TCP 8080, source = `cis260-target-sg` itself (`sgr-0b9dcb7481490a2ec`) | Controlled change — nothing outside the group can use it | `2026-10-02_24_test1-rule-added.png` |
| 5:44 PM | 22:25:41 | Found the `PutRule` record (events.amazonaws.com) in CloudTrail for the creation of `cis260-sg-changes` — my identity | Changes to the monitoring itself are audited: deleting or disabling an alert rule would show up the same way | `2026-10-02_28_cloudtrail-putrule.png` |
| 5:26 PM | 22:26 | Created EventBridge rule `cis260-sg-changes`: CloudTrail `AuthorizeSecurityGroupIngress`/`RevokeSecurityGroupIngress` for `cis260-target-sg`, Enabled | Inbound-rule changes → email | `2026-10-02_23_eventbridge-sg-rule.png` |
| TODO | TODO | Run Test 1 and Test 2 | Midterm requirement: two controlled tests | TODO |

**Problems:** [ISSUE-01](issues.md#issue-01--cloudtrail-console-accessdeniedexception) — CloudTrail console AccessDeniedException.

**Budget:** Learner Lab showed **Used $1.4 of $50** at 3:40 PM CDT.

**Shutdown:** TODO — stop `cis260-target` before ending the lab session (see [cleanup checklist](cleanup-checklist.md)).

**Next task:** finish TEST-02 evidence (alert emails, CloudTrail records) → security-group alert rule → TEST-01 → incident records IR-01 and IR-02.

---

## Before 2026-10-02 — Retrospective: VPC and subnet

Created `cis260-security-VPC` (10.26.0.0/16) and `cis260-lab-subnet` (10.26.1.0/24) in us-east-1.
TODO: add the exact date and the screenshots from that session.
