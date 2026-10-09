# Cost log

Budget: **$50** Learner Lab credit · internal ceiling **$30** · reserve **$20**.
The Learner Lab cost display can lag, so each session records both an estimate and the displayed figure.

## Hourly costs of what is running (us-east-1, approximate on-demand prices)

| Resource | Rate | Notes |
|---|---|---|
| EC2 t3.micro | $0.0104/hour | Only while running |
| Public IPv4 address | $0.005/hour | Only while the instance is running (auto-assigned address is released on stop) |
| EBS root volume (gp3) | ≈ $0.08 per GB-month | Billed even while the instance is stopped |
| CloudTrail trail | $0 | The first copy of management events delivered to S3 is free |
| S3 storage | ≈ $0.023 per GB-month | Log files are a few KB each |
| SNS email | $0 at this volume | Well under the free tier |
| EventBridge (AWS service events) | $0 | Events from AWS services on the default bus are free |

**While the instance runs:** ≈ $0.0154/hour ≈ **$0.37/day**.

## Session journal

| Date | Resources running | Hours | Estimated cost | Credit shown in Learner Lab | Shutdown done? |
|---|---|---|---|---|---|
| 2026-10-02 | `cis260-target` (from ~12:10 PM CDT), trail, bucket, topic | Session 10:28 AM – ~2:28 PM CDT (4-hour timer) | ≈ $0.04 for the instance + IPv4 address | **Used $1.4 of $50** (read 3:40 PM CDT; includes all earlier usage) | Lab session expired on its own; TODO confirm the instance is stopped |
