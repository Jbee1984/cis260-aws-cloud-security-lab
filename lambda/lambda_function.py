# cis260-incident-processor
# EventBridge runs this function when one of my lab's watched API calls is recorded by CloudTrail.
# It does three things: (1) checks that the event belongs to my lab, (2) saves the full event to S3
# as an incident record, and (3) emails a short readable alert through SNS.
# It never changes, stops, or deletes anything. Deciding what to do is my job as the analyst.

import json
import os

import boto3

s3 = boto3.client("s3")
sns = boto3.client("sns")

# Each watched API call, and the environment variable that names the one resource it must be about.
WATCHED = {
    "AuthorizeSecurityGroupIngress": "TARGET_GROUP_ID",
    "RevokeSecurityGroupIngress": "TARGET_GROUP_ID",
    "StopInstances": "TARGET_INSTANCE_ID",
    "StartInstances": "TARGET_INSTANCE_ID",
    "DisableRule": "MONITORED_RULE_NAME",
    "EnableRule": "MONITORED_RULE_NAME",
    "PutBucketVersioning": "TEST_BUCKET_NAME",
}


def resource_of(name, params):
    """Return the ID of the resource the API call was about (each service stores it in a different field)."""
    if name in ("StopInstances", "StartInstances"):
        items = params.get("instancesSet", {}).get("items", [])
        return items[0].get("instanceId") if items else None
    if name in ("DisableRule", "EnableRule"):
        return params.get("name")
    if name == "PutBucketVersioning":
        return params.get("bucketName")
    return params.get("groupId")


def lambda_handler(event, context):
    detail = event.get("detail", {})
    name = detail.get("eventName")

    # 1. Scope check: my account, my Region, a watched API call, and my resource. Anything else is ignored.
    if event.get("account") != os.environ["LAB_ACCOUNT_ID"]:
        return {"status": "ignored", "reason": "account"}
    if event.get("region") != os.environ["AWS_REGION"]:
        return {"status": "ignored", "reason": "region"}
    if name not in WATCHED:
        return {"status": "ignored", "reason": "event"}
    resource = resource_of(name, detail.get("requestParameters") or {})
    if resource is None or resource != os.environ.get(WATCHED[name]):
        return {"status": "ignored", "reason": "resource"}

    # 2. Evidence: save the complete event, unchanged, as a private JSON file named after its CloudTrail event ID.
    event_id = detail.get("eventID", "no-event-id")
    key = f"incidents/{detail.get('eventTime', 'unknown')[:10]}/{name}-{event_id}.json"
    s3.put_object(
        Bucket=os.environ["INCIDENT_BUCKET"],
        Key=key,
        Body=json.dumps(event, indent=2).encode("utf-8"),
        ContentType="application/json",
    )

    # 3. Alert: one readable email. A denied API call is reported as FAILED, not as a change that happened.
    outcome = f"FAILED ({detail['errorCode']})" if detail.get("errorCode") else "succeeded"
    message = "\n".join([
        f"CIS260 INCIDENT: {name} {outcome}",
        f"Resource: {resource}",
        f"Who: {detail.get('userIdentity', {}).get('arn', 'unknown')}",
        f"When (UTC): {detail.get('eventTime', 'unknown')}",
        f"From IP: {detail.get('sourceIPAddress', 'unknown')}",
        f"CloudTrail event ID: {event_id}",
        f"Evidence: s3://{os.environ['INCIDENT_BUCKET']}/{key}",
    ])
    sns.publish(TopicArn=os.environ["SNS_TOPIC_ARN"], Subject=f"CIS260 incident: {name}", Message=message)
    return {"status": "recorded", "key": key}
