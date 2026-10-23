# AWS Cloud Security Monitoring and Incident Response Lab

**CIS 260: Computer Information Systems Field Project** · Jeremiah Banks · Wilbur Wright College, City Colleges of Chicago · Fall 2026

A small AWS lab I built from scratch to practice the full incident-response loop:
**detect** a change, **investigate** it, **preserve** evidence, **correct** the problem, and **retest** to prove the correction worked.

The lab runs in an AWS Academy Learner Lab account ($50 total credit, restricted IAM permissions). Most of the system is AWS configuration, with every setting explained. The one piece of code is a small Python Lambda function ([lambda/](lambda/)) with 23 offline tests and a line-by-line explanation, deployed and tested end to end.

**Result: all 7 controlled tests passed** (Tests 1–2 on Oct 2, Tests 3–7 on Oct 22), and every alert can be matched to its CloudTrail event ID.

---

## Current status — October 23, 2026

| Component | Status | Evidence |
|---|---|---|
| VPC `cis260-security-VPC` (10.26.0.0/16), subnet `cis260-lab-subnet` (10.26.1.0/24), internet gateway, custom route table | ✅ Done | screenshots 01–03, [configuration](docs/configuration.md) |
| Security group `cis260-target-sg`: no inbound rules, outbound HTTPS only | ✅ Done | screenshots 04–05 |
| EC2 target `cis260-target` (t3.micro, Amazon Linux 2023, IMDSv2 required), Session Manager access (no SSH) | ✅ Verified | screenshots 06–07 |
| CloudTrail trail `cis260-management-trail` → private, encrypted, versioned S3 bucket | ✅ Delivery verified | screenshots 08–12, [log sample](evidence/logs/2026-10-02_cloudtrail-sample-redacted.json) |
| SNS topic `cis260-security-alerts`, confirmed email | ✅ Verified | screenshots 13–14 |
| EventBridge alerts: security-group changes and EC2 stop/start, as readable one-line emails | ✅ **Verified end to end** | screenshots 15–16, 23, 30–39 |
| **TEST-01** security-group change · **TEST-02** EC2 stop and restart | ✅ **Both PASS** (2026-10-02) | [IR-01](incidents/IR-01-security-group-change.md), [IR-02](incidents/IR-02-ec2-stop-start.md) |
| VPC Flow Log `cis260-subnet-flowlog` → S3 (attached to `cis260-lab-subnet`) | ✅ Delivering every 5 minutes; REJECT/ACCEPT records used in TEST-03 | screenshots 17, 2026-10-22_40, _48, _57 |
| CloudWatch alarm `cis260-cpu-high` (CPU > 10 %) → SNS | ✅ Fired for real in TEST-04 (ALARM 23:58:15 → OK 00:05:15 UTC) | screenshots 21, 2026-10-22_45–_60 |
| Lambda `cis260-incident-processor` (incident records + readable alerts) + private bucket `cis260-incident-records-jbanks` | ✅ **Deployed 2026-10-22**: 23/23 offline tests, 2/2 synthetic, every real event recorded with its CloudTrail event ID, 0 errors | [lambda/](lambda/), [test output](evidence/logs/2026-10-22_lambda-offline-tests.txt), 2026-10-22_61–_64, _70 |
| Least-privilege IAM policies (what LabRole should be split into) | ✅ Written (reference; Learner Lab blocks creating roles) | [config/iam/](config/iam/), [least-privilege.md](docs/least-privilege.md) |
| **TEST-03** blocked vs. allowed traffic · **TEST-04** CPU alarm · **TEST-05** S3 control · **TEST-06** Lambda end to end · **TEST-07** alert-rule tampering (the security improvement) | ✅ **All PASS** (2026-10-22) | [test plan](docs/test-plan.md), [IR-03](incidents/IR-03-blocked-vs-allowed-traffic.md), [IR-04](incidents/IR-04-cpu-alarm.md), [IR-05](incidents/IR-05-alert-rule-disabled.md), [control improvement](docs/control-improvement.md) |
| Demo recording | 📅 To record | — |

## How it works

```mermaid
flowchart LR
    A["Change in AWS<br/>security group · EC2 · alert rule · S3 setting"] --> B["CloudTrail<br/>records the API call"]
    B --> C["S3 log bucket<br/>private · encrypted · versioned"]
    B --> D["EventBridge rules<br/>scoped to my resources"]
    D --> F["SNS email<br/>one-line alert"]
    D --> L["Lambda incident processor<br/>scope check"]
    L --> R["S3 incident record<br/>named by CloudTrail event ID"]
    L --> F2["SNS email<br/>incident summary"]
    N["VPC Flow Logs<br/>ACCEPT / REJECT"] --> C2["S3 flow-log bucket"]
    M["CloudWatch alarm<br/>CPU > 10 %"] --> F
    F --> H["Investigate · correct · retest"]
    F2 --> H
    R --> H
    C --> H
    C2 --> H
```

| Source | Answers | Example |
|---|---|---|
| CloudTrail | **Who changed what, when, from where** (API calls) | `AuthorizeSecurityGroupIngress` by my lab session at 22:31:23 UTC |
| VPC Flow Logs | **Which traffic was allowed or blocked** (network metadata, no packet contents) | client → target port 8080 `REJECT` |
| CloudWatch | **How the server is performing** (metrics) | CPUUtilization above 10 % → ALARM |

Diagram as an image: [docs/images/architecture.png](docs/images/architecture.png)

EventBridge receives CloudTrail events directly from AWS; it does not read the log files in S3. S3 is the long-term evidence; the email is the fast notification. The Lambda function never changes anything. A person reviews the evidence and makes the fix ([why](docs/decisions.md#d-12--lambda-records-evidence-it-does-not-fix-things-automatically)).

## Architecture at a glance

| Layer | Resource | Key settings |
|---|---|---|
| Network | `cis260-security-VPC`, `cis260-lab-subnet` | 10.26.0.0/16 and 10.26.1.0/24, us-east-1 |
| | `cis260-Lab-igw`, `cis260-lab-rt` | 0.0.0.0/0 → internet gateway; no NAT gateway (cost) |
| Firewall | `cis260-target-sg` | inbound: none · outbound: HTTPS (TCP 443) only |
| Compute | `cis260-target` | t3.micro, Amazon Linux 2023, role LabRole, IMDSv2 required |
| Access | Session Manager | shell as `ssm-user`, no SSH keys, no inbound port |
| Logging | `cis260-management-trail` | management events, multi-region, delivers to S3 |
| Evidence | `cis260-security-logs-jbanks-20261002` | Block all public access, SSE-S3, versioning, bucket policy limited to my trail |
| Network logging | `cis260-subnet-flowlog` | all traffic, 1-minute aggregation → `cis260-flowlogs-jbanks-20261002` |
| Metrics | `cis260-cpu-high` | CPUUtilization > 10 % for one 5-minute period → SNS |
| Alerting | `cis260-security-alerts` + rules `cis260-sg-changes`, `cis260-ec2-api-changes` | readable one-line emails (input transformer) |
| Incident records | `cis260-incident-processor` → `cis260-incident-records-jbanks` | Python 3.12 Lambda (LabRole), outside the VPC; 4 Lambda-target rules incl. `cis260-monitoring-integrity` |

Every setting and the reason for it: [docs/configuration.md](docs/configuration.md).

## The code and how to test it

| Path | What it is |
|---|---|
| [lambda/lambda_function.py](lambda/lambda_function.py) | The incident processor: scope check → full event saved to S3 → readable email (76 lines) |
| [lambda/test_lambda_function.py](lambda/test_lambda_function.py), [lambda/test_event_patterns.py](lambda/test_event_patterns.py) | 23 offline tests (fake S3/SNS, no AWS account needed) |
| [lambda/events/](lambda/events/) | Synthetic test events |
| [config/](config/README.md) | EventBridge patterns and IAM policies, explained line by line |

```
python -m unittest discover -s lambda -v
```

Expected: `Ran 23 tests ... OK` ([saved output from 2026-10-22](evidence/logs/2026-10-22_lambda-offline-tests.txt)). Deploy steps: [lambda/README.md](lambda/README.md). Every line explained: [docs/lambda-line-by-line.md](docs/lambda-line-by-line.md).

## Repository map

| Path | What it holds |
|---|---|
| [docs/work-log.md](docs/work-log.md) | Dated record of every work session |
| [docs/configuration.md](docs/configuration.md) | Every resource, every setting, and why |
| [docs/decisions.md](docs/decisions.md) | Design decisions and the alternatives I rejected |
| [docs/issues.md](docs/issues.md) | Problems: expected vs. actual, diagnosis, fix, retest |
| [docs/test-plan.md](docs/test-plan.md) | All seven tests: steps, expected results, actual results |
| [docs/control-improvement.md](docs/control-improvement.md) | The before/after security improvement |
| [docs/least-privilege.md](docs/least-privilege.md) | LabRole, why it's too broad, and the roles I'd use instead |
| [docs/lambda-line-by-line.md](docs/lambda-line-by-line.md) | The function explained line by line |
| [docs/cost-log.md](docs/cost-log.md) | Credit tracking against the $30 internal ceiling |
| [docs/cleanup-checklist.md](docs/cleanup-checklist.md) | End-of-session and end-of-project shutdown steps |
| [lambda/](lambda/README.md) | The code, its tests, and deploy steps |
| [config/](config/README.md) | Event patterns and IAM policies |
| [incidents/](incidents/) | Incident records for each controlled test (and a template) |
| [evidence/](evidence/manifest.md) | Original (unredacted) screenshots, log samples, test output, and the evidence manifest with SHA-256 hashes |

## What is deliberately *not* in this repository

- No secret keys or passwords. The screenshots are published unredacted, so they show the Learner Lab account ID, source IP address, and lab user details (see [evidence/manifest.md](evidence/manifest.md)).
- No raw CloudTrail logs. Originals stay offline; only redacted samples are published.
- No credentials of any kind. The Lambda function gets its permissions from its execution role, never from keys in code.

## Timeline

| Dates | Work | Status |
|---|---|---|
| Aug 28 – Sep 4 | Topic, proposal, AWS access | ✅ |
| Late Sep – Oct 2 | Foundation, logging, alerting, TEST-01 and TEST-02 | ✅ |
| Oct 9 | Midterm presentation | ✅ |
| Oct 22 | Lambda incident processor, 23 offline tests, least-privilege policies, final test procedures | ✅ |
| Oct 22 (evening) | TEST-03 to TEST-07 run and passed; Lambda deployed; incident records IR-03 to IR-05 | ✅ |
| Nov 7 – 19 | Demo recording, final paper, final README pass | 📅 |
| Nov 20 | Optional early final presentation | 📅 |
| Dec 4 | Final paper and repository due before class | 📅 |

## Scope and boundaries

All testing stays inside my Learner Lab account and uses synthetic data only. No denial-of-service, malware, phishing, scanning of systems I don't own, or attacks against AWS infrastructure. AWS access for this project was authorized by Professor Gustavo Allata of Wilbur Wright College.
