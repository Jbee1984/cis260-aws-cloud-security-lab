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
