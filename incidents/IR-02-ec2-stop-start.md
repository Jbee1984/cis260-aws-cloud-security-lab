# IR-02 — Lab server stopped (outage) and restored

| Field | Entry |
|---|---|
| Incident ID | IR-02 (controlled test TEST-02) |
| Date | 2026-10-02 |
| Severity | Low — planned outage during a test window |
| Status | ✅ Closed — **PASS** |
| Affected resource | EC2 instance `cis260-target` |
| Detection source | EventBridge rule `cis260-ec2-api-changes` (CloudTrail `StopInstances` / `StartInstances`) → SNS email |
| Analyst | Jeremiah Banks |

## Summary
At 21:52:34 UTC a `StopInstances` request stopped `cis260-target`. The alert email arrived the same minute and named my lab session as the caller. I started the instance at 21:54:30 UTC, and Session Manager reconnected at 21:58:10 UTC, about 5½ minutes from the stop request to working access.

## Timeline (UTC)
| Time | Event | Source |
|---|---|---|
| — | Baseline: running (the stop request succeeded); no separate baseline screenshot | — |
| 21:52:34 | Stop requested — CloudTrail `StopInstances` (event ID d6a1c3df-48be-4eae-9fdb-13fe34aaca26), my identity | inside the alert email |
| 21:52 | **Alert email received** (4:52 PM CDT) — `StopInstances` on `cis260-target`, running → stopping | `2026-10-02_30_alert-email-stopinstances.png` |
| 21:54 | **Second alert email** (4:54 PM CDT) — `StartInstances` | `2026-10-02_31_alert-email-startinstances.png` |
| 21:54 | Observed: state Stopped, public IPv4 released | `2026-10-02_18_test2-instance-stopped.png` (the `StopInstances` record itself is inside the alert email) |
| 21:54:30 | Start requested (correction) — CloudTrail `StartInstances`, my identity, resource `cis260-target` | `2026-10-02_26_cloudtrail-startinstances.png` |
| 21:56 | Observed: state Running, status checks initializing, new public IPv4 | `2026-10-02_19_test2-instance-running.png` |
| 21:57:56 | CloudTrail `StartSession` (ssm.amazonaws.com) recorded for my identity — the reconnect is audited | `2026-10-02_25_cloudtrail-startsession.png` |
| 21:58 | Session Manager reconnected (`whoami` → `ssm-user`); private address unchanged, public address changed | `2026-10-02_20_test2-session-manager-reconnected.png` |

**Outage timing (UTC):** stop requested 21:52:34 → start requested 21:54:30 (1 min 56 s) → Running observed by 21:56 → usable Session Manager shell at 21:58:10 (about 5 min 36 s after the stop request). "Running" is not the same as recovered; the session check is what proves access came back.

## Investigation — the five questions
| Question | Answer | Where it came from |
|---|---|---|
| What happened? | `cis260-target` went from running to stopped | Alert email / CloudTrail `StopInstances` |
| Who did it? | My lab identity (`voclabs` role session for Jeremiah_Banks) | CloudTrail `StopInstances` → `userIdentity` |
| When? | 2026-10-02 21:52:34 UTC (stop request); alert email the same minute | email / CloudTrail `eventTime` |
| Expected or unexpected? | Expected — planned test TEST-02 | Test plan |
| What would make it suspicious? | A stop by an identity I don't recognize, outside a planned window, or followed by other changes (e.g., a new inbound rule) | Analysis |

## Correction and recovery
- Correction: start requested at 21:54:30 UTC (CloudTrail `StartInstances`); Running by 21:56.
- Verification: Session Manager reconnected at 21:58:10 UTC (`whoami` → `ssm-user`).
- Observation: the auto-assigned public IP changes after a stop/start. That doesn't matter here because nothing connects *in* to the instance.

## Lessons learned
- **The alert answered "who" immediately.** Because the rule uses the CloudTrail API event, the email's `userIdentity` named the caller. EC2's own state-change event would only have said the instance stopped.
- **A successful API call is not recovery.** `StartInstances` succeeded at 21:54:30, but access only came back at 21:58:10, once status checks ran and the SSM agent reconnected. Recovery has to be proven with a real session.
- **The public IP changed and it didn't matter,** because nothing connects in to the instance. The private IP stayed the same.
- **Learner Lab's own 4-hour shutdown is also a `StopInstances` call** (ISSUE-02). An unplanned stop like that should also alert, and CloudTrail shows which identity made it. In a real environment, a stop outside a maintenance window by an unknown identity would be escalated.

## Evidence
| File | What it shows |
|---|---|
| `2026-10-02_15_eventbridge-ec2-rule.png`, `2026-10-02_16_eventbridge-sns-target.png` | EventBridge rule and its SNS target |
| `2026-10-02_18_test2-instance-stopped.png` | Instance stopped |
| `2026-10-02_30_alert-email-stopinstances.png` | Alert email (`StopInstances`) |
| (inside the alert email) | CloudTrail `StopInstances` record |
| `2026-10-02_31_alert-email-startinstances.png` | Alert email (`StartInstances`) |
| `2026-10-02_19_test2-instance-running.png` | Instance running again |
| `2026-10-02_20_test2-session-manager-reconnected.png` | Session Manager reconnected after the restart |
| `2026-10-02_25_cloudtrail-startsession.png` | CloudTrail `StartSession` record for that reconnect |
| `2026-10-02_26_cloudtrail-startinstances.png` | CloudTrail `StartInstances` record (who restarted the server, when) |
