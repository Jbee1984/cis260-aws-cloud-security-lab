# Issue log

Every real problem met while building the lab. Fields follow the issue format promised in the project proposal.

---

## ISSUE-01 — CloudTrail console AccessDeniedException

| Field | Entry |
|---|---|
| Date / time | 2026-10-02, ~12:31 PM CDT (~17:31 UTC) |
| Component | AWS CloudTrail console |
| Task being attempted | Create the management trail that delivers logs to the S3 evidence bucket |
| Expected behavior | The CloudTrail console opens normally and a trail can be created |
| Actual behavior | A yellow banner at the top of the CloudTrail landing page |
| Exact error message | `AccessDeniedException` — "You don't have permissions to access this resource." |
| Diagnostic steps | Not written down at the time. The evidence shows I kept going to **Create trail**, the trail was created 8 minutes later, and its first log file reached S3 3 minutes after that. |
| Sources consulted | AWS Academy Learner Lab Readme (service restrictions); later, the `errorCode` fields in my own first CloudTrail log file |
| Root cause | **Likely:** the Learner Lab role (`voclabs`) denies some API calls that AWS console pages make in the background. Supporting evidence: my first CloudTrail log file (17:40–17:42 UTC) contains **4 records with `errorCode: AccessDenied`** for other console background calls (`notifications.amazonaws.com` and `uxc.amazonaws.com`), while the calls needed for the project succeeded. |
| Change made | None to permissions. I continued creating the trail and did not try to change the lab's protected IAM settings. |
| Verification test | Trail `cis260-management-trail` shows status **Logging** (12:39 PM CDT); first log file delivered to S3 (12:42 PM CDT); a record from that file read successfully |
| Time spent | About 10 minutes (12:31 → ~12:39 PM CDT) |
| Lesson learned | An AccessDenied banner doesn't always mean the task is blocked. Check whether the resource you actually need was created, and use CloudTrail's `errorCode` field to see exactly which call was denied. |
| Evidence | `evidence/screenshots/2026-10-02_issue-01_cloudtrail-access-denied.png`, `evidence/logs/2026-10-02_cloudtrail-sample-redacted.json` |

### Related finding — CloudTrail records denied calls too

Of the 7 records in the first log file, 4 had `errorCode: AccessDenied`. CloudTrail records **failed** attempts as well as successful ones. In a real investigation, a burst of `AccessDenied` errors from one identity can be a sign of someone probing for permissions they don't have.

---

## ISSUE-02 — Learner Lab session expired during the build

| Field | Entry |
|---|---|
| Date / time | 2026-10-02, ~2:28 PM CDT (~19:28 UTC) |
| Component | AWS Academy Learner Lab session |
| Task being attempted | EventBridge rules and Tests 1–2 |
| Expected behavior | Session stays active until the work is finished |
| Actual behavior | At 3:40 PM the Learner Lab page showed a red status dot and timer **0:00** — the session had ended |
| Root cause | Learner Lab sessions last 4 hours. CloudTrail shows this session's role credentials were created at 15:28:51 UTC (10:28 AM CDT), so it ran out at about 2:28 PM. When a session ends, running EC2 instances are stopped. |
| Change made | Clicked **Start Lab** to begin a new session. The exact time wasn't recorded; work resumed by 4:24 PM CDT. |
| Verification test | The new session worked: the EC2 alert rule was created at 4:24 PM and the TEST-02 `StopInstances` call succeeded at 4:52 PM. The instance's state at the start of the new session wasn't recorded. |
| Lesson learned | Check the session timer before starting a multi-step test, and restart the session first if less than an hour is left. The automatic stop is itself a stop request — with rule `cis260-ec2-api-changes` in place, an unplanned stop like this should now produce an alert, and CloudTrail shows which identity stopped the instance. |
| Follow-up (2026-10-22) | **Confirmed for starts.** When I clicked Start Lab, CloudTrail recorded `StartInstances` for `cis260-target` at 23:43:48 UTC by **`sys4246727`**, the lab's own automation identity, not my `user4744416=Jeremiah_Banks`. The `cis260-ec2-api-changes` rule emailed it. So an analyst can tell lab automation from a person by the `userIdentity` in the alert. |

---

## ISSUE-03 — Alert emails were raw JSON and hard to read  ✅ Fixed and verified

| Field | Entry |
|---|---|
| Date / time | 2026-10-02, ~6:15 PM CDT, while reviewing the four alert emails from TEST-01 and TEST-02 |
| Component | EventBridge rule targets (SNS) |
| Expected behavior | An alert anyone can read at a glance: what happened, to which resource, who did it, when |
| Actual behavior | Each email was one long block of raw JSON (the full CloudTrail event), plus the SNS footer |
| Root cause | Both rule targets used **Configure target input → Matched events**, which forwards the entire event unchanged; SNS emails whatever it receives |
| Change made | Switched each target to an **Input transformer**: an input path pulls out `eventName`, the resource ID, `userIdentity.arn`, `eventTime`, and `sourceIPAddress`, and a template turns them into one plain-English sentence. `cis260-ec2-api-changes` updated 6:50 PM CDT; `cis260-sg-changes` updated ~7:11 PM CDT |
| Console note | AWS redesigned the EventBridge console: rules are now under **Event buses → default → Rules** (no "Rules" item in the left menu), and the setting is under the target's **Additional settings → Configure target input** |
| Verification test | **Verified for `cis260-sg-changes`:** a new AuthorizeSecurityGroupIngress at 2026-10-03 00:22:11 UTC (7:22 PM CDT Oct 2) produced a one-sentence alert — "CIS260 ALERT: AuthorizeSecurityGroupIngress changed an inbound rule (port 8080) on security group sg-06e94ae52286f9f2e by … at … (UTC) from IP …"; the removal at 00:23:12 UTC (7:23 PM CDT) produced the matching readable RevokeSecurityGroupIngress alert. **Verified for `cis260-ec2-api-changes`:** the end-of-day stop at 00:29:44 UTC (7:29 PM CDT) produced "CIS260 ALERT: StopInstances was requested for EC2 instance i-085a300c3d2a60c75 by … at … (UTC) from IP …". Both rules now send readable alerts. |
| Evidence | Before: `2026-10-02_16_eventbridge-sns-target.png` (Input: Matched event), alert emails `_30`–`_33`. After: `2026-10-02_34_eventbridge-ec2-transformer.png`, `2026-10-02_35_eventbridge-sg-transformer.png`, readable alerts `2026-10-02_36_readable-alert-sg-authorize.png`, `2026-10-02_37_readable-alert-sg-revoke.png`, `2026-10-02_38_readable-alert-ec2-stop.png`, `2026-10-02_39_readable-alert-ec2-start.png` |
| Lesson learned | Detection is only useful if the person receiving the alert can act on it quickly. The full JSON is still kept in CloudTrail for the investigation. |
