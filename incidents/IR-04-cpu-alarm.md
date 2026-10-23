# IR-04 — High CPU on the lab server

| Field | Entry |
|---|---|
| Incident ID | IR-04 (controlled test TEST-04) |
| Date | 2026-10-22 (CDT) / 2026-10-22–23 (UTC) |
| Severity | Low: planned, bounded load on a lab server |
| Status | ✅ Closed — **PASS** |
| Affected resource | `cis260-target` (`i-085a300c3d2a60c75`) |
| Detection source | CloudWatch alarm `cis260-cpu-high` (CPUUtilization average > 10 % for one 5-minute period) → SNS `cis260-security-alerts` |
| Analyst | Jeremiah Banks |

## Summary
A single CPU busy loop, limited to 7 minutes, ran on the target from 23:56:51 to 00:03:51 UTC. The alarm went to **ALARM at 23:58:15** (the 5-minute average reached 16.4 %) and the SNS email action ran at the same second. CPU peaked at about 50 % (one of the two vCPUs fully busy). After the load stopped, the alarm returned to **OK at 00:05:15**, and the server stayed healthy.

## Timeline (UTC)
| Time | Event | Source |
|---|---|---|
| 23:55 | Baseline: alarm OK, CPU near 0 %; action = notify `cis260-security-alerts` | `2026-10-22_45_test4-alarm-ok-before.jpg`, `_46_test4-alarm-action.jpg` |
| 23:56:51 | Load started: `timeout 420 sh -c 'while :; do :; done'` (load average 0.00) | `2026-10-22_47_test4-load-started.jpg` |
| 23:58:15 | **ALARM**: "1 out of the last 1 datapoints [16.39 (23:53)] was greater than the threshold (10.0)" | `2026-10-22_53_test4-alarm-state-and-datapoints.jpg` |
| 23:58:15 | Alarm action: "Successfully executed action … cis260-security-alerts" (email sent) | `2026-10-22_59_test4-alarm-history-recovered.jpg` |
| 00:03:51 | Load stopped by itself (load average 1.17) | `2026-10-22_55_test4-load-finished.jpg` |
| 00:05:15 | **OK**: alarm recovered | `2026-10-22_59_test4-alarm-history-recovered.jpg` |
| 00:08:31 | Health check: Session Manager works, load average 0.02 | `2026-10-22_60_test4-healthy.jpg` |

| 5-minute period starting | Average CPU | Maximum |
|---|---|---|
| 23:50 | 0.31 % | 0.53 % |
| 23:55 | **29.78 %** | **49.90 %** |
| 00:00 | 10.52 % (partial when read) | 11.54 % |

## Investigation — the five questions
| Question | Answer | Where it came from |
|---|---|---|
| What happened? | CPU on `cis260-target` rose above 10 % | CloudWatch metric `AWS/EC2 CPUUtilization` |
| Who did it? | My Session Manager session ran the test loop | Session Manager (ssm-user) |
| When? | 23:56:51–00:03:51 UTC | `date -u` in the session |
| From where? | Inside the server (a process), not the network | `uptime` load average, CPU metric |
| Expected or unexpected? | Expected — planned test TEST-04 | Test plan |

## Correction and recovery
- Correction: none needed. The loop was bounded with `timeout 420` and stopped on its own.
- Verification: alarm back to OK at 00:05:15 UTC; Session Manager responsive; load average 0.02.

## Lessons learned
- **The alarm was faster than I planned for.** With basic monitoring I expected 5–10 minutes. CloudWatch evaluated a 5-minute window that already held about 1½ minutes of load and fired 84 seconds after the load started, because the average crossed 10 %.
- **One busy loop shows as about 50 %** on a 2-vCPU t3.micro, which is why the threshold had to be low for a controlled test. In production a threshold would be tuned to the workload.
- **CPU credits were Standard,** so the test couldn't run up surplus-credit charges.
- **Recovery has to be checked, not assumed.** The OK state plus a working session prove the server came back.

## Evidence
`2026-10-22_45` through `_47`, `_53` through `_55`, `_59`, `_60` (see the [evidence manifest](../evidence/manifest.md)).
