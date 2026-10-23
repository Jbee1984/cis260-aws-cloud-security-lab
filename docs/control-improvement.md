# Security improvement — alert when an alert rule is switched off

**Status:** ✅ **Deployed and tested 2026-10-22: PASS.** Rule `cis260-monitoring-integrity` was created at 00:19:38 UTC. Before/after evidence is below and in [IR-05](../incidents/IR-05-alert-rule-disabled.md).

## The gap (before)

My alerts depend on EventBridge rules. If someone **disables** `cis260-sg-changes`, every later security-group change happens **silently**: no email at all.

Disabling a rule is itself an API call (`DisableRule` on events.amazonaws.com), so CloudTrail records it. But nothing **tells** anyone. An attacker who wants to open a port quietly would switch the alert off first.

This is a well-known attacker step: **defense evasion**, meaning impairing or disabling security tools.

## The change (after)

| Piece | Setting |
|---|---|
| New rule | `cis260-monitoring-integrity`, default event bus, us-east-1 |
| Pattern | `DisableRule` or `EnableRule` calls on events.amazonaws.com whose `requestParameters.name` is `cis260-sg-changes` |
| Target | Lambda `cis260-incident-processor`, input = Matched events |
| Result | An incident record in S3 and an email: "CIS260 INCIDENT: DisableRule succeeded … Resource: cis260-sg-changes …" |

Because the new rule is **separate** from the rule it watches, switching off `cis260-sg-changes` can't also switch off the alert about it.

## Test (TEST-07)

| Step | Action | Evidence (screenshot names) |
|---|---|---|
| 1. Before | Confirm `cis260-sg-changes` is Enabled and `cis260-monitoring-integrity` doesn't exist yet | `H1_before_rule-enabled.png` |
| 2. Before | Disable `cis260-sg-changes`, then **immediately** enable it again. Record both UTC times. | `H1_before_disable-enable.png` |
| 3. Before | CloudTrail Event history shows `DisableRule` and `EnableRule`. No dedicated alert exists for them (an empty inbox alone doesn't prove that, but the rule list does). | `H1_before_cloudtrail.png` |
| 4. Change | Create `cis260-monitoring-integrity` (pattern above, target the Lambda), Enabled | `H2_integrity-rule.png` |
| 5. After | Disable `cis260-sg-changes` once, then enable it again | `H3_after_disable-enable.png` |
| 6. After | Two incident emails (DisableRule, EnableRule); two records under `incidents/` in `cis260-incident-records-jbanks`; event IDs match CloudTrail | `H3_after_emails.png`, `H3_after_records.png` |
| 7. Final state | `cis260-sg-changes` is Enabled again. Rule list shows every rule's final state. | `H4_final-rule-states.png` |

**Pass:** before, the disable produced no alert. After, the same action produced an email and a record within a few minutes, and the event IDs match CloudTrail. The watched rule is enabled again at the end.

| Field | Result |
|---|---|
| Date run | 2026-10-22 (7:19–7:20 PM CDT) |
| Before: DisableRule / EnableRule (UTC) | 00:19:09 / 00:19:11 (CloudTrail `dc9ef349…` / `9a909f72…`): **no incident record, no alert** |
| After: DisableRule / EnableRule (UTC) | 00:20:05 / 00:20:07 (CloudTrail `83a3c184-4ea3-409b-b6aa-48b3772e4163` / `62606ba9-4236-43e4-b1fe-0e482b681b52`) |
| After: incident records saved | 00:20:19 and 00:20:27 UTC (same event IDs), each with an email |
| Final state | `cis260-sg-changes` ENABLED; all six cis260 rules enabled |
| Result | ✅ **PASS** |

The screenshots used plain CloudShell output instead of the console names planned above: `2026-10-22_65_test7-before-disable-enable.jpg`, `_66_test7-integrity-rule-created.jpg`, `_67_test7-after-records.jpg`, `_70_evidence-correlation.jpg`, `_71_final-security-state.jpg`.

## Rollback

Disable or delete `cis260-monitoring-integrity`. Nothing else changes.

## What it does not cover (residual risk)

- It watches **one** rule. `cis260-ec2-api-changes` could be added to the same pattern's `name` list.
- It doesn't watch **`DeleteRule`** or **`RemoveTargets`**, which also silence an alert. Next step: add them.
- It doesn't watch CloudTrail itself (**`StopLogging`**, `DeleteTrail`). Next step, because without CloudTrail none of the API-based alerts work.
- Nothing protects the integrity rule itself. Someone with enough permission could disable it first. In a company, these rules would be deployed centrally (for example, by AWS Organizations) so one account owner can't turn them off.
