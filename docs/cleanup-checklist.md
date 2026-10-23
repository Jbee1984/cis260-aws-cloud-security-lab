# Cleanup checklist

## End of every work session

- [ ] Remove any temporary test rules (for example the TEST-01/TEST-03 port 8080 rules) and confirm `cis260-target-sg` has **0 inbound rules**
- [ ] Stop any test listener (`Ctrl+C`), terminate `cis260-test-client` if it exists, and delete `cis260-test-client-sg` once it has no attachments
- [ ] Make sure every alert rule that was disabled for a test (TEST-07) is **Enabled** again
- [ ] Stop `cis260-target` (EC2 → Instance state → **Stop instance**) and wait for **Stopped**
- [ ] Check **both** allowed regions (us-east-1 and us-west-2) for anything left running
- [ ] Record the remaining Learner Lab credit in the [cost log](cost-log.md)
- [ ] Write the work-log entry, including the next unfinished task
- [ ] End the Learner Lab session

Leaving the trail, buckets, topic, rules, alarm, and Lambda function in place costs almost nothing and keeps evidence collection working.

## End of the project (after grading)

Export everything needed for the record **first**, then delete in this order (dependencies first):

1. [ ] Download any evidence still needed from the S3 buckets (CloudTrail logs, Flow Logs, incident records)
2. [ ] Delete the Lambda-target rules `cis260-lambda-sg`, `cis260-lambda-ec2`, `cis260-monitoring-integrity`, `cis260-s3-control`, then the function `cis260-incident-processor` (and its log group, if one was created)
3. [ ] Delete EventBridge rules `cis260-ec2-api-changes` and `cis260-sg-changes`
4. [ ] Delete CloudWatch alarm `cis260-cpu-high`
5. [ ] Delete the SNS subscription and topic `cis260-security-alerts`
6. [ ] Delete flow log `cis260-subnet-flowlog`; stop logging and delete trail `cis260-management-trail`
7. [ ] Empty and delete each bucket: `cis260-security-logs-jbanks-20261002`, `cis260-flowlogs-jbanks-20261002`, `cis260-incident-records-jbanks`, `cis260-s3-control-test-jbanks`. With versioning on, choose **Show versions** and delete every version, otherwise the bucket isn't really empty. Deleting versions is permanent.
8. [ ] Terminate `cis260-target`; confirm its EBS volume is deleted
9. [ ] Delete security group `cis260-target-sg`
10. [ ] Remove the route `0.0.0.0/0`, disassociate and delete route table `cis260-lab-rt`
11. [ ] Detach and delete internet gateway `cis260-Lab-igw`
12. [ ] Delete subnet `cis260-lab-subnet`, then VPC `cis260-security-VPC`
13. [ ] Check both regions one last time, and record the final credit
