# C2 — Ethereum historical data and archive access

**Checked:** 2026-10-11. No cloud project, paid service, provider account, credential, or live RPC request was used.

| Source | What primary documentation supports | Cost/access note | What it does not yet establish |
|---|---|---|---|
| Google Cloud Blockchain Analytics | Indexed Ethereum blocks, transactions, logs and traces queryable through BigQuery | Blockchain Analytics uses BigQuery pricing; first 1 TiB of on-demand query processing per month is documented free. Google Cloud project/account and billing configuration were not created. | Arbitrary historical `eth_call`/storage state or exact AMM quotes |
| Alchemy | Current pricing documentation lists Full Archive Data on its free tier, with 30M base compute units and 300 CU/s | Requires signup and API key; no credentials or account used. A provider may impose quota/rate limits. | Successful access for this study's selected blocks, calls, and required throughput |
| Cloudflare Ethereum Gateway | Documentation says its archive nodes serve historical `eth_getCode`, `eth_getStorageAt`, `eth_call`, and related methods | Endpoint setup and acceptable unauthenticated-use terms were not established. No endpoint call made. | Access under this project's authorized account/terms, rate limits, and reproducibility |
| Local archive node | Full control over state and reproducibility | Hardware, synchronization, storage and operations costs not estimated or incurred | Feasibility within the submission timeline |

BigQuery appears useful for event chronology and contract logs; it must not be represented as a replacement for archive-state calls. An Alchemy free tier is the most explicit documented possibility for archive reads among the reviewed hosted options, but it is account/key gated, so it is not anonymous/free-to-use-without-setup. Cloudflare documents the needed archive methods, but terms and endpoint conditions remain to be resolved. The C2 harness accepts a local `WWW_ETH_RPC_URL` only when a future user-authorized read-only probe is run; it redacts endpoints from errors and does not support transaction-submission methods. No actual provider is selected or live-verified.

## Read-only probe harness

The `www-c2-rpc-probe` command checks chain ID, the requested historical block number/hash, and contract bytecode at that block. An optional ABI-encoded `eth_call` payload can be provided. Set `WWW_ETH_RPC_URL` in the local environment; do not put endpoint URLs or API keys in tracked files or shell command arguments. Only HTTPS and explicit read-only methods are supported. The harness is deliberately not run in C2 because no suitable, authorized endpoint is configured.

## Sources

- [Google Blockchain Analytics overview](https://docs.cloud.google.com/blockchain-analytics/docs/overview), [dataset query example](https://docs.cloud.google.com/blockchain-analytics/docs/example-ethereum), and [pricing](https://cloud.google.com/blockchain-analytics/pricing), reviewed 2026-10-11.
- [Alchemy pricing plans](https://www.alchemy.com/docs/reference/pricing-plans) and [Ethereum `eth_call` API](https://www.alchemy.com/docs/chains/ethereum/ethereum-api-endpoints/eth-call), reviewed 2026-10-11.
- [Cloudflare Ethereum Gateway node types and historical state methods](https://developers.cloudflare.com/web3/ethereum-gateway/concepts/node-types/), reviewed 2026-10-11.
- [Ethereum JSON-RPC methods](https://ethereum.org/developers/docs/apis/json-rpc/).
