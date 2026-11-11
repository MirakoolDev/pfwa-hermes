# PFWA for Hermes Agent

**Randomness Hermes can't fake.** Ask an LLM to "pick a random winner" and it makes one up: it can't be checked, and it isn't random. `pfwa_random` draws from the drand beacon (the League of Entropy) using a round chosen *before it existed*, and hands back the result with a proof anyone can recheck. Use it for giveaways, raffles, draws, team picks, dice and tie-breaks. It's the same beacon PFWA's HoodRand verifies onchain on Robinhood Chain.

**Plus prediction markets on Robinhood Chain**, from inside Hermes. Ask Hermes what markets are open, what an outcome costs right now, what your wallet holds and what you can claim, then get a ready-to-sign transaction for your own wallet.

[PFWA](https://www.pfwa.fun) runs permissionless prediction markets on Robinhood Chain (chain id 4663): token prices and market caps, tokenized stocks, football matches and DeFi metrics. Every outcome is its own onchain token priced by a bonding curve, and markets resolve automatically from public data.

## Tools

| Tool | What it does |
|---|---|
| `pfwa_random` | A provably fair number, coin flips, winner picks from a list, or a shuffle, with the drand round, signature and derivation so anyone can recheck it. |
| `pfwa_markets` | Open markets with each outcome's live chance, volume and trades. Optional `search`. |
| `pfwa_quote` | Reads the outcome contract onchain: tokens a given ETH amount buys after fees, average price, and what selling returns. |
| `pfwa_positions` | Every position a wallet holds in open markets, what each sells for now, and resolved markets it can claim. |
| `pfwa_build_tx` | An unsigned `buy`, `sell` or `claim` transaction with a slippage buffer, for the user's own wallet to sign. |
| `pfwa_results` | Recently resolved markets and their winning outcome. |
| `hoodrand_lookup` | Looks up a HoodRand request on Robinhood Chain: its round, number and transactions. |
| `sherwood_game` | Live round of Sherwood, PFWA's arena game on a Uniswap v4 hook: pot, time left, leaderboard, King of the Hill, burns. |

Things to ask:

- "Pick 3 winners from this list of 40 entries, and show me the proof."
- "Roll two dice." / "Flip a coin for who pays."
- "What PFWA markets are open on PONS?"
- "How many YES tokens does 0.001 ETH buy on market 79?"
- "What does 0x… hold on PFWA, and can it claim anything?"
- "Build me a 0.002 ETH buy of NO on market 80."

## Install

```bash
hermes plugins install pfwa
hermes plugins enable pfwa
```

Or from source: copy this folder to `~/.hermes/plugins/pfwa/` and run `hermes plugins enable pfwa`.

No API key and no configuration. Standard library only, no dependencies.

## Safety

- **No keys.** The plugin never asks for, stores or uses a private key. `pfwa_build_tx` returns an unsigned transaction (`to`, `value`, `data`, `chainId`); the user signs it in their own wallet, or trades on the market page instead.
- **Read-only otherwise.** Every other tool only reads: PFWA's public agent API (`https://www.pfwa.fun/api/agents`) and `eth_call` against Robinhood Chain's public RPC (`https://rpc.mainnet.chain.robinhood.com`).
- **Network calls** go only to PFWA, the Robinhood Chain RPC and drand's public relays (`api.drand.sh`, `api2.drand.sh`, `api3.drand.sh`). Wallet addresses you ask about are sent to the RPC as part of `balanceOf` calls.
- Prices move. A built buy asks for slightly fewer tokens than the quote (default 3%) and caps the ETH sent, so it fails rather than overpays.

## How the randomness is checked

1. When you ask, the plugin picks drand evmnet round `now + 2` (about 6 seconds in the future), so nobody, the plugin included, can know the result in advance.
2. When the round is published, `root = sha256(signature)`, and each value is `sha256(root || seed || i)`: reduced into your range, a coin, or picks from your list (Fisher-Yates for shuffles).
3. The answer includes the round, signature and seed. Fetch `https://api.drand.sh/v2/beacons/evmnet/rounds/<round>` and redo step 2 to get the same result. The round's signature verifies against drand's evmnet public key (chain hash `04f1e9062b8a81f848fded9c12306733282b2727ecced50032187751166ec8c3`), as HoodRand does onchain.

## Contracts

- Market factory: `0x7B38e940Cd649bc0C701c42eE1A6ceff75584afa` (Robinhood Chain, verified on Sourcify)
- Agent guide: https://www.pfwa.fun/agents.md

## License

MIT
