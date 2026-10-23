# Least privilege and LabRole

**Short version:** everything in this lab runs as one shared role, LabRole, because Learner Lab blocks creating new roles. LabRole can do much more than any one part of the lab needs. In a real account I would replace it with three small roles, one per job. The policies for those roles are written in [`config/iam/`](../config/iam/).

## What LabRole is

An **IAM role** is a set of permissions that an AWS service can take on ("assume") to get temporary credentials. It has no password or long-term keys.

Learner Lab gives every student one ready-made role, **LabRole**, and denies `iam:CreateRole`, so I can't make my own. In this lab, three different things use it:

| Who uses LabRole | How | What it actually needs |
|---|---|---|
| EC2 instance `cis260-target` | Through the instance profile `LabInstanceProfile`; the server reads temporary credentials from the instance metadata service | Only what the Systems Manager agent needs, so Session Manager works |
| EventBridge rules `cis260-sg-changes`, `cis260-ec2-api-changes` | As each rule target's execution role | Only `sns:Publish` on topic `cis260-security-alerts` |
| Lambda `cis260-incident-processor` | As its execution role | Only `s3:PutObject` on one bucket prefix, `sns:Publish` on one topic, and writing its own logs |

## Why it matters

**Blast radius:** if anything using the role is compromised, the attacker gets *everything the role allows*, not just what that one part needed.

Example: if someone got a shell on `cis260-target` and took its temporary credentials, they would hold all of LabRole's permissions across the account. They could read buckets or change security groups, not just talk to Systems Manager. Requiring **IMDSv2** makes stealing those credentials harder, but it doesn't shrink what they allow.

## What I would change: three roles, each with one job

| Role (production) | Permissions | Reference |
|---|---|---|
| `cis260-ec2-ssm-role` (instance profile) | AWS managed policy **AmazonSSMManagedInstanceCore** only: enough for the SSM agent, nothing else | AWS managed policy; no custom JSON needed |
| `cis260-eventbridge-sns-role` | `sns:Publish` on `cis260-security-alerts` only | [`config/iam/eventbridge-to-sns-policy.json`](../config/iam/eventbridge-to-sns-policy.json) |
| `cis260-incident-processor-role` | `s3:PutObject` on `cis260-incident-records-jbanks/incidents/*`; `sns:Publish` on the topic; create and write its own log group | [`config/iam/lambda-incident-processor-policy.json`](../config/iam/lambda-incident-processor-policy.json) |

Each role also has a **trust policy** that says which service may assume it. For the Lambda role it is `lambda.amazonaws.com`, limited to my account: [`config/iam/lambda-trust-policy.json`](../config/iam/lambda-trust-policy.json).

How I'd confirm the policies are tight enough, in a real account:

1. Use **IAM Access Analyzer → Generate policy**, which builds a policy from the role's real CloudTrail activity.
2. Run the same tests again.
3. Anything that now fails with `AccessDenied` shows a permission that is truly needed.

## What I did inside the lab's limits

- **No inbound rules and no SSH.** Nobody can connect *in* to use the instance's role.
- **IMDSv2 required** on the instance.
- **The Lambda function checks scope in code** (account, Region, API call, resource). Even with a broad role, it only ever writes one kind of record to one bucket and emails one topic.
- **The instance is stopped whenever I'm not working,** so its credentials aren't being issued.

## "What if you changed the role on the server?"

| Change | What happens |
|---|---|
| Remove the role | The SSM agent loses its credentials. Session Manager stops working and the instance shows as not managed. |
| Swap in a less powerful role (AmazonSSMManagedInstanceCore only) | Session Manager keeps working, and the server can no longer touch S3, security groups, or anything else. **This is the least-privilege fix.** |
| Swap in a *more* powerful role | That is a **privilege-escalation** path. Swapping the role is an API call (`AssociateIamInstanceProfile` / `ReplaceIamInstanceProfileAssociation`), so CloudTrail records it. Alerting on those two calls is a next step for this lab. |

In Learner Lab I can't create the smaller role, so I document it here instead of claiming I enforced it.
