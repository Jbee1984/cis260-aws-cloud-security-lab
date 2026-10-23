# `lambda_function.py`, line by line

The function is 76 lines; 56 are code. Every one is explained here, in order. Code is in [lambda/lambda_function.py](../lambda/lambda_function.py).

## Imports and clients (lines 7–13)

| Code | What it means |
|---|---|
| `import json` | Python's built-in JSON tools. Used to turn the event back into JSON text before saving it. |
| `import os` | Python's built-in access to the operating system. Used to read environment variables (`os.environ`). |
| `import boto3` | The AWS SDK for Python. It is already installed in every Python Lambda, so nothing has to be packaged with the code. |
| `s3 = boto3.client("s3")` | A client for Amazon S3. Created **outside** the handler, so a warm Lambda reuses it instead of creating a new one on every run (an AWS best practice). |
| `sns = boto3.client("sns")` | A client for Amazon SNS, created the same way. |

The clients use the function's **execution role** (LabRole) automatically. No access keys appear anywhere in the code.

## The watch list (lines 16–24)

`WATCHED` is a dictionary. Each **key** is an API call name exactly as CloudTrail spells it. Each **value** is the name of the environment variable that holds the one resource that call must be about.

Example: `"StopInstances": "TARGET_INSTANCE_ID"` means *a StopInstances call only counts if it names the instance in TARGET_INSTANCE_ID.*

Keeping IDs in environment variables means the code holds no account-specific values. Changing the instance means changing a setting, not the code.

## `resource_of(name, params)` (lines 27–36)

Each AWS service records the affected resource in a different field of `requestParameters`. This function returns the right one:

| Code | What it means |
|---|---|
| `if name in ("StopInstances", "StartInstances"):` | EC2 start and stop requests |
| `items = params.get("instancesSet", {}).get("items", [])` | EC2 stores instance IDs in a **list** (one request can stop several instances). `.get(key, default)` returns the default instead of crashing when a field is missing. |
| `return items[0].get("instanceId") if items else None` | The first instance ID, or `None` if the list is empty |
| `if name in ("DisableRule", "EnableRule"):` / `return params.get("name")` | EventBridge records the rule's name in `name` |
| `if name == "PutBucketVersioning":` / `return params.get("bucketName")` | S3 records the bucket in `bucketName` |
| `return params.get("groupId")` | Everything left is a security-group call, which uses `groupId` |

## The handler: setup (lines 39–41)

| Code | What it means |
|---|---|
| `def lambda_handler(event, context):` | The function Lambda calls. `event` is the EventBridge event (a dictionary). `context` holds run information like time remaining; this code doesn't need it. |
| `detail = event.get("detail", {})` | The CloudTrail record sits under `detail` |
| `name = detail.get("eventName")` | Which API call happened, for example `StopInstances` |

## Step 1: scope check (lines 43–52)

Four questions, in order. The first "no" ends the run with `{"status": "ignored", "reason": ...}`, with no record and no email.

| Code | Question |
|---|---|
| `if event.get("account") != os.environ["LAB_ACCOUNT_ID"]:` | Is it from **my** AWS account? |
| `if event.get("region") != os.environ["AWS_REGION"]:` | Is it in the **Region the function runs in** (us-east-1)? Lambda sets `AWS_REGION` itself. |
| `if name not in WATCHED:` | Is it one of the **7 watched** API calls? |
| `resource = resource_of(name, detail.get("requestParameters") or {})` | Find the resource. `or {}` turns a missing or `null` value into an empty dictionary so nothing crashes. |
| `if resource is None or resource != os.environ.get(WATCHED[name]):` | Is it about **my** resource? `WATCHED[name]` gives the variable's name, and `os.environ.get(...)` gives its value. |

The EventBridge rules already filter on most of this. The function checks again anyway (**defense in depth**): if a rule is edited wrong, or someone runs the function by hand with other input, it still won't record or email things outside the lab.

## Step 2: evidence record (lines 54–62)

| Code | What it means |
|---|---|
| `event_id = detail.get("eventID", "no-event-id")` | CloudTrail's unique ID for this API call |
| `` key = f"incidents/{detail.get('eventTime', 'unknown')[:10]}/{name}-{event_id}.json" `` | The record's name, for example `incidents/2026-10-22/StopInstances-<id>.json`. `[:10]` keeps just the date part of the timestamp, so records group by day. |
| `s3.put_object(` | Save one object to S3 |
| `Bucket=os.environ["INCIDENT_BUCKET"],` | The private incident bucket |
| `Key=key,` | The name built above |
| `Body=json.dumps(event, indent=2).encode("utf-8"),` | The **whole event, unchanged**, as readable JSON text turned into bytes |
| `ContentType="application/json",` | Tells S3 (and a browser) the file is JSON |
| `)` | End of the call. If it fails, Python raises an error, the function stops here, and **no email is sent**. |

Naming the file after the event ID means a retry of the same event overwrites one record instead of making a duplicate.

## Step 3: readable alert (lines 64–76)

| Code | What it means |
|---|---|
| `` outcome = f"FAILED ({detail['errorCode']})" if detail.get("errorCode") else "succeeded" `` | CloudTrail records denied calls too, with an `errorCode`. A denied call is reported as **FAILED**, so a blocked attempt is never mistaken for a real change. |
| `message = "\n".join([ ... ])` | Builds the email from 7 lines joined with line breaks: the call and outcome, resource, who (`userIdentity.arn`), when (UTC), from which IP, the CloudTrail event ID, and the record's S3 location |
| `.get('userIdentity', {}).get('arn', 'unknown')` | If a field is missing, the email says `unknown` instead of the function crashing |
| `sns.publish(TopicArn=..., Subject=..., Message=message)` | Sends the email through the existing confirmed topic `cis260-security-alerts` |
| `return {"status": "recorded", "key": key}` | Shown in the Lambda console and logs, and checked by the tests |

## Questions to be ready for

- **Why Lambda if EventBridge can already email?** The rule's email is one sentence and disappears into an inbox. The function adds a permanent, named case record that links the email to the exact CloudTrail event, plus a scope check and FAILED-versus-succeeded reporting.
- **Why doesn't it fix things automatically?** An automatic fix can't tell an approved change from a malicious one, and it could break a legitimate change. I kept the human decision in the loop (decision D-12).
- **What permissions does it need?** `s3:PutObject` on `incidents/*` in one bucket, `sns:Publish` on one topic, and writing its own logs. In the lab it runs as LabRole, which is far broader. See [least-privilege.md](least-privilege.md).
- **Who is allowed to start it?** Only EventBridge, through the function's resource-based policy, limited to my rules' ARNs. That is separate from the execution role.
- **What happens if S3 fails?** The error stops the run before the email, so Lambda retries the event (up to 2 more times). The original one-line alert still arrives from its own rule.
- **Why `.get()` instead of `[]`?** `event["x"]` crashes if `x` is missing; `event.get("x", default)` returns the default.
- **How did you test it?** 18 offline tests with fake S3 and SNS clients, 5 tests of the event patterns, then synthetic console tests and real end-to-end tests in AWS (see the [test plan](test-plan.md)).
