# Test plan

Every test record contains: test ID, objective, prerequisites, exact actions, expected result, actual result, date, evidence, pass/fail, problems, correction, and retest. All times are recorded in **UTC** so they can be lined up with CloudTrail.

| Test | Scenario | Schedule | Status |
|---|---|---|---|
| TEST-01 | Temporary security-group rule | Midterm (Oct 2) | ⏳ In progress → [IR-01](../incidents/IR-01-security-group-change.md) |
| TEST-02 | EC2 stop and restart | Midterm (Oct 2) | ⏳ In progress → [IR-02](../incidents/IR-02-ec2-stop-start.md) |
| TEST-03 | Rejected vs. allowed network traffic (VPC Flow Logs) | Oct 17–30 | 📅 Planned |
| TEST-04 | CPU metric threshold (CloudWatch alarm) | Oct 17–30 | 📅 Planned |
| TEST-05 | S3 security-control event (stretch) | If time permits | 📅 Planned |

---

## TEST-01 — Temporary security-group rule

**Objective:** prove that an inbound-rule change on the target's security group is recorded, alerted, investigated, corrected, and verified.
**Prerequisites:** rule `cis260-sg-changes` enabled; SNS subscription confirmed; CloudTrail logging.

| Step | Action | Expected result |
|---|---|---|
| 1 | Record the baseline | `cis260-target-sg` has 0 inbound rules |
| 2 | Edit inbound rules → add **Custom TCP, port 8080, source = `cis260-target-sg` itself**, description `TEST-01 temporary` | Rule saved. Because the source is the security group itself, nothing outside the group can use it — the test exposes nothing to the internet |
| 3 | Wait for the alert | Email from SNS containing `AuthorizeSecurityGroupIngress` |
| 4 | Find the CloudTrail record (Event history → Event name = `AuthorizeSecurityGroupIngress`) | Record shows my identity, the group ID, port 8080, and the time |
| 5 | Remove the rule (correction) | Second email containing `RevokeSecurityGroupIngress` |
| 6 | Retest | 0 inbound rules again; Session Manager still connects |

**Pass criteria:** both emails arrive, both CloudTrail records are found, and the group is back to its baseline.

## TEST-02 — EC2 stop and restart

**Objective:** prove that an unplanned-looking outage is detected, explained, and recovered from.
**Prerequisites:** rule `cis260-ec2-api-changes` enabled; instance running; Session Manager working.

| Step | Action | Expected result |
|---|---|---|
| 1 | Baseline | Instance running, status checks passed, Session Manager connects |
| 2 | Instance state → **Stop instance** | Instance reaches `stopped` |
| 3 | Wait for the alert | Email containing `"eventName": "StopInstances"`, my instance ID, and my identity |
| 4 | Find `StopInstances` in CloudTrail Event history | Same who / when as the email |
| 5 | Instance state → **Start instance** (correction) | Second email with `"eventName": "StartInstances"`; `StartInstances` in CloudTrail |
| 6 | Retest | Status checks pass; Session Manager reconnects; note that the public IP changed |

**Pass criteria:** both state emails arrive, both API records are found, and the instance is reachable through Session Manager again.

## TEST-03 — Rejected vs. allowed traffic (planned)
A short-lived second instance in the same subnet attempts a connection to a closed port on the target → expect a `REJECT` record in VPC Flow Logs. Then a narrowly scoped temporary rule (source = test instance's security group) allows one connection → expect `ACCEPT`. Remove the rule and terminate the test instance.

## TEST-04 — CPU metric threshold (planned)
A brief, controlled CPU workload on the target (stopped manually after a few minutes) → CloudWatch `CPUUtilization` rises → alarm goes to `ALARM` → SNS email → workload stopped → alarm returns to `OK`.

## TEST-05 — S3 security-control event (stretch)
An approved, non-public change (or a denied attempt) against an empty test bucket → CloudTrail record → alert if configured → proof the final control state is secure.
