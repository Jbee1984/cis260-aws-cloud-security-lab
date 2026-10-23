# Test plan

Every test record contains: test ID, objective, prerequisites, exact actions, expected result, actual result, date, evidence, pass/fail, problems, correction, and retest. All times are recorded in **UTC** so they line up with CloudTrail. A console setting that saved without an error is **not** a passed test: a test passes only on real evidence.

| Test | Scenario | Status |
|---|---|---|
| TEST-01 | Temporary security-group rule | ✅ **PASS** 2026-10-02 → [IR-01](../incidents/IR-01-security-group-change.md) |
| TEST-02 | EC2 stop and restart | ✅ **PASS** 2026-10-02 → [IR-02](../incidents/IR-02-ec2-stop-start.md) |
| TEST-03 | Rejected vs. allowed network traffic (VPC Flow Logs) | ✅ **PASS** 2026-10-22 → [IR-03](../incidents/IR-03-blocked-vs-allowed-traffic.md) |
| TEST-04 | CPU alarm and recovery (CloudWatch) | ✅ **PASS** 2026-10-22 → [IR-04](../incidents/IR-04-cpu-alarm.md) |
| TEST-05 | S3 versioning change on an empty test bucket (supplemental) | ✅ **PASS** 2026-10-22 |
| TEST-06 | Lambda incident processor, synthetic and real end to end | ✅ **PASS** 2026-10-22 (offline 23/23; synthetic 2/2; real 4/4) |
| TEST-07 | Security improvement: alert when an alert rule is disabled (before/after) | ✅ **PASS** 2026-10-22 → [IR-05](../incidents/IR-05-alert-rule-disabled.md), [control-improvement.md](control-improvement.md) |

All of TEST-03 to TEST-07 ran in one Learner Lab session on 2026-10-22 (6:44–7:26 PM CDT). Most actions were run as AWS CLI commands in **AWS CloudShell** (decision [D-17](decisions.md#d-17--aws-cloudshell-and-the-cli-for-the-final-tests)) and Session Manager, so every step has an exact UTC timestamp. The steps below show the console way. The commands actually used are in [lambda/README.md](../lambda/README.md#what-was-actually-run-2026-10-22).

---

## TEST-01 — Temporary security-group rule ✅

**Objective:** prove that an inbound-rule change on the target's security group is recorded, alerted, investigated, corrected, and verified.
**Prerequisites:** rule `cis260-sg-changes` enabled; SNS subscription confirmed; CloudTrail logging.

| Step | Action | Expected result |
|---|---|---|
| 1 | Record the baseline | `cis260-target-sg` has 0 inbound rules |
| 2 | Edit inbound rules → add **Custom TCP, port 8080, source = `cis260-target-sg` itself** | Rule saved. Because the source is the group itself, nothing outside the group can use it: the test exposes nothing to the internet |
| 3 | Wait for the alert | Email containing `AuthorizeSecurityGroupIngress` |
| 4 | Find the CloudTrail record (Event history → Event name = `AuthorizeSecurityGroupIngress`) | Record shows my identity, the group ID, port 8080, and the time |
| 5 | Remove the rule (correction) | Second email containing `RevokeSecurityGroupIngress` |
| 6 | Retest | 0 inbound rules again |

**Actual:** rule added 22:31:23 UTC; alert email the same minute; removed 22:41:07 UTC; second alert the same minute; 0 inbound rules after. **PASS.** Repeated 00:22–00:23 UTC Oct 3 to verify readable alerts (ISSUE-03); removed again, 0 inbound rules.

## TEST-02 — EC2 stop and restart ✅

**Objective:** prove that an outage is detected, explained, and recovered from.
**Prerequisites:** rule `cis260-ec2-api-changes` enabled; instance running; Session Manager working.

| Step | Action | Expected result |
|---|---|---|
| 1 | Baseline | Instance running, Session Manager connects |
| 2 | Instance state → **Stop instance** | Instance reaches `stopped` |
| 3 | Wait for the alert | Email with `StopInstances`, my instance ID, and my identity |
| 4 | Find `StopInstances` in CloudTrail | Same who and when as the email |
| 5 | Instance state → **Start instance** (correction) | Second email with `StartInstances` |
| 6 | Retest | Status checks pass; Session Manager reconnects; the public IP changed |

**Actual:** stop 21:52:34 UTC, start 21:54:30 UTC, both alerts within a minute, Session Manager reconnected 21:58:10 UTC. **PASS.**

---

## TEST-03 — Rejected vs. allowed traffic (VPC Flow Logs)

**Objective:** show the security group blocking a connection, then allowing exactly one source, with matching `REJECT` and `ACCEPT` Flow Log records.
**Prerequisites:** flow log `cis260-subnet-flowlog` Active and delivering to `cis260-flowlogs-jbanks-20261002`; target running.

| Step | Action | Expected result | Evidence |
|---|---|---|---|
| 1 | EC2 → Security groups → create `cis260-test-client-sg` in the project VPC: **no inbound**; outbound HTTPS 443 to 0.0.0.0/0 (for Session Manager) and Custom TCP 8080 to **destination `cis260-target-sg`** | Group created | `T3_client-sg.png` |
| 2 | Launch `cis260-test-client`: Amazon Linux 2023, t3.micro, project subnet, `cis260-test-client-sg` only, LabInstanceProfile, IMDSv2 required, no key pair | Running, status checks pass | `T3_client-running.png` |
| 3 | Write down both **private** IPs and the target's network-interface ID (EC2 → target → Networking) | — | (private notes) |
| 4 | Session Manager on the **target**: `timeout 900 python3 -m http.server 8080 --bind TARGET_PRIVATE_IP` (a test web server for at most 15 minutes) | "Serving HTTP on … port 8080" | `T3_listener.png` |
| 5 | Session Manager on the **client**: `date -u` then `curl --connect-timeout 5 -v http://TARGET_PRIVATE_IP:8080/` | **Timeout** (target has no inbound rule) | `T3_blocked_client.png` |
| 6 | Wait ~10 minutes; S3 → flow-log bucket → today's folder → download the newest `.log.gz`; find client IP → target IP, port 8080 | A record ending in **`REJECT OK`** | `T3_reject-record.png` |
| 7 | Target SG → add inbound **Custom TCP 8080, source `cis260-test-client-sg`** (not 0.0.0.0/0); run the same curl | HTTP response (directory listing). The `cis260-sg-changes` alert email arrives | `T3_narrow-rule.png`, `T3_allowed_client.png` |
| 8 | Find the matching **`ACCEPT OK`** record | Same IPs and port, action ACCEPT | `T3_accept-record.png` |
| 9 | **Correction:** remove the 8080 rule; run curl again | Timeout again; Revoke alert email; target back to 0 inbound rules | `T3_retest-blocked.png`, `T3_final-empty-inbound.png` |
| 10 | Ctrl+C the listener; **terminate** `cis260-test-client` (check name and ID first); delete `cis260-test-client-sg` after it shows no attachments | Client terminated, group deleted | `T3_client-terminated.png` |

**Reading a record** (default format): `version account-id interface-id srcaddr dstaddr srcport dstport protocol packets bytes start end action log-status`. Protocol `6` = TCP. `start`/`end` are Unix times (convert to UTC). ACCEPT/REJECT is the network decision, not an incident verdict.

**Pass:** a REJECT record before the rule, an ACCEPT record with it, REJECT behavior again after removing it, and the client cleaned up.
**If curl says "Connection refused" instead of timing out:** the listener isn't running. Check step 4 first.

| Field | Result |
|---|---|
| Date run | 2026-10-22 (6:52–7:06 PM CDT) |
| Blocked attempt | curl timed out at 23:54:51 UTC (exit 28); **REJECT** on target interface `eni-0e9467ff27cb756eb` (23:54:26 and 23:54:53 windows, 5 packets) |
| Allowed attempt | rule `sgr-0b5b017731738b433` (8080 from `cis260-test-client-sg`) added 00:01:24; **HTTP 200** at 00:01:44; **ACCEPT** on the target interface (00:01:54 window) |
| Retest after removal | rule removed 00:02:18; curl timed out at 00:02:44; **REJECT** (00:02:29 window) |
| Rule add / remove alert emails | sent by `cis260-sg-changes` for both changes |
| Cleanup confirmed | listener stopped (one request served), client terminated 00:06:11, client group deleted, 0 inbound rules |
| Result | ✅ **PASS**. Note: the client's own interface shows ACCEPT for the blocked attempts (its outbound rule let them leave); judge reachability on the **target's** interface. See [IR-03](../incidents/IR-03-blocked-vs-allowed-traffic.md) |

## TEST-04 — CPU alarm and recovery

**Objective:** a real CPU load trips the alarm, the email arrives, and the alarm returns to OK after the load stops.
**Prerequisites:** alarm `cis260-cpu-high` (CPUUtilization > 10 % for 1 datapoint in 5 minutes) in state OK; its action notifies `cis260-security-alerts` (check this first: it wasn't visible in the Oct 2 screenshot).

| Step | Action | Expected result | Evidence |
|---|---|---|---|
| 1 | CloudWatch → Alarms → `cis260-cpu-high` → confirm state **OK** and the SNS action. Optional: add a second notification for **OK** to the same topic, so recovery also emails | OK; action listed | `T4_alarm-before.png` |
| 2 | Session Manager on the target: `date -u`, then `timeout 420 sh -c 'while :; do :; done'` (one busy loop, stops itself after 7 minutes) | Command runs | `T4_load-started.png` |
| 3 | In a second session: `top` (press `q` to quit) | One process near 100 % of a CPU | `T4_top.png` |
| 4 | Wait for the next 5-minute datapoint; the alarm goes to **In alarm** | ALARM state; email from SNS. Record the real delay (5-minute averages are not instant) | `T4_alarm.png`, `T4_alarm-email.png`, `T4_cpu-graph.png` |
| 5 | Load stops by itself; wait for fresh low datapoints | Alarm returns to **OK** (and the OK email, if added) | `T4_recovery-ok.png` |
| 6 | Session Manager still connects; status checks pass | Healthy | `T4_healthy.png` |

**Pass:** the alarm moved OK → ALARM → OK because of the real load, and the ALARM email arrived. Do not use "Set alarm state" as a substitute: that would test only the email path, not the metric.

| Field | Result |
|---|---|
| Date run | 2026-10-22 (6:55–7:08 PM CDT) |
| Load start / stop (UTC) | 23:56:51 / 00:03:51 (stopped itself) |
| ALARM time and email time | ALARM 23:58:15 (datapoint 16.39 % > 10); SNS action executed 23:58:15 |
| OK time | 00:05:15 |
| Peak CPU % | 5-minute average 29.78 %, maximum 49.90 % (one of two vCPUs busy) |
| Result | ✅ **PASS**: OK → ALARM → OK from a real load; session healthy at 00:08:31. See [IR-04](../incidents/IR-04-cpu-alarm.md) |

## TEST-05 — S3 versioning change on an empty test bucket (supplemental)

**Objective:** a security-relevant S3 setting change is recorded, alerted, and verified, without ever making anything public.
**Prerequisites:** Lambda deployed (TEST-06 part A passed); rule `cis260-s3-control` created from [`config/eventbridge-s3-control.json`](../config/eventbridge-s3-control.json).

| Step | Action | Expected result | Evidence |
|---|---|---|---|
| 1 | Create bucket `cis260-s3-control-test-jbanks`: Block all public access **on**, SSE-S3, versioning **off**, upload nothing | Empty private bucket | `S1_bucket-before.png` |
| 2 | Bucket → Properties → Bucket Versioning → **Enable** → Save; record UTC time | Versioning Enabled | `S2_versioning-enabled.png` |
| 3 | CloudTrail Event history → `PutBucketVersioning` | My identity, the bucket name, no errorCode | `S2_cloudtrail.png` |
| 4 | Incident email + record under `incidents/` | Same event ID in all three | `S3_control-alert.png` |
| 5 | Bucket still empty, private, versioning Enabled | Final state | `S4_final.png` |

**This does not test public-data exposure.** It never turns off Block Public Access. Delete the empty bucket after grading.

**Actual (2026-10-22):** bucket created 00:21:15 UTC (all 4 Block Public Access settings on, SSE-S3, versioning never enabled, empty); rule `cis260-s3-control` created; versioning enabled 00:22:18 → CloudTrail `PutBucketVersioning` `8ba7a55c-b8c1-408a-98c1-9e35a679f8c8` at 00:22:19 → record saved 00:22:29 with the same ID; bucket still empty and private. **✅ PASS.**

## TEST-06 — Lambda incident processor

**Part A, synthetic (Lambda console → Test):** follow [lambda/README.md](../lambda/README.md) step 6.
- `synthetic-sg-authorize.json` → `"status": "recorded"`, a new S3 object, an email.
- `synthetic-sg-other-group.json` → `"reason": "resource"`, no object, no email.

Label these screenshots **synthetic** (`L5_synthetic-recorded.png`, `L6_synthetic-ignored.png`).

**Part B, real end to end:** with rules `cis260-lambda-sg` and `cis260-lambda-ec2` enabled, repeat TEST-01 (add and remove the self-sourced 8080 rule) and TEST-02 (stop and start the target). For each action:

| Check | Where |
|---|---|
| CloudTrail event ID | Event history |
| Record `incidents/<date>/<eventName>-<eventID>.json` with the **same** event ID | S3 → `cis260-incident-records-jbanks` |
| Incident email with the same event ID | Inbox |
| Function ran without errors | Lambda → Monitor (Invocations, Errors = 0) |
| Final state restored | 0 inbound rules; instance running and reachable |

**Pass:** all four real actions produce matching record + email + CloudTrail ID, and nothing outside the lab is recorded.

**Part A (synthetic, 00:12 UTC):** my group → `{"status": "recorded"}` and a 1,408-byte record; other group → `{"status": "ignored", "reason": "resource"}`, no record.

| Action (UTC) | CloudTrail event ID | S3 record saved (UTC) | Result |
|---|---|---|---|
| AuthorizeSecurityGroupIngress 00:13:28 | `f503e285-0cc3-45b1-980c-66498bb45b2b` | 00:13:32 | ✅ same ID |
| RevokeSecurityGroupIngress 00:13:50 | `8587d2f4-b164-4925-a68a-17daabd2e569` | 00:13:52 | ✅ same ID |
| StopInstances 00:16:40 | `724e7fef-7a1a-418b-add5-9575ecc0814c` | 00:16:45 | ✅ same ID |
| StartInstances 00:17:13 | `d1b7fc1f-0396-4a51-88b6-7f360e379140` | 00:17:19 | ✅ same ID |

Lambda: 9 invocations, **0 errors**. SNS (whole session): 16 emails delivered, 0 failed. After the restart, Session Manager was Online at 00:18:16. Final state: 0 inbound rules, target running. **✅ PASS.**

## TEST-07 — Monitoring-integrity improvement (before/after)

Full procedure and result table: [control-improvement.md](control-improvement.md).
