# Research decision register

Each decision lists its evidence and who made it. Scope decisions need independent reviewer approval.

| # | Date (UTC) | Decision | Evidence | Status |
|---|---|---|---|---|
| D1 | 2026-10-11 | Paid data is declined | User instruction | In force |
| D2 | 2026-10-11 | Free Binance, Binance.US and Bitstamp klines authorized | User instruction; `reports/events/acquisition_manifest.json` | Executed |
| D3 | 2026-10-11 | Amendments A1–A4 govern the analysis (A2 made after seeing data) | `docs/PRE_ANALYSIS_AMENDMENTS.md` | In force |
| D4 | 2026-10-11 | Reviewer: on-chain-only paper permissible with narrower claims; CEX L2 investigation kept separate | Reviewer C2C, decision 3 | Recorded. **Scope not changed** |
| D5 | 2026-10-11 | Reviewer: bounded free archive-RPC tests permitted after terms check; stop if historical state is inadequate | Reviewer C2C, decision 2; `reports/c2/archive_probe.json` | **Stopped: no free, keyless, terms-compatible archive endpoint found** |
| D6 | 2026-10-11 | Reviewer: UST A4 experiment permitted after precondition checks | Reviewer C2C, decision 4; `reports/events/E2022-05-UST-COLLAPSE_a4_splice.json` | Executed. Negative: recovery window uncovered |
| D7 | 2026-10-11 | Reviewer: free Tardis first-of-month samples for normal-market comparison | Reviewer C2C, decision 5; `reports/c1/normal_market_depth.json` | Executed (3 files) |
| D8 | 2026-10-11 | User approved A5 (UST continuation via UST/BUSD); UST is classified EXPLORATORY (post-hoc eligibility) | User instruction; `docs/PRE_ANALYSIS_AMENDMENTS.md` A5; `configs/plan_freeze.json` (`exploratory_post_hoc`) | Executed. UST ACCEPTED as an episode, excluded from confirmatory counts. **User confirmed 2026-10-11: keep UST exploratory.** |

## Scope: CEX–DEX restoration capacity vs on-chain-only fallback

**CEX–DEX scope (primary hypothesis, unchanged):**
- **Requires** crisis-day CEX L2 and historical DEX state.
- **Status:** CEX crisis-day L2 is blocked (paid only, declined). DEX state is blocked: no free, keyless archive endpoint permits historical `eth_call`.
- **Available:** candle-level multi-event evidence, plus normal-market CEX depth on 3 first-of-month days.

**On-chain-only fallback (permitted by the reviewer, not adopted):**
- **Requires** historical pool state at event blocks.
- **Status:** **not currently feasible within the constraints.**
  - The NodeFlare public tier returns `state at block #14000001 is pruned`.
  - rpcfree.com's free tier excludes archive data.
  - PublicNode's terms prohibit automated data extraction.
  - Cloudflare documents archive methods but no keyless public gateway.
- **Narrow path that would unblock it:** the user creates a free provider key and sets `WWW_ETH_RPC_URL` locally, without sharing it in chat. This requires the user to authorize account creation.
- **Assessment of an on-chain-only paper** (originality, strength, limits) is deferred until state can actually be read.

**Claims allowed now:** descriptive, candle-level, multi-event evidence on peg dislocation versus within-venue wedges, plus normal-market CEX depth levels. **Not allowed:** any restoration-capacity number, and any CEX–DEX capacity claim.
