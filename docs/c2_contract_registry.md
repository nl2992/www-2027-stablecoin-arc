# C2 — Historical contract discovery registry

The registry at `reports/c2/contract_registry.json` separates an address documented by a protocol source from deployment/state verification at the March 10–12, 2023 target blocks. All candidates are `SOURCE_DOCUMENTED` and `UNVERIFIED_AT_TARGET_BLOCK`; none is labeled live verified. `configs/c2_contracts.yaml` is the human-maintained counterpart.

| Candidate | Address | C2 evidence | Remaining verification |
|---|---|---|---|
| Curve Ethereum 3pool swap | `0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7` | Curve deployment-address documentation | Historical code, coin order, decimals, A, fee, balances and block-level contract identity |
| Curve 3pool LP token | `0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490` | Curve deployment-address documentation | Historical code and relationship to the pool at target blocks |
| Uniswap v3 Ethereum factory | `0x1F98431c8aD98523631AE4a59f267346ea31F984` | Official Uniswap deployments documentation | Resolve relevant pools via historical factory `getPool`; verify creation block, bytecode, token order, fee tier and target-block state |
| Maker legacy USDC PSM candidate | `0x89B78CfA322F6C5dE0aBcEecab66Aee45393cC5A` | `dss-psm` repository contract list | Verify active March 2023 deployment, dependencies, `tin`/`tout`, debt ceiling, available inventory and governance execution blocks |

Addresses and present-day documentation do not establish historical state. Maker parameter proposals are not parameter changes until the corresponding on-chain executive action executes. Uniswap pools are unique instances; do not substitute a currently popular pool for one verified at the target date. The research boundary is registry discovery only: no historical swap simulation or capacity estimate in C2.

Sources reviewed 2026-10-11: [Curve deployment addresses](https://curve.readthedocs.io/ref-addresses.html), [Uniswap v3 official deployments and factory resolution](https://developers.uniswap.org/docs/protocols/v3/deployments), and [Maker `dss-psm` contract reference](https://github.com/sky-ecosystem/dss-psm). The Maker source repository is protocol-maintained but the contract's historical deployment/state is explicitly not verified here.

## Multi-event extension (2026-10-11)

Each entry in `reports/c2/contract_registry.json` now lists the registry events it relates to (`event_ids`), and a test checks that every linked event exists. New candidates:

| Candidate | Address | Evidence | Linked event |
|---|---|---|---|
| Curve wormhole-UST/3CRV metapool | `0xCEAF7747579696A2F0bb206a14210e3c9e6fB269` | Jump Crypto's UST depeg analysis names it, verbatim, as the pool studied for 2022-05-07..09 | E2022-05-UST-COLLAPSE |
| Curve legacy UST metapool | `0x890f4e345B1dAED0367A877a1612f86A1f86985f` | Curve address docs (`StableSwapUST.vy`) | E2022-05-UST-COLLAPSE (relevance unverified) |
| Curve BUSD pool | `0x79a8C46DeA5aDa233ABaFFD40F3A0A2B1e5A4F27` | Curve address docs | P2023-02-BUSD-PAXOS-HALT |
| Curve USDe/USDC pool | `0x02950460E2b9529D0E00284A5fA2d7bDF3fA4d72` | **Aggregator listing only**, so labelled `UNVERIFIED`; a test enforces this | E2025-10-USDE-BINANCE |

The 3pool entries now also link to the June 2023 USDT negative case. None of these entries is verified at a target block. Using any of them for capacity requires an authorized archive endpoint, followed by block-pinned checks of code, coin order, decimals, A, fee and balances.
