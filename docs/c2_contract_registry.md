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
