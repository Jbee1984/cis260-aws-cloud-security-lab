# Cleanup checklist

## End of every work session

- [ ] Remove any temporary test rules (e.g., `TEST-01 temporary`) and confirm `cis260-target-sg` has **0 inbound rules**
- [ ] Terminate any temporary test instances
- [ ] Stop `cis260-target` (EC2 → Instance state → **Stop instance**) and wait for **Stopped**
- [ ] Check **both** allowed regions (us-east-1 and us-west-2) for anything left running
- [ ] Record the remaining Learner Lab credit in the [cost log](cost-log.md)
- [ ] Write the work-log entry, including the next unfinished task
- [ ] End the Learner Lab session

Leaving the trail, bucket, topic, and rules in place costs almost nothing and keeps evidence collection working.

## End of the project (after December 4)

Export everything needed for the record **first**, then delete in this order (dependencies first):

1. [ ] Download any evidence still needed from S3
2. [ ] Delete EventBridge rules `cis260-ec2-api-changes` and `cis260-sg-changes`
3. [ ] Delete the SNS subscription and topic `cis260-security-alerts`
4. [ ] Stop logging and delete trail `cis260-management-trail` (and Flow Logs, alarms when added)
5. [ ] Empty bucket `cis260-security-logs-jbanks-20261002` — with versioning on, choose **Show versions** and delete every version — then delete the bucket
6. [ ] Terminate `cis260-target`; confirm its EBS volume is deleted
7. [ ] Delete security group `cis260-target-sg`
8. [ ] Remove the route `0.0.0.0/0`, disassociate and delete route table `cis260-lab-rt`
9. [ ] Detach and delete internet gateway `cis260-Lab-igw`
10. [ ] Delete subnet `cis260-lab-subnet`, then VPC `cis260-security-VPC`
11. [ ] Check both regions one last time, and record the final credit
