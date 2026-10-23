# Decision log

Why the lab is built the way it is. Each decision lists the alternatives I considered.

---

## D-01 — Session Manager instead of SSH
**Decision:** administer the instance only through Systems Manager Session Manager; no inbound rules at all.
**Why:** SSH needs an open inbound port (22) and private-key management. An open port is constantly scanned on the internet, and a leaked key gives direct access. Session Manager needs no inbound port, no keys, and access is controlled and logged through IAM and CloudTrail.
**Alternative rejected:** SSH limited to my home IP — still an open port, and home IPs change.

## D-02 — S3 as the log and evidence store
**Decision:** CloudTrail (and later VPC Flow Logs) deliver to a protected S3 bucket.
**Why:** CloudTrail-to-CloudWatch Logs is restricted in Learner Lab. S3 is cheap, durable, and supports versioning and Block Public Access. A log-analysis server (SIEM) would run around the clock and use up the credit.

## D-03 — Outbound limited to HTTPS (443)
**Decision:** replaced the default "all traffic" outbound rule with HTTPS only.
**Why:** least privilege. Session Manager and package updates use HTTPS. If the instance were compromised, it couldn't easily use other ports to reach attacker infrastructure.

## D-04 — Internet gateway and public IP instead of a NAT gateway
**Decision:** the instance gets an auto-assigned public IPv4 address and reaches AWS through the internet gateway; inbound stays closed.
**Why — cost comparison (us-east-1, approximate):**

| Option | Cost |
|---|---|
| Public IPv4 address | $0.005/hour ≈ $0.12/day (only while running) |
| NAT gateway | $0.045/hour ≈ $1.08/day + data charges |
| Interface VPC endpoints for SSM (3 needed) | ≈ $0.01/hour each ≈ $0.72/day |

The public address is reachable, but with no inbound rules the security group drops any connection attempt.

## D-05 — Multi-region trail
**Decision:** the trail records all regions.
**Why:** Learner Lab allows us-east-1 and us-west-2. A forgotten or unexpected resource in the other region would otherwise be invisible.

## D-06 — SSE-S3 encryption instead of KMS
**Decision:** default encryption with Amazon S3-managed keys.
**Why:** encrypts at rest with no extra cost and no key policy to manage. KMS adds per-request charges and key policies that Learner Lab may restrict. SSE-C is blocked so nobody can upload objects encrypted with their own key.

## D-07 — Alerts built on CloudTrail API events
**Decision:** both alert rules match "AWS API Call via CloudTrail" events (`StopInstances`/`StartInstances` for the server; `AuthorizeSecurityGroupIngress`/`RevokeSecurityGroupIngress` for the security group).
**Why:** the alert *is* the API record, so every email already says who made the change, when, and from where.
**Alternative considered:** EC2's "Instance State-change Notification" events arrive without CloudTrail, but they only say *what* happened, not *who* caused it.

## D-08 — Rules scoped to my own resources
**Decision:** each rule matches only `cis260-target-sg` or `cis260-target`.
**Why:** narrow rules keep alerts meaningful and tie each email to one test. Broad rules create alert fatigue.

## D-09 — $30 internal budget ceiling
**Decision:** plan to spend at most $30 of the $50 credit and keep $20 in reserve.
**Why:** the Learner Lab cost display can lag, so late charges or a mistake shouldn't end the project.

## D-10 — t3.micro instance
**Decision:** one t3.micro target, stopped whenever I'm not working.
**Why:** enough for Amazon Linux, the SSM agent, and a short CPU test; about $0.0104/hour.

## D-11 — Readable alerts with an input transformer
**Decision:** each rule target uses an EventBridge input transformer instead of forwarding the raw event.
**Why:** the raw JSON alerts were accurate but slow to read. A one-line alert (what, which resource, who, when, from where) lets anyone triage in seconds; the complete record stays in CloudTrail and the S3 evidence bucket.
**Alternative considered:** a Lambda function to format the message — rejected because the transformer needs no code and nothing extra to secure or pay for.

## D-12 — Lambda records evidence; it does not fix things automatically
**Decision (2026-10-22):** add one small Python Lambda function, `cis260-incident-processor`. It checks that an event belongs to the lab, saves the full event to S3 as a named incident record, and emails a readable summary. It never changes, stops, or deletes anything.
**Why:** the one-line alerts (D-11) are good for noticing a change, but they leave no case record that links the email to the exact CloudTrail event. The function adds that record, a second scope check in code, and FAILED-versus-succeeded reporting for denied calls.
**Alternative rejected: automatic revocation** (a function that removes any new inbound rule by itself). It can't tell an approved change from a malicious one, could break a legitimate change, and is much harder to test safely. For this lab, a person reviews the evidence and makes the fix, and the fix is retested.
**Still true from D-11:** formatting alone didn't justify code; the input transformer still formats the original alerts.

## D-13 — Monitoring integrity is the before/after security improvement
**Decision:** the improvement is a new rule that alerts when the security-group alert rule is disabled or enabled ([control-improvement.md](control-improvement.md)).
**Why:** turning off alerts before making a change is a common attacker step. Before the change, disabling `cis260-sg-changes` produced no alert at all; it was only recorded in CloudTrail. The improvement is small, safe to test (disable, then enable right away), and gives clear before/after evidence.

## D-14 — Separate private bucket for incident records
**Decision:** incident records go to `cis260-incident-records-jbanks`, not into the CloudTrail bucket.
**Why:** the CloudTrail bucket's policy only lets CloudTrail write, and only for my trail (D-02). Keeping the function's records in their own bucket leaves that policy untouched and separates raw logs (written by AWS) from case records (written by my code). Same protections: Block Public Access, SSE-S3, versioning.

## D-15 — Lambda outside the VPC
**Decision:** the function is not attached to the VPC.
**Why:** it only calls the S3 and SNS public endpoints. Attaching it to a VPC subnet would need a NAT gateway (about $1/day) or VPC endpoints for it to reach those services (D-04), and it gains nothing.

## D-16 — Separate Lambda rules; the original alert rules stay
**Decision:** new rules (`cis260-lambda-sg`, `cis260-lambda-ec2`) send events to the function. The original SNS rules are not changed.
**Why:** if the function fails, the original one-line alerts still arrive (a rollback path that is already working). It also keeps the integrity test independent: disabling `cis260-sg-changes` doesn't stop `cis260-lambda-sg` from recording security-group changes. The cost is two emails per change during testing, which is expected and documented.

## D-17 — AWS CloudShell and the CLI for the final tests
**Decision (2026-10-22):** the final-phase tests and the Lambda deployment were run as AWS CLI commands in **AWS CloudShell**, a browser terminal that uses my console sign-in. The servers were reached with Session Manager, and the console was used where a picture shows the result better (the CloudWatch alarm graph and history).
**Why:**
- Every command prints its own UTC time, so each step can be matched to CloudTrail.
- The exact commands are kept in the repository, so anyone can repeat the build ([lambda/README.md](../lambda/README.md#what-was-actually-run-2026-10-22)).
- CloudShell needs no access keys on my PC.
- Each API call is still recorded by CloudTrail like a console click.

**Trade-off:** fewer console screenshots. The CLI output screenshots show the same facts with timestamps.
