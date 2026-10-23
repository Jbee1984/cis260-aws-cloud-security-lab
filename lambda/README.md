# Lambda — `cis260-incident-processor`

**Status:** ✅ **Deployed 2026-10-22 and tested end to end.**
- Offline: 23/23 tests ([output](../evidence/logs/2026-10-22_lambda-offline-tests.txt)).
- Synthetic: 2/2, recorded and ignored as expected.
- Real: every watched action produced a record whose name matches its CloudTrail event ID, with 0 errors. See [TEST-06](../docs/test-plan.md#test-06--lambda-incident-processor), [IR-05](../incidents/IR-05-alert-rule-disabled.md), and [TEST-05](../docs/test-plan.md#test-05--s3-versioning-change-on-an-empty-test-bucket-supplemental).

## What it does

The original alert rules email one sentence and stop there. This function adds a **case record**:

| Step | What happens | Why |
|---|---|---|
| 1. Scope check | Ignores the event unless it is from my account, in us-east-1, one of 7 watched API calls, **and** about my resource | No noise from anything outside the lab |
| 2. Evidence | Saves the complete CloudTrail event, unchanged, to `s3://cis260-incident-records-jbanks/incidents/<date>/<eventName>-<eventID>.json` | Every alert gets a permanent record named by its CloudTrail event ID, so the email, the record, and CloudTrail can be matched |
| 3. Alert | Emails what happened, succeeded or FAILED, which resource, who, when, from which IP, the event ID, and where the record is | An analyst can read it in seconds; a denied call is not reported as a real change |

It **never changes, stops, or deletes anything.** Deciding what an event means and fixing it is the analyst's job (see [decision D-12](../docs/decisions.md#d-12--lambda-records-evidence-it-does-not-fix-things-automatically)).

| Watched API call | Must be about | Environment variable |
|---|---|---|
| `AuthorizeSecurityGroupIngress`, `RevokeSecurityGroupIngress` | security group `cis260-target-sg` | `TARGET_GROUP_ID` |
| `StopInstances`, `StartInstances` | instance `cis260-target` | `TARGET_INSTANCE_ID` |
| `DisableRule`, `EnableRule` | alert rule `cis260-sg-changes` | `MONITORED_RULE_NAME` |
| `PutBucketVersioning` | empty test bucket `cis260-s3-control-test-jbanks` | `TEST_BUCKET_NAME` |

Every line is explained in [docs/lambda-line-by-line.md](../docs/lambda-line-by-line.md).

## Files

| File | What it is |
|---|---|
| [`lambda_function.py`](lambda_function.py) | The function (76 lines, 56 of them code) |
| [`test_lambda_function.py`](test_lambda_function.py) | 18 offline tests of the function, using fake S3 and SNS clients |
| [`test_event_patterns.py`](test_event_patterns.py) | 5 offline tests that the EventBridge patterns in `config/` match the right events |
| [`events/`](events/) | Synthetic test events (fake identity `Synthetic_Test`, documentation IP 203.0.113.10). Not CloudTrail exports |

## Run the tests (no AWS needed)

From the repository root:

```
python -m unittest discover -s lambda -v
```

Expected: `Ran 23 tests ... OK`. On Windows, use `py` instead of `python` if needed. Nothing else needs to be installed: the tests replace `boto3` with fakes.

## Deploy it (AWS console, us-east-1)

1. **Incident bucket:** S3 → Create bucket → `cis260-incident-records-jbanks` → keep **Block all public access** on and Object Ownership **Bucket owner enforced** → enable **Versioning** → encryption **SSE-S3** → Create.
2. **Function:** Lambda → Create function → Author from scratch → name `cis260-incident-processor` → runtime **Python 3.12** (or the newest Python offered) → architecture x86_64 → *Change default execution role* → **Use an existing role → LabRole** → Create.
3. **Code:** paste `lambda_function.py` into the editor's `lambda_function.py` → **Deploy**. The handler must be `lambda_function.lambda_handler`.
4. **Settings:** Configuration → General configuration → memory **128 MB**, timeout **10 seconds**. Leave VPC **unconfigured**: the function only calls S3 and SNS, so it needs no network inside my VPC and no NAT gateway.
5. **Environment variables** (Configuration → Environment variables). `AWS_REGION` is set by Lambda automatically:

| Key | Value |
|---|---|
| `LAB_ACCOUNT_ID` | `235317051044` |
| `TARGET_GROUP_ID` | `sg-06e94ae52286f9f2e` |
| `TARGET_INSTANCE_ID` | `i-085a300c3d2a60c75` |
| `MONITORED_RULE_NAME` | `cis260-sg-changes` |
| `TEST_BUCKET_NAME` | `cis260-s3-control-test-jbanks` |
| `INCIDENT_BUCKET` | `cis260-incident-records-jbanks` |
| `SNS_TOPIC_ARN` | `arn:aws:sns:us-east-1:235317051044:cis260-security-alerts` |

6. **Console test first:** Test → Create new event → paste [`events/synthetic-sg-authorize.json`](events/synthetic-sg-authorize.json) → Test. Expect `"status": "recorded"`, a new object under `incidents/` in the bucket, and an email. Then test [`events/synthetic-sg-other-group.json`](events/synthetic-sg-other-group.json) → expect `"reason": "resource"`, no object, no email. These are **synthetic** runs; label their screenshots that way.
7. **Triggers:** EventBridge → Event buses → default → Rules → Create rule, once per row. Target: **AWS service → Lambda function → `cis260-incident-processor`**, input **Matched events** (the function needs the full event; don't use an input transformer here):

| New rule | Event pattern file |
|---|---|
| `cis260-lambda-sg` | [`config/eventbridge-sg-change-rule.json`](../config/eventbridge-sg-change-rule.json) |
| `cis260-lambda-ec2` | [`config/eventbridge-ec2-api-changes.json`](../config/eventbridge-ec2-api-changes.json) |
| `cis260-monitoring-integrity` | [`config/eventbridge-monitoring-integrity.json`](../config/eventbridge-monitoring-integrity.json) |
| `cis260-s3-control` (supplemental) | [`config/eventbridge-s3-control.json`](../config/eventbridge-s3-control.json) |

8. **Invoke permission:** Lambda → Configuration → Permissions → *Resource-based policy statements* should list `events.amazonaws.com` for each rule (the console adds it when the rule is saved). The execution role (LabRole) controls what the function **may do**; this statement controls **who may start it**.

The original rules `cis260-sg-changes` and `cis260-ec2-api-changes` stay as they are. During testing, each change sends **two** emails: the one-line alert and the incident email. That is expected.

## Limits (stated honestly)

- **LabRole is far broader than this function needs.** Learner Lab doesn't allow creating roles. The least-privilege policy it *should* have is in [`config/iam/`](../config/iam/) and explained in [docs/least-privilege.md](../docs/least-privilege.md).
- **Not exactly-once.** EventBridge can retry. A retry rewrites the same S3 record name (the CloudTrail event ID), but it can send a second email.
- **A storage error stops the function before the email,** so no alert ever points to a record that wasn't saved. Lambda retries the event up to 2 more times, and the error shows in the function's Monitor tab and logs. The original one-line alert still arrives, because it comes from a separate rule.
- **No dead-letter queue.** For a production version I would add one, plus an alarm on the function's `Errors` metric.

## What was actually run (2026-10-22)

The deployment and tests were run in **AWS CloudShell** (decision [D-17](../docs/decisions.md#d-17--aws-cloudshell-and-the-cli-for-the-final-tests)). These are the commands, in order. Each one is also a CloudTrail event.

```bash
# 1. Private incident bucket
B=cis260-incident-records-jbanks
aws s3api create-bucket --bucket $B --object-ownership BucketOwnerEnforced
aws s3api put-public-access-block --bucket $B --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket $B --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $B --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# 2. Function (the code was copied in and checked by SHA-256 = 24a37b2b...d158b4698, the same file as the repo)
zip function.zip lambda_function.py
aws lambda create-function --function-name cis260-incident-processor \
  --runtime python3.12 --handler lambda_function.lambda_handler \
  --role arn:aws:iam::235317051044:role/LabRole --zip-file fileb://function.zip \
  --memory-size 128 --timeout 10 \
  --environment 'Variables={LAB_ACCOUNT_ID=235317051044,TARGET_GROUP_ID=sg-06e94ae52286f9f2e,TARGET_INSTANCE_ID=i-085a300c3d2a60c75,MONITORED_RULE_NAME=cis260-sg-changes,TEST_BUCKET_NAME=cis260-s3-control-test-jbanks,INCIDENT_BUCKET=cis260-incident-records-jbanks,SNS_TOPIC_ARN=arn:aws:sns:us-east-1:235317051044:cis260-security-alerts}'

# 3. Synthetic tests
aws lambda invoke --function-name cis260-incident-processor --payload fileb://synthetic-sg-authorize.json outA.json     # -> recorded
aws lambda invoke --function-name cis260-incident-processor --payload fileb://synthetic-sg-other-group.json outB.json   # -> ignored/resource

# 4. One rule per watched pattern: rule -> invoke permission -> target (repeated for each row of the table in "Deploy it")
R=$(aws events put-rule --name cis260-lambda-sg --event-pattern file://../config/eventbridge-sg-change-rule.json \
      --state ENABLED --query RuleArn --output text)
aws lambda add-permission --function-name cis260-incident-processor --statement-id cis260-lambda-sg \
  --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn $R
aws events put-targets --rule cis260-lambda-sg \
  --targets Id=incident-processor,Arn=arn:aws:lambda:us-east-1:235317051044:function:cis260-incident-processor
```

The patterns were pasted inline in CloudShell; they are identical to the files in [`config/`](../config/). The `--source-arn` on each permission means only that one rule can start the function.

Lambda created its log group `/aws/lambda/cis260-incident-processor` automatically, which shows LabRole is allowed to write logs.
