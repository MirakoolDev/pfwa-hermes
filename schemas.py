"""Tool schemas the model reads to decide when to call each PFWA tool."""

MARKETS = {
    "name": "pfwa_markets",
    "description": (
        "List open PFWA prediction markets on Robinhood Chain (token prices, market caps, "
        "stocks, football, DeFi metrics) with each outcome's live chance, volume and trade count. "
        "Use it to find markets on a topic before quoting or trading."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "search": {"type": "string", "description": "Optional words to filter questions, e.g. 'PONS' or 'Arsenal'."},
            "limit": {"type": "integer", "description": "Max markets to return (default 10, max 50)."},
        },
        "required": [],
    },
}

QUOTE = {
    "name": "pfwa_quote",
    "description": (
        "Read the live onchain price for one outcome: how many outcome tokens a given amount of ETH buys "
        "(after fees), the average price, and what selling a token amount would return. Reads the contract "
        "directly, no account needed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "token_address": {"type": "string", "description": "The outcome's token address from pfwa_markets."},
            "eth": {"type": "number", "description": "ETH to spend, e.g. 0.001."},
            "sell_tokens": {"type": "number", "description": "Optional: outcome tokens to price a sale of."},
        },
        "required": ["token_address"],
    },
}

POSITIONS = {
    "name": "pfwa_positions",
    "description": (
        "Show a wallet's positions in every open PFWA market and any resolved market it can claim winnings from, "
        "with what each position would sell for now. Read-only; takes a public address."
    ),
    "parameters": {
        "type": "object",
        "properties": {"wallet": {"type": "string", "description": "A 0x wallet address on Robinhood Chain."}},
        "required": ["wallet"],
    },
}

BUILD_TX = {
    "name": "pfwa_build_tx",
    "description": (
        "Build an unsigned transaction to buy, sell or claim on a PFWA outcome, with a slippage buffer, "
        "plus a link to the market page. Hermes never holds keys: the user signs it in their own wallet. "
        "Always quote first and show the user the numbers before building."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["buy", "sell", "claim"]},
            "token_address": {"type": "string", "description": "The outcome's token address."},
            "eth": {"type": "number", "description": "For buy: ETH to spend."},
            "tokens": {"type": "number", "description": "For sell: outcome tokens to sell."},
            "slippage_pct": {"type": "number", "description": "Price buffer in percent (default 3)."},
        },
        "required": ["action", "token_address"],
    },
}

RESULTS = {
    "name": "pfwa_results",
    "description": "List recently resolved PFWA markets with the winning outcome, so the user can see results and what to claim.",
    "parameters": {
        "type": "object",
        "properties": {
            "search": {"type": "string", "description": "Optional words to filter questions."},
            "limit": {"type": "integer", "description": "Max markets to return (default 10, max 50)."},
        },
        "required": [],
    },
}


RANDOM = {
    "name": "pfwa_random",
    "description": (
        "Verifiable randomness Hermes can't fake or bias: a random number in a range, coin flips, picking winners "
        "from a list, or a shuffle. It uses a drand evmnet round chosen before that round existed (the beacon HoodRand "
        "verifies onchain on Robinhood Chain) and returns a proof anyone can recheck. Use it instead of inventing a "
        "'random' answer for giveaways, raffles, draws, team picks or tie-breaks. Takes about 6 seconds."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "enum": ["number", "coin", "pick", "shuffle"]},
            "min": {"type": "integer", "description": "number: lowest value (default 1)."},
            "max": {"type": "integer", "description": "number: highest value (default 100)."},
            "count": {"type": "integer", "description": "How many numbers, flips or winners (default 1)."},
            "options": {"type": "array", "items": {"type": "string"}, "description": "pick/shuffle: the entries."},
            "seed": {"type": "string", "description": "Optional text mixed in, e.g. the giveaway name."},
        },
        "required": ["kind"],
    },
}

HOODRAND_LOOKUP = {
    "name": "hoodrand_lookup",
    "description": "Look up a HoodRand request on Robinhood Chain by sequence number: drand round, status, random number and transactions.",
    "parameters": {"type": "object", "properties": {"sequence": {"type": "string"}}, "required": ["sequence"]},
}

SHERWOOD = {
    "name": "sherwood_game",
    "description": "Live state of a Sherwood arena round on Robinhood Chain (a game on a Uniswap v4 hook where every move is a token buy): pot, time left, leaderboard, King of the Hill and burns.",
    "parameters": {
        "type": "object",
        "properties": {"game": {"type": "string", "enum": ["pfwa", "imd", "wif"], "description": "Default pfwa."}},
        "required": [],
    },
}
