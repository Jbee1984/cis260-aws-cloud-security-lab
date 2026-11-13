# Work log

Times are shown in local time (CDT, UTC−5) and UTC, because AWS records everything in UTC.
Each entry records the goal, what changed and why, evidence, problems, budget, and the next task. Newest first. Entries are written on or right after the day they describe; anything not written down at the time is marked "not recorded" instead of guessed.

---

## 2026-11-12 to 11-13 (Thu–Fri) — Documentation pass and repository update (no AWS work)

**Goal:** bring the repository up to date with everything from the final lab session and make the main page usable by someone who has never seen the project.

| What I did | Why | Evidence |
|---|---|---|
| Published the post-session evidence: the Learner Lab credit screenshot and the three alert emails (`2026-10-22_72` to `_75`), with their hashes in the manifest, plus the cost-log and work-log updates | They were captured after the first push on October 22 | Commit `08d8b51` |
| Added **Quickstart**, **Setting up a workspace**, **Troubleshooting**, and **FAQ** sections to the main README | The final-paper rubric asks for documentation on the main repository page; the troubleshooting rows come from this project's own issues | [README](../README.md) |
| Cleaned up stale wording: the Oct 2 cost-log entry (instance state confirmed on Oct 22), the event-pattern notes (Lambda rules are deployed, not planned; Start Lab identity confirmed), and the timeline | The repository should describe the lab as it is now | [cost-log.md](cost-log.md), [config/README.md](../config/README.md) |
| Re-checked all 78 evidence files against the manifest hashes. One log file's published copy didn't match; fixed with `.gitattributes` and verified. Corrected 13 descriptions that still said parts of the October 2 screenshots were hidden | The manifest has to describe exactly what is published | [ISSUE-04](issues.md#issue-04--a-published-evidence-file-didnt-match-its-manifest-hash---fixed-and-verified), [manifest](../evidence/manifest.md) |
| Re-ran the offline tests: **23 passed, 0 failed**; checked every link in the Markdown files | Confirm nothing broke | `python -m unittest discover -s lambda -v` |

**Problems:** [ISSUE-04](issues.md#issue-04--a-published-evidence-file-didnt-match-its-manifest-hash---fixed-and-verified) (a published log file's hash didn't match the manifest; fixed).
**Budget:** no AWS resources were started. The target server has been stopped since 2026-10-22, 00:25:57 UTC.
**Schedule note:** the final presentation dates are December 4 and December 11; the paper, repository, and slides are due December 4 before class.
**Next task:** record the demo and link it from the README.

---

## 2026-10-22 (Thu) — Lambda written and tested; evening lab session: Tests 3–7 all PASS

**Goal:** write and test the final-phase code and procedures, then run every remaining test in one Learner Lab session.

### Afternoon: code and documents (no AWS)

| Time (CDT) | What I did | Why | Evidence |
|---|---|---|---|
| afternoon | Wrote `lambda/lambda_function.py` (`cis260-incident-processor`): scope check → full event saved to S3 → readable email | Adds a case record for every alert ([D-12](decisions.md#d-12--lambda-records-evidence-it-does-not-fix-things-automatically)) | [lambda/](../lambda/) |
| afternoon | Wrote 6 synthetic events and 23 offline tests (18 for the function, 5 for the event patterns) | Prove the code and patterns before using lab time | [lambda/events/](../lambda/events/) |
| 5:49 PM | Ran the tests: **23 passed, 0 failed** | — | [test output](../evidence/logs/2026-10-22_lambda-offline-tests.txt) |
| afternoon | Event patterns for the integrity rule and the S3 test; least-privilege IAM policies; procedures for TEST-03 to TEST-07 | Security improvement (D-13) and the LabRole answer | [config/](../config/), [least-privilege.md](least-privilege.md), [test-plan.md](test-plan.md) |

### Evening: Learner Lab session (6:43–7:26 PM CDT), run in CloudShell and Session Manager ([D-17](decisions.md#d-17--aws-cloudshell-and-the-cli-for-the-final-tests))

| Time (CDT) | Time (UTC) | What I did | Result | Evidence |
|---|---|---|---|---|
| 6:43 PM | 23:43:48 | Started the lab. The lab itself started `cis260-target`: CloudTrail `StartInstances` by **`sys4246727`**, not by me | The EC2 alert rule emailed it too (see ISSUE-02) | CloudTrail lookup |
| 6:50 PM | 23:50:21 | Inventory: target running, 0 inbound rules, flow log on `cis260-lab-subnet` ACTIVE/SUCCESS, rules enabled, alarm OK with SNS action, trail logging | Baseline confirmed | `2026-10-22_40` |
| 6:52 PM | 23:52:18 | Created `cis260-test-client-sg` (no inbound; out 443, and 8080 to the target group only) | — | `_41` |
| 6:53 PM | 23:53:05 | Launched `cis260-test-client` (10.26.1.241) | Online in Session Manager by 23:54 | `_43` |
| 6:53 PM | 23:53:52 | Test listener on 10.26.1.235:8080 | — | `_42` |
| 6:54 PM | 23:54:51 | **TEST-03 blocked:** curl timed out | REJECT on the target interface | `_44`, `_48` |
| 6:56 PM | 23:56:51 | **TEST-04:** 7-minute CPU loop started | — | `_47` |
| 6:58 PM | 23:58:15 | Alarm **ALARM** (16.39 % > 10), SNS action executed | — | `_53`, `_54`, `_59` |
| 7:01 PM | 00:01:24 | **TEST-03:** 8080 allowed from the client group only | HTTP 200 at 00:01:44; ACCEPT on the target interface | `_49`, `_50`, `_57` |
| 7:02 PM | 00:02:18 | Removed the rule; retest at 00:02:44 timed out | 0 inbound rules; REJECT again | `_51`, `_52`, `_57` |
| 7:03 PM | 00:03:51 | CPU loop ended by itself | — | `_55` |
| 7:04 PM | ~00:04:20 | Stopped the listener (one request served); port 8080 closed | — | `_56` |
| 7:05 PM | 00:05:15 | Alarm back to **OK** | **TEST-04 PASS** | `_59` |
| 7:06 PM | 00:06:11 | Terminated the client; deleted its security group | **TEST-03 PASS** | `_58` |
| 7:08 PM | 00:08:31 | Health check on the target | Session OK, load 0.02 | `_60` |
| 7:09 PM | 00:09:18 | Created `cis260-incident-records-jbanks` (private, versioned, SSE-S3) | — | `_61` |
| 7:10 PM | 00:10:47 | Deployed `cis260-incident-processor` (Python 3.12, LabRole, 128 MB, 10 s), code SHA-256 checked against the repo | LabRole was accepted | — |
| 7:12 PM | 00:12:07 | Synthetic tests | recorded / ignored as designed | `_62` |
| 7:12 PM | 00:12:45 | Rules `cis260-lambda-sg`, `cis260-lambda-ec2` with invoke permissions | — | `_63` |
| 7:13 PM | 00:13:27–48 | **TEST-06:** self-sourced 8080 rule added and removed | Records match CloudTrail IDs `f503e285`, `8587d2f4` | `_64` |
| 7:16 PM | 00:16:40–00:17:30 | **TEST-06:** target stopped and started | Records match `724e7fef`, `d1b7fc1f`; Session Manager Online 00:18:16 | `_70` |
| 7:19 PM | 00:19:09–11 | **TEST-07 before:** `cis260-sg-changes` disabled and re-enabled | No record, no alert | `_65`, `_70` |
| 7:19 PM | 00:19:38 | Created `cis260-monitoring-integrity` | — | `_66` |
| 7:20 PM | 00:20:05–07 | **TEST-07 after:** same disable/enable | Records `83a3c184`, `62606ba9` + emails: **PASS** | `_67`, `_70` |
| 7:21 PM | 00:21:15 | Empty private test bucket + rule `cis260-s3-control` | — | `_68` |
| 7:22 PM | 00:22:18 | **TEST-05:** versioning enabled | Record `8ba7a55c` at 00:22:29: **PASS** | `_69` |
| 7:23 PM | 00:23:41 | Evidence roll-up: 8 records ↔ CloudTrail, Lambda 9 runs / 0 errors, SNS 16 delivered / 0 failed | **TEST-06 PASS** | `_70` |
| 7:25 PM | 00:25:10 | Final state: 0 inbound, 6 rules enabled, alarm OK, no temporary resources, 4 private buckets | — | `_71` |
| 7:25 PM | 00:25:57 | Stopped `cis260-target` (end-of-session cleanup) | Stopped | — |

Screenshot names above are short for `evidence/screenshots/2026-10-22_<nn>_….jpg`.

**Problems:** none blocked the work.
- At first the Flow Log ACCEPT for the blocked attempt looked wrong. It was the client's own interface; analysis is in [IR-03](../incidents/IR-03-blocked-vs-allowed-traffic.md).
- CloudTrail Event history showed new events a few minutes late, while EventBridge and the Lambda reacted in 4–20 seconds.

**Budget:** about 42 minutes of t3.micro for the target and 13 for the client, ≈ $0.02. After the lab ended, the Learner Lab showed **Used $2.4 of $50** (11:30 PM CDT; [cost log](cost-log.md), `2026-10-22_72`). That is far under the $30 ceiling.
**After the session (11:30 PM):** pushed the repo to GitHub, read the credit, and saved three alert emails as evidence (`2026-10-22_73` to `_75`).
**Next task:** record the demo; final deck.

---

## 2026-10-14 (Wed) — Considered automatic revocation (not used)

Drafted an idea for a function that would remove any new inbound rule by itself. Not deployed. Rejected on 2026-10-22 in favor of an evidence-recording function: see [D-12](decisions.md#d-12--lambda-records-evidence-it-does-not-fix-things-automatically).

---

## 2026-10-09 (Fri) — Midterm presentation (no AWS work)

Presented the midterm progress. Feedback to act on for the final:
- Stay inside the time limit (the appendix ran long).
- Be ready to explain IAM roles, especially LabRole and what I would change about it. That led to [least-privilege.md](least-privilege.md).

---

## 2026-10-02 (Fri) — Build day: network, server access, logging, alerting, Tests 1 and 2

**Goal:** finish the foundation, logging, and alerting promised for the midterm, then run the first two controlled tests.
**Learner Lab session started:** 10:28 AM CDT (15:28 UTC), taken from the `sessionContext.creationDate` field in my own CloudTrail records.

| Time (CDT) | Time (UTC) | What I did | Why | Evidence |
|---|---|---|---|---|
| 11:23 AM | 16:23 | Created internet gateway `cis260-Lab-igw` and attached it to `cis260-security-VPC` | Gives the VPC a path to AWS public service endpoints | `2026-10-02_01_gateway-attached.png` |
| 11:29 AM | 16:29 | Created route table `cis260-lab-rt` with route 0.0.0.0/0 → internet gateway | Without a default route, traffic for addresses outside 10.26.0.0/16 has nowhere to go | `2026-10-02_02_route-table-routes.png` |
| 11:32 AM | 16:32 | Explicitly associated `cis260-lab-subnet` (10.26.1.0/24) with `cis260-lab-rt` | A custom route table only applies to subnets associated with it | `2026-10-02_03_subnet-association.png` |
| 11:44 AM | 16:44 | Created security group `cis260-target-sg` with **no inbound rules** | Nothing on the internet can start a connection to the server; no SSH | `2026-10-02_04_security-group-inbound.png` |
| 11:45 AM | 16:45 | Replaced the default "all traffic" outbound rule with **HTTPS (TCP 443) only** | Least privilege: Session Manager only needs outbound HTTPS | `2026-10-02_05_security-group-outbound.png` |
| 12:11 PM | 17:11 | Launched `cis260-target` (t3.micro, Amazon Linux 2023, role LabRole, IMDSv2 required); all 3 status checks passed | Small, low-cost target with the lab-provided role that allows Systems Manager | `2026-10-02_06_ec2-running.png` |
| 12:16 PM | 17:15 | Connected with Session Manager; ran `whoami` (→ `ssm-user`), `cat /etc/os-release`, `date -u` | Proves access works with zero inbound rules and no SSH keys | `2026-10-02_07_session-manager-connected.png` |
| 12:31 PM | 17:31 | CloudTrail console showed **AccessDeniedException** | See [ISSUE-01](issues.md#issue-01--cloudtrail-console-accessdeniedexception) | `2026-10-02_issue-01_cloudtrail-access-denied.png` |
| 12:39 PM | 17:39 | Trail `cis260-management-trail` created: management events, multi-region, delivering to the S3 bucket, status **Logging** | Event history only keeps 90 days and can't be exported as evidence; a trail keeps a permanent copy in S3 | `2026-10-02_08_cloudtrail-logging.png` |
| 12:42 PM | 17:42 | First CloudTrail log file delivered to S3 | Delivery verified, not just "logging enabled" | `2026-10-02_09_cloudtrail-log-delivery.png` |
| 12:45 PM | 17:45 | Downloaded and read the log file: 7 records, including `GetBucketVersioning` by my lab role and 4 `AccessDenied` console calls | Confirms I can answer who, what, when, and which resource from the evidence | [redacted sample](../evidence/logs/2026-10-02_cloudtrail-sample-redacted.json) |
| 12:59 PM | 17:59 | Verified **Block all public access: On** and the bucket policy (only CloudTrail may write, only for my trail) | Evidence storage must never be public | `2026-10-02_10_s3-block-public-access.png` |
| 1:01 PM | 18:01 | Verified default encryption **SSE-S3** (SSE-C blocked) | Logs encrypted at rest | `2026-10-02_11_s3-default-encryption.png` |
| 1:03 PM | 18:03 | Verified **versioning: Enabled** | Evidence can't be silently overwritten or deleted | `2026-10-02_12_s3-versioning.png` |
| 1:34 PM | 18:34 | Created SNS topic `cis260-security-alerts`; email subscription **Confirmed** | Alert delivery channel | `2026-10-02_13_sns-subscription-confirmed.png` |
| 1:36 PM | 18:36 | Published manual test message **SNS-01**; email received | Proves the subscription works (not yet a real AWS-triggered alert) | `2026-10-02_14_sns-test-email.png` |
| ~2:28 PM | ~19:28 | Learner Lab session reached its 4-hour limit; at 3:40 PM the lab showed a red status dot and timer 0:00 | See [ISSUE-02](issues.md#issue-02--learner-lab-session-expired-during-the-build) | Learner Lab page |
| before 4:24 PM | — | Started a new Learner Lab session (exact time not recorded) | The previous session had expired | — |
| 4:24 PM | 21:24 | Created EventBridge rule `cis260-ec2-api-changes` (CloudTrail `StopInstances`/`StartInstances` for `cis260-target`), Enabled | A real stop or start request should now produce an email | `2026-10-02_15_eventbridge-ec2-rule.png` |
| 4:26 PM | 21:26 | Verified the rule target: SNS topic `cis260-security-alerts`, input = matched event, role LabRole | EventBridge needs permission to publish; LabRole provides it | `2026-10-02_16_eventbridge-sns-target.png` |
| 4:47 PM | 21:47 | Created VPC Flow Log `cis260-subnet-flowlog`: all traffic, 1-minute aggregation, to S3 bucket `cis260-flowlogs-jbanks-20261002`; state Active | Network-traffic evidence for Test 3 (rejected vs. allowed traffic) | `2026-10-02_17_vpc-flow-log.png` |
| 4:52 PM | 21:52:34 | **TEST-02:** stop requested for `cis260-target` (CloudTrail `StopInstances`); alert email the same minute | Controlled outage | `2026-10-02_30_alert-email-stopinstances.png` |
| 4:54 PM | 21:54 | State Stopped, public IPv4 released | — | `2026-10-02_18_test2-instance-stopped.png` |
| 4:54 PM | 21:54:30 | **TEST-02 correction:** start requested (CloudTrail `StartInstances`); alert email the same minute | Recovery | `2026-10-02_31_alert-email-startinstances.png`, `2026-10-02_26_cloudtrail-startinstances.png` |
| 4:56 PM | 21:56 | State Running, status checks initializing, new public IPv4 assigned | — | `2026-10-02_19_test2-instance-running.png` |
| 4:58 PM | 21:58 | **TEST-02 retest:** Session Manager reconnected; `date -u` = 21:58:10 UTC, `whoami` → `ssm-user`; private address unchanged, public address changed | Access recovered with no inbound rules | `2026-10-02_20_test2-session-manager-reconnected.png` |
| 5:11 PM | 22:11 | Created CloudWatch alarm `cis260-cpu-high`: CPUUtilization > 10 for 1 datapoint within 5 minutes; actions enabled; Insufficient data at 22:11:08 UTC, then **OK** at 22:12:01 UTC | First metric alarm, for Test 4 (controlled CPU load) | `2026-10-02_21_cloudwatch-cpu-alarm.png` |
| 5:18 PM | 22:18 | **TEST-01 baseline:** `cis260-target-sg` has no inbound rules | Starting point for the security-group test | `2026-10-02_22_test1-sg-baseline.png` |
| 5:26 PM | 22:26 | Created EventBridge rule `cis260-sg-changes`: CloudTrail `AuthorizeSecurityGroupIngress`/`RevokeSecurityGroupIngress` for `cis260-target-sg`, Enabled (`PutRule` at 22:25:41 UTC) | Inbound-rule changes → email | `2026-10-02_23_eventbridge-sg-rule.png` |
| 5:31 PM | 22:31:23 | **TEST-01 change:** added inbound rule Custom TCP 8080, source = `cis260-target-sg` itself (`sgr-0b9dcb7481490a2ec`); alert email the same minute | Controlled change; nothing outside the group can use it | `2026-10-02_24_test1-rule-added.png`, `2026-10-02_32_alert-email-sg-authorize.png` |
| 5:36 PM | (21:57:56) | Found the `StartSession` record (ssm.amazonaws.com) for the TEST-02 reconnect: my identity | Proves Session Manager access is audited, not just allowed | `2026-10-02_25_cloudtrail-startsession.png` |
| 5:37 PM | (21:54:30) | Found `StartInstances` in CloudTrail Event history: my identity, resource `cis260-target` | Who restarted the server and exactly when | `2026-10-02_26_cloudtrail-startinstances.png` |
| 5:41 PM | 22:41:07 | **TEST-01 correction:** removed the 8080 rule (CloudTrail `RevokeSecurityGroupIngress`); second alert email the same minute; **retest:** 0 inbound rules | Restore the baseline | `2026-10-02_27_test1-sg-restored.png`, `2026-10-02_29_cloudtrail-revoke-sg.png`, `2026-10-02_33_alert-email-sg-revoke.png` |
| 5:44 PM | (22:25:41) | Found the `PutRule` record (events.amazonaws.com) for the creation of `cis260-sg-changes` | Changes to the monitoring itself are audited | `2026-10-02_28_cloudtrail-putrule.png` |
| 6:11 PM | — | Collected all four automatic alert emails, each within a minute of its action | **Both alert rules verified end to end; TEST-01 and TEST-02 PASS** | `2026-10-02_30` to `_33_alert-email-*.png` |
| 6:50 PM | — | **ISSUE-03 fix:** changed `cis260-ec2-api-changes` target input from Matched events to an input transformer (readable one-line alert) | Raw JSON alerts were hard to read | `2026-10-02_34_eventbridge-ec2-transformer.png` |
| 7:11 PM | — | **ISSUE-03 fix:** same change on `cis260-sg-changes` | Both alert rules now send readable alerts | `2026-10-02_35_eventbridge-sg-transformer.png` |
| 7:22 PM | 00:22 (Oct 3) | **ISSUE-03 retest:** added the 8080 test rule again; the alert now arrives as one readable sentence | Fix verified for `cis260-sg-changes` | `2026-10-02_36_readable-alert-sg-authorize.png` |
| 7:23 PM | 00:23 (Oct 3) | Removed the 8080 test rule; readable Revoke alert received; **security group back to 0 inbound rules** | Fix verified both ways; cleanup | `2026-10-02_37_readable-alert-sg-revoke.png` |
| 7:29 PM | 00:29 (Oct 3) | Stopped `cis260-target`; readable StopInstances alert received | ISSUE-03 verified for the EC2 rule | `2026-10-02_38_readable-alert-ec2-stop.png` |
| 7:30 PM | 00:30 (Oct 3) | Started `cis260-target` again; readable StartInstances alert received | Both EC2 actions confirmed in the readable format | `2026-10-02_39_readable-alert-ec2-start.png` |

**Problems:** [ISSUE-01](issues.md#issue-01--cloudtrail-console-accessdeniedexception) CloudTrail console AccessDeniedException; [ISSUE-02](issues.md#issue-02--learner-lab-session-expired-during-the-build) session expired; [ISSUE-03](issues.md#issue-03--alert-emails-were-raw-json-and-hard-to-read---fixed-and-verified) raw JSON alerts (fixed).

**Budget:** Learner Lab showed **Used $1.4 of $50** at 3:40 PM CDT.

**Shutdown:** not recorded. The last recorded action was the 7:30 PM start for the ISSUE-03 retest. Learner Lab stops running instances when a session ends; the next session must confirm the instance's state.

---

## Before 2026-10-02 — Retrospective: VPC and subnet

Created `cis260-security-VPC` (10.26.0.0/16) and `cis260-lab-subnet` (10.26.1.0/24, us-east-1a) in us-east-1, in late September 2026 (exact date not recorded). The Oct 2 screenshots 01–03 show both in place.
