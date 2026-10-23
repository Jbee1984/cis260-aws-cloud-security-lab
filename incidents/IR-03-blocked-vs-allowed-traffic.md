# IR-03 — Connection attempts to a closed port on the lab server

| Field | Entry |
|---|---|
| Incident ID | IR-03 (controlled test TEST-03) |
| Date | 2026-10-22 (CDT) / 2026-10-22–23 (UTC) |
| Severity | Low: planned test between two lab servers inside the private VPC range; nothing was opened to the internet |
| Status | ✅ Closed — **PASS** |
| Affected resource | `cis260-target` (10.26.1.235, interface `eni-0e9467ff27cb756eb`), security group `cis260-target-sg` |
| Detection source | VPC Flow Log `cis260-subnet-flowlog` (REJECT/ACCEPT records in S3); the rule change also alerted through `cis260-sg-changes` |
| Analyst | Jeremiah Banks |

## Summary
A temporary client server (10.26.1.241) tried to reach a test web listener on the target over TCP 8080. With zero inbound rules, the request timed out and Flow Logs recorded **REJECT** on the target's interface. A narrow rule allowing 8080 only from the client's security group let one request through: **HTTP 200**, and an **ACCEPT** record on the target's interface. Removing the rule blocked the port again (**REJECT**). The client and its security group were deleted, and the listener was stopped.

## Timeline (UTC)
| Time | Event | Source |
|---|---|---|
| 23:52:18 | Created `cis260-test-client-sg` (no inbound; outbound 443 and 8080 to `cis260-target-sg` only) | `2026-10-22_41_test3-client-sg.jpg` |
| 23:53:05 | Launched `cis260-test-client` (`i-0a86e4bcc5db5a721`, 10.26.1.241) | `2026-10-22_43_test3-client-running.jpg` |
| 23:53:52 | Test listener started on 10.26.1.235:8080 (stops itself after 40 minutes) | `2026-10-22_42_test3-target-listener.jpg` |
| 23:54:51 | **Blocked:** curl from the client timed out after 5 s (exit code 28) | `2026-10-22_44_test3-blocked-timeout.jpg` |
| 23:54:26 / 23:54:53 | Flow Logs: **REJECT** on the target interface (2 + 3 packets) | `2026-10-22_48_test3-reject-records.jpg` |
| 00:01:24 | Added rule `sgr-0b5b017731738b433`: TCP 8080 from `cis260-test-client-sg` only. `cis260-sg-changes` alert email sent | `2026-10-22_49_test3-narrow-rule-added.jpg` |
| 00:01:44 | **Allowed:** HTTP 200 "CIS260 TEST-03: hello from cis260-target" (exit code 0) | `2026-10-22_50_test3-allowed-200.jpg` |
| 00:01:54 | Flow Logs: **ACCEPT** on the target interface (5 packets) | `2026-10-22_57_test3-all-flow-records.jpg` |
| 00:02:18 | **Correction:** rule removed; 0 inbound rules again; Revoke alert email sent | `2026-10-22_51_test3-rule-removed.jpg` |
| 00:02:44 | **Retest:** curl timed out again (exit code 28) | `2026-10-22_52_test3-retest-blocked.jpg` |
| 00:02:29 | Flow Logs: **REJECT** on the target interface (5 packets) | `2026-10-22_57_test3-all-flow-records.jpg` |
| ~00:04:20 | Listener stopped (Ctrl+C); its log shows **one** request served, the allowed one; port 8080 no longer listening | `2026-10-22_56_test3-listener-stopped.jpg` |
| 00:06:11 | Client terminated; its security group deleted | `2026-10-22_58_test3-cleanup.jpg` |

Flow-log `start` times mark the first packet seen in each 1-minute aggregation window and can be up to 60 seconds off the real packet time, so they don't line up exactly with the curl times.

## Investigation — the five questions
| Question | Answer | Where it came from |
|---|---|---|
| What happened? | TCP 8080 connection attempts from 10.26.1.241 to 10.26.1.235 | Flow Log records (srcaddr, dstaddr, dstport) |
| Who did it? | The temporary test client; the rule changes were made by my lab session | Flow Logs (IP → instance); CloudTrail (rule changes) |
| When? | 23:54 UTC (blocked), 00:01 (allowed), 00:02 (blocked again) | Flow Logs `start`, curl output |
| From where? | Inside the VPC (10.26.1.0/24), not the internet | Flow Logs `srcaddr` |
| Expected or unexpected? | Expected — planned test TEST-03 | Test plan |

## Analysis note: why the blocked attempt also shows an ACCEPT
The flow log is attached to the **subnet**, so it records both servers' network interfaces:
- The **client's** interface (`eni-0e499ec56c13f60e9`) shows ACCEPT. Its own outbound rule allowed the packets to leave.
- The **target's** interface (`eni-0e9467ff27cb756eb`) shows REJECT. Its inbound rules dropped them.

Security groups are checked separately at each interface. To judge whether traffic reached the server, I filter on the **target's** interface ID. Reading the client's ACCEPT alone would wrongly suggest the connection succeeded.

## Correction and recovery
- Correction: removed the temporary 8080 rule at 00:02:18 UTC.
- Verification: inbound rule count 0; retest timed out; REJECT recorded again; listener stopped; client and its security group deleted.

## Lessons learned
- **A timeout alone doesn't prove which control blocked traffic.** The REJECT on the target's interface does.
- **Narrow beats open.** Allowing one source security group gave exactly one working connection. Nothing else, and nothing from the internet.
- **Evidence has delays.** Flow-log files reached S3 about 5 minutes after the traffic, in 5-minute files. A rule that is "Active" isn't proof until a matching record is found.

## Evidence
`2026-10-22_41` through `_44`, `_48` through `_52`, and `_56` through `_58` (see the [evidence manifest](../evidence/manifest.md)).
