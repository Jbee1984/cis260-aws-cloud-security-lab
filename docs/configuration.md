# Configuration — every resource, every setting, and why

Region: **us-east-1 (N. Virginia)**. All names start with `cis260-` so project resources are easy to find and clean up.

---

## 1. VPC — `cis260-security-VPC`

| Setting | Value | Why |
|---|---|---|
| IPv4 CIDR | 10.26.0.0/16 | A private range only this lab uses; room for more subnets later |
| Tenancy | Default | Dedicated tenancy costs much more and isn't needed |

A VPC is my own isolated network inside AWS. Nothing gets in or out unless I add a gateway and routes.

## 2. Subnet — `cis260-lab-subnet`

| Setting | Value | Why |
|---|---|---|
| IPv4 CIDR | 10.26.1.0/24 | 251 usable addresses — far more than one target needs |
| Public IPv4 | Auto-assigned to the instance | The instance needs an address that can reach AWS service endpoints through the internet gateway |

## 3. Internet gateway — `cis260-Lab-igw`

Attached to `cis260-security-VPC`. It connects the VPC to the internet so the instance can reach the Systems Manager endpoints over HTTPS.
**Why not a NAT gateway?** A NAT gateway costs about $0.045/hour (≈ $1/day) before data charges — too expensive for a $50 credit. See [decisions.md](decisions.md#d-04--internet-gateway-and-public-ip-instead-of-a-nat-gateway).

## 4. Route table — `cis260-lab-rt`

| Destination | Target | Meaning |
|---|---|---|
| 10.26.0.0/16 | local | Traffic inside the VPC stays inside the VPC (created automatically) |
| 0.0.0.0/0 | `cis260-Lab-igw` | Everything else goes out through the internet gateway |

- **Main route table:** No — this is a custom table.
- **Explicit subnet association:** `cis260-lab-subnet`. A custom route table only affects subnets explicitly associated with it.

## 5. Security group — `cis260-target-sg`

Description: *CIS260 lab server managed through Session Manager*.

| Direction | Rule | Why |
|---|---|---|
| Inbound | **none** | No connection can be started *to* the instance from anywhere. No SSH (port 22). |
| Outbound | HTTPS, TCP 443, destination 0.0.0.0/0 | The SSM agent reaches Systems Manager over HTTPS. The default "all traffic" outbound rule was removed (least privilege). |

Security groups are **stateful**: replies to connections the instance starts are allowed back in automatically, even with zero inbound rules. That is why Session Manager works.

DNS lookups to the VPC's Amazon-provided resolver and instance metadata requests are not filtered by security groups, so they still work with HTTPS-only outbound.

## 6. EC2 target — `cis260-target`

| Setting | Value | Why |
|---|---|---|
| AMI | Amazon Linux 2023 | Supported by AWS, SSM agent preinstalled |
| Instance type | t3.micro | Smallest practical size (≈ $0.0104/hour) |
| IAM role | LabRole (through the lab-provided instance profile) | Learner Lab doesn't allow creating roles; LabRole includes the permissions Systems Manager needs |
| Metadata | **IMDSv2 required** | Requires a session token for metadata requests, which blocks SSRF-style theft of instance credentials |
| Key pair | none needed | Access is through Session Manager only |
| Status checks | System, instance, and EBS checks passed | Instance is healthy |
| Root volume | 15 GiB gp3, **encrypted** (`vol-0bdfdbf9b6d51b67b`) | Checked 2026-10-22 |
| CPU credits | Standard | A CPU test can't run up surplus-credit charges (TEST-04) |
| Private IP / interface | 10.26.1.235 / `eni-0e9467ff27cb756eb` | Stays the same across stop/start; used to read Flow Logs |

## 7. Systems Manager Session Manager

- Start: EC2 console → instance → **Connect** → **Session Manager** → Connect.
- The SSM agent on the instance keeps an outbound HTTPS connection to Systems Manager. My browser session is relayed through AWS — no inbound port is ever opened.
- Sessions run as `ssm-user`. Access is controlled by IAM, and session starts are recorded in CloudTrail — verified 2026-10-02: a `StartSession` record (ssm.amazonaws.com) at 21:57:56 UTC with my identity.

## 8. CloudTrail trail — `cis260-management-trail`

| Setting | Value | Why |
|---|---|---|
| Events | Management events (API activity) | Records who changed what in the account |
| Multi-region | Yes | Also records activity in other regions (e.g., a forgotten resource in us-west-2) |
| Insights | Disabled | Extra cost; not needed for the project |
| Destination | S3 bucket `cis260-security-logs-jbanks-20261002` | Permanent, protected copy of the evidence |
| CloudWatch Logs | Not configured | Restricted in Learner Lab; S3 is the planned destination |
| Status | Logging | Verified by finding a delivered log file, not just the status text |

**Why a trail, if CloudTrail already has Event history?** Event history keeps only 90 days of management events and isn't a protected evidence store. The trail writes log files to S3, where versioning and access controls protect them.

CloudTrail delivers log files to S3 about every 5 minutes, so S3 is the **evidence** path, not the alerting path.

## 9. S3 evidence bucket — `cis260-security-logs-jbanks-20261002`

| Setting | Value | Why |
|---|---|---|
| Block all public access | On (all four settings) | The bucket and its objects can never be made public by accident |
| Default encryption | SSE-S3 (Amazon S3-managed keys) | Logs are encrypted at rest at no extra cost; SSE-C (customer-provided keys) is blocked |
| Bucket Key | Disabled | Only matters for KMS encryption |
| Versioning | Enabled | Overwritten or deleted evidence can be recovered |
| MFA delete | Disabled | Requires the account root user, which Learner Lab doesn't provide |
| Bucket policy | Created for CloudTrail: allows `cloudtrail.amazonaws.com` to check the bucket ACL and write log files, **only when `aws:SourceArn` is my trail** | Least privilege, and prevents another account's trail from writing into my bucket ("confused deputy" protection) |

## 10. SNS topic — `cis260-security-alerts`

| Setting | Value | Why |
|---|---|---|
| Type | Standard | Email doesn't need FIFO ordering |
| Subscription | Email (my school address), status **Confirmed** | A subscription receives nothing until it is confirmed from the inbox |
| Manual test | Message `SNS-01` published 1:36 PM CDT, received | Proves the email path, not yet an AWS-triggered alert |

## 11. VPC Flow Log — `cis260-subnet-flowlog`

| Setting | Value | Why |
|---|---|---|
| Flow log ID | fl-0a8056794f234d676 | |
| Created | 2026-10-02, 4:47:59 PM CDT | |
| Traffic type | All | Records both ACCEPT and REJECT decisions — Test 3 needs to see rejected traffic |
| Destination | S3 bucket `cis260-flowlogs-jbanks-20261002` | Network logs kept separate from the CloudTrail evidence bucket |
| IAM role | none | Delivery to S3 is authorized by the bucket policy, not a role |
| Max aggregation interval | 1 minute | Records appear sooner, which makes tests faster to check (the default is 10 minutes) |
| Log format | Default | Standard fields: account, interface, source/destination address and port, protocol, packets, bytes, start/end time, action (ACCEPT/REJECT), log status |
| File format / partitions | Plain text, partitioned daily, Hive-compatible partitions off | Simple to read in S3 |

**What Flow Logs add:** CloudTrail shows *API calls* (who changed what). Flow Logs show *network traffic* metadata (which addresses and ports talked, and whether the security group accepted or rejected it). They record metadata only — never packet contents.

**Verified 2026-10-22** (`2026-10-22_40_inventory-before.jpg`):
- The flow log is attached to `subnet-03af475ebf3cc4b29` (`cis260-lab-subnet`), status ACTIVE, delivery SUCCESS.
- The flow-log bucket has all four Block Public Access settings on, SSE-S3 (AES256), and versioning Enabled.
- Files arrive in S3 every 5 minutes.
- Because it is attached to the subnet, it records every network interface in it. TEST-03 used that to see the client's ACCEPT and the target's REJECT for the same packets ([IR-03](../incidents/IR-03-blocked-vs-allowed-traffic.md)).

## 12. CloudWatch alarm — `cis260-cpu-high`

| Setting | Value | Why |
|---|---|---|
| Metric | EC2 `CPUUtilization` for `cis260-target` | Standard EC2 metric, no agent needed |
| Condition | > 10 % for 1 datapoint within 5 minutes | Low threshold so the controlled CPU test (Test 4) trips it quickly; an idle t3.micro sits well below 10 % |
| Actions | Enabled | Verified 2026-10-22: "When alarm transitions to in alarm, send message to topic cis260-security-alerts" (`2026-10-22_46_test4-alarm-action.jpg`). Fired for real in TEST-04 (ALARM 23:58:15 UTC, action executed; OK 00:05:15). No OK notification is configured; recovery is visible in the alarm history |
| State | Insufficient data at creation (22:11:08 UTC), then **OK** at 22:12:01 UTC | Insufficient data is normal until the first datapoints arrive; OK means the alarm is receiving data and CPU is below 10 % |

## 13. EventBridge rules

Rules on the **default event bus in us-east-1**. The event patterns and a line-by-line explanation are in [config/README.md](../config/README.md).

| Rule | Listens for | Scope | Target | Status |
|---|---|---|---|---|
| `cis260-ec2-api-changes` | `StopInstances` / `StartInstances` API calls recorded by CloudTrail | Only `cis260-target` | SNS (one-line alert) | ✅ Created and enabled 2026-10-02, 4:24 PM CDT |
| `cis260-sg-changes` | `AuthorizeSecurityGroupIngress` / `RevokeSecurityGroupIngress` API calls recorded by CloudTrail | Only `cis260-target-sg` | SNS (one-line alert) | ✅ Created and enabled 2026-10-02, 5:26 PM CDT |
| `cis260-lambda-sg` | Same pattern as `cis260-sg-changes` | Only `cis260-target-sg` | Lambda `cis260-incident-processor` | ✅ Created 2026-10-22, 7:12 PM CDT (00:12:45 UTC) |
| `cis260-lambda-ec2` | Same pattern as `cis260-ec2-api-changes` | Only `cis260-target` | Lambda | ✅ Created 2026-10-22, 7:12 PM CDT (00:12:45 UTC) |
| `cis260-monitoring-integrity` | `DisableRule` / `EnableRule` | Only rule `cis260-sg-changes` | Lambda | ✅ Created 2026-10-22, 7:19 PM CDT (00:19:38 UTC), the security improvement |
| `cis260-s3-control` | `PutBucketVersioning` | Only bucket `cis260-s3-control-test-jbanks` | Lambda | ✅ Created 2026-10-22, 7:21 PM CDT (TEST-05) |

The SNS targets use the settings below. The Lambda targets use **Matched events** (the function needs the full event) and are allowed to invoke the function by its resource-based policy, which the console adds when the rule is saved.

| Target setting | Value | Why |
|---|---|---|
| Target | SNS topic `cis260-security-alerts` | Delivers the alert by email |
| Input | Originally **Matched event** (raw JSON); changed to an **Input transformer** — one readable sentence (ISSUE-03, D-11) | The email states what happened, to which resource, who, when, and from where |
| Execution role | LabRole | Learner Lab doesn't allow creating a dedicated role; LabRole is allowed to publish to SNS |
| Dead-letter queue | None | Not needed at lab scale; failed deliveries show up as `FailedInvocations` in rule monitoring |

## 14. Lambda function — `cis260-incident-processor` (deployed 2026-10-22, 00:10:47 UTC)

Code, tests, and deploy steps: [lambda/README.md](../lambda/README.md). Every line explained: [lambda-line-by-line.md](lambda-line-by-line.md).

| Setting | Value | Why |
|---|---|---|
| Runtime | Python 3.12 (or the newest Python the console offers) | `boto3` is built in; nothing to package |
| Handler | `lambda_function.lambda_handler` | File name + function name |
| Memory / timeout | 128 MB / 10 seconds | One S3 write and one SNS publish take well under a second |
| Execution role | LabRole | Learner Lab blocks creating roles; the least-privilege policy it *should* have is in [config/iam/](../config/iam/) ([least-privilege.md](least-privilege.md)) |
| VPC | Not attached | Only calls the S3 and SNS public endpoints; attaching it would need a NAT gateway or endpoints (D-15) |
| Environment variables | `LAB_ACCOUNT_ID`, `TARGET_GROUP_ID`, `TARGET_INSTANCE_ID`, `MONITORED_RULE_NAME`, `TEST_BUCKET_NAME`, `INCIDENT_BUCKET`, `SNS_TOPIC_ARN` | No IDs hard-coded in the code |
| Triggers | The four Lambda-target rules in section 13 | — |

## 15. S3 incident bucket — `cis260-incident-records-jbanks` (created 2026-10-22, 00:09:18 UTC)

Same protections as the CloudTrail bucket: Block all public access **on**, Bucket owner enforced, **SSE-S3**, **versioning on**. No bucket policy is needed: the function writes with its execution role. Records are stored as `incidents/<YYYY-MM-DD>/<eventName>-<CloudTrail eventID>.json` (D-14).

## 16. Temporary resources for tests

| Resource | Test | Settings | Removed |
|---|---|---|---|
| `cis260-test-client` (EC2, `i-0a86e4bcc5db5a721`, 10.26.1.241) | TEST-03 | t3.micro, Amazon Linux 2023, project subnet, public IPv4 for Session Manager only, LabInstanceProfile, IMDSv2 required, Standard CPU credits, encrypted root volume, no key pair | ✅ Launched 23:53:05 UTC, terminated 00:06:11 UTC |
| `cis260-test-client-sg` (`sg-0551ab694cd8f8633`) | TEST-03 | No inbound; outbound 443 to 0.0.0.0/0 and 8080 to `cis260-target-sg` only | ✅ Deleted after the client was terminated |
| `cis260-s3-control-test-jbanks` (S3) | TEST-05 | Empty, private, SSE-S3; versioning turned on during the test (00:22:18 UTC) | Kept until grading, then deleted |
