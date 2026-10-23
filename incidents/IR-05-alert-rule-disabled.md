# IR-05 — Security-group alert rule switched off and back on

| Field | Entry |
|---|---|
| Incident ID | IR-05 (controlled test TEST-07, the security improvement) |
| Date | 2026-10-22 (CDT) / 2026-10-23 (UTC) |
| Severity | Medium in a real environment (turning off alerts is a defense-evasion step); Low here because it was planned and lasted 2 seconds |
| Status | ✅ Closed — **PASS** |
| Affected resource | EventBridge rule `cis260-sg-changes` |
| Detection source | New rule `cis260-monitoring-integrity` → Lambda `cis260-incident-processor` → S3 incident record + SNS email |
| Analyst | Jeremiah Banks |

## Summary
Before the improvement, switching off the security-group alert rule left **no alert and no record**. The action appeared only in CloudTrail. After I added `cis260-monitoring-integrity`, the same action produced an incident record and an email for both the disable and the re-enable, matched to CloudTrail by event ID. The watched rule ended Enabled.

## Timeline (UTC, 2026-10-23)
| Time | Event | Incident record | Source |
|---|---|---|---|
| 00:19:09 | **Before:** `DisableRule cis260-sg-changes` (CloudTrail `dc9ef349-28d0-4a70-ba52-dc746137f704`) | none | `2026-10-22_65_test7-before-disable-enable.jpg`, `_70_evidence-correlation.jpg` |
| 00:19:11 | **Before:** `EnableRule` (CloudTrail `9a909f72-035d-49c6-a0b6-859b8ee92267`) | none | same |
| 00:19:38 | **Change:** created `cis260-monitoring-integrity` (DisableRule/EnableRule on `cis260-sg-changes` → Lambda) | — | `2026-10-22_66_test7-integrity-rule-created.jpg` |
| 00:20:05 | **After:** `DisableRule` (CloudTrail `83a3c184-4ea3-409b-b6aa-48b3772e4163`) | `DisableRule-83a3c184-….json` saved 00:20:19, email sent | `2026-10-22_67_test7-after-records.jpg` |
| 00:20:07 | **After:** `EnableRule` (CloudTrail `62606ba9-4236-43e4-b1fe-0e482b681b52`) | `EnableRule-62606ba9-….json` saved 00:20:27, email sent | same |
| 00:25:10 | Final state: all six cis260 rules Enabled | — | `2026-10-22_71_final-security-state.jpg` |

## Investigation — the five questions
| Question | Answer | Where it came from |
|---|---|---|
| What happened? | The security-group alert rule was disabled, then re-enabled | CloudTrail `DisableRule` / `EnableRule`, `requestParameters.name` |
| Who did it? | `user4744416=Jeremiah_Banks` (my lab session) | Incident email / CloudTrail `userIdentity` |
| When? | 00:20:05 and 00:20:07 UTC (after phase) | `eventTime` |
| From where? | My CloudShell session, where I ran the AWS CLI. The saved record keeps the exact `sourceIPAddress` and `userAgent` | Saved incident record (full CloudTrail event) |
| Expected or unexpected? | Expected — planned test TEST-07 | Test plan |

## Correction and recovery
- Correction: re-enabled `cis260-sg-changes` within 2 seconds each time.
- Verification: rule state ENABLED (`describe-rule`) and in the final state check.

## Lessons learned
- **Monitoring must watch itself.** Without the integrity rule, a disable is only visible to someone who goes looking in CloudTrail.
- **Separate rules matter.** The integrity rule is a different rule from the one it watches, so disabling the watched rule can't silence it. While `cis260-sg-changes` was briefly off, `cis260-lambda-sg` would still have recorded security-group changes.
- **Limits remain.** It watches one rule and two actions. `DeleteRule`, `RemoveTargets`, and CloudTrail `StopLogging` are next.

## Evidence
`2026-10-22_65` through `_67`, `_70`, `_71` (see the [evidence manifest](../evidence/manifest.md)).
