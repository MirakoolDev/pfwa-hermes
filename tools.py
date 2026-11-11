"""PFWA tool handlers. Standard library only. Every handler returns a JSON string and never raises."""

import json
import re
import urllib.request
from decimal import Decimal

API = "https://www.pfwa.fun/api/agents"
SITE = "https://www.pfwa.fun"
RPC = "https://rpc.mainnet.chain.robinhood.com"
CHAIN_ID = 4663
WEI = Decimal(10) ** 18
UA = {"User-Agent": "pfwa-hermes-plugin/1.0", "Content-Type": "application/json"}

SEL = {
    "buy": "d96a094a",
    "sell": "e4849b32",
    "claim": "b401faf1",
    "tokensForEth": "2e834576",
    "costToBuyWithFee": "d95654b7",
    "proceedsFromSell": "e16e8310",
    "balanceOf": "70a08231",
}
ADDR = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _ok(data):
    return json.dumps(data, default=str)


def _err(msg):
    return json.dumps({"error": msg})


def _get(path):
    req = urllib.request.Request(API + path, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _rpc_batch(calls):
    """calls: list of (to, data_hex). Returns list of ints (None on revert)."""
    if not calls:
        return []
    body = [
        {"jsonrpc": "2.0", "id": i, "method": "eth_call", "params": [{"to": to, "data": "0x" + data}, "latest"]}
        for i, (to, data) in enumerate(calls)
    ]
    out = []
    for start in range(0, len(body), 50):
        chunk = body[start:start + 50]
        req = urllib.request.Request(RPC, data=json.dumps(chunk).encode(), headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode("utf-8"))
        if isinstance(res, dict):
            res = [res]
        by_id = {x.get("id"): x for x in res}
        for x in chunk:
            v = by_id.get(x["id"], {}).get("result")
            out.append(int(v, 16) if v and v != "0x" else None)
    return out


def _u256(n):
    return format(int(n), "064x")


def _addr_arg(a):
    return a.lower().replace("0x", "").rjust(64, "0")


def _eth(wei):
    return str((Decimal(wei) / WEI).quantize(Decimal("0.000000000001")).normalize())


def _to_wei(x):
    return int(Decimal(str(x)) * WEI)


def _filter(items, search, limit):
    if search:
        words = [w.lower() for w in search.split()]
        items = [m for m in items if all(w in m.get("question", "").lower() for w in words)]
    try:
        limit = max(1, min(int(limit or 10), 50))
    except (TypeError, ValueError):
        limit = 10
    return items[:limit]


def markets(args: dict, **kwargs) -> str:
    try:
        data = _get("/markets")
        ms = _filter(data.get("markets", []), args.get("search"), args.get("limit"))
        return _ok({
            "chain": "Robinhood Chain (4663)",
            "open_markets": data.get("activeMarkets"),
            "markets": [
                {
                    "id": m.get("id"),
                    "question": m.get("question"),
                    "ends": m.get("expiresAt"),
                    "volume": m.get("totalVolume"),
                    "trades": m.get("tradesCount"),
                    "page": f"{SITE}/market/{m.get('id')}",
                    "outcomes": [
                        {"label": o.get("label"), "chance": o.get("impliedProbability"), "token_address": o.get("tokenAddress")}
                        for o in m.get("options", [])
                    ],
                }
                for m in ms
            ],
        })
    except Exception as e:  # noqa: BLE001
        return _err(f"Could not load PFWA markets: {e}")


def quote(args: dict, **kwargs) -> str:
    try:
        token = str(args.get("token_address", ""))
        if not ADDR.match(token):
            return _err("token_address must be a 0x address from pfwa_markets")
        eth = args.get("eth")
        sell = args.get("sell_tokens")
        if eth is None and sell is None:
            eth = 0.001
        out = {"token_address": token}
        calls = []
        if eth is not None:
            calls.append((token, SEL["tokensForEth"] + _u256(_to_wei(eth))))
        if sell is not None:
            calls.append((token, SEL["proceedsFromSell"] + _u256(_to_wei(sell))))
        res = _rpc_batch(calls)
        i = 0
        if eth is not None:
            toks = res[i]
            i += 1
            if toks is None:
                return _err("The contract refused the quote; the market may be closed or resolved.")
            out["buy"] = {
                "eth_in": str(eth),
                "tokens_out": _eth(toks),
                "avg_price_eth": _eth(Decimal(_to_wei(eth)) / Decimal(toks) * WEI) if toks else None,
                "pays_if_wins": "each winning token's share of the market's ETH pool",
            }
        if sell is not None:
            proceeds = res[i]
            out["sell"] = {"tokens_in": str(sell), "eth_out": _eth(proceeds) if proceeds is not None else None}
        return _ok(out)
    except Exception as e:  # noqa: BLE001
        return _err(f"Quote failed: {e}")


def positions(args: dict, **kwargs) -> str:
    try:
        wallet = str(args.get("wallet", ""))
        if not ADDR.match(wallet):
            return _err("wallet must be a 0x address")
        open_ms = _get("/markets").get("markets", [])
        resolved = _get("/markets/resolved").get("markets", [])
        rows = []
        for m in open_ms:
            for o in m.get("options", []):
                rows.append(("open", m, o.get("label"), o.get("tokenAddress")))
        for m in resolved:
            win = m.get("winningTokenAddress")
            if win:
                rows.append(("won", m, _winner(m), win))
        bals = _rpc_batch([(t, SEL["balanceOf"] + _addr_arg(wallet)) for _, _, _, t in rows])
        held = [(r, b) for r, b in zip(rows, bals) if b]
        sells = _rpc_batch([(r[3], SEL["proceedsFromSell"] + _u256(b)) for r, b in held if r[0] == "open"])
        out_open, out_claim, si = [], [], 0
        for (kind, m, label, token), bal in held:
            item = {"market_id": m.get("id"), "question": m.get("question"), "outcome": label,
                    "tokens": _eth(bal), "token_address": token, "page": f"{SITE}/market/{m.get('id')}"}
            if kind == "open":
                v = sells[si]
                si += 1
                item["sells_now_for_eth"] = _eth(v) if v is not None else None
                out_open.append(item)
            else:
                item["action"] = "claim with pfwa_build_tx action=claim"
                out_claim.append(item)
        return _ok({"wallet": wallet, "open_positions": out_open, "claimable_winnings": out_claim})
    except Exception as e:  # noqa: BLE001
        return _err(f"Could not read positions: {e}")


def build_tx(args: dict, **kwargs) -> str:
    try:
        action = args.get("action")
        token = str(args.get("token_address", ""))
        if not ADDR.match(token):
            return _err("token_address must be a 0x address")
        slip = Decimal(str(args.get("slippage_pct", 3))) / 100
        if action == "buy":
            eth = args.get("eth")
            if not eth or float(eth) <= 0:
                return _err("buy needs eth > 0")
            value = _to_wei(eth)
            toks = _rpc_batch([(token, SEL["tokensForEth"] + _u256(value))])[0]
            if not toks:
                return _err("The contract refused the quote; the market may be closed.")
            # Ask for slightly fewer tokens than the ETH buys now, so a small price move still fills.
            amount = int(Decimal(toks) * (1 - slip))
            cost = _rpc_batch([(token, SEL["costToBuyWithFee"] + _u256(amount))])[0]
            if cost is None:
                return _err("Could not price the buy.")
            value = min(value, int(Decimal(cost) * (1 + slip)))
            tx = {"to": token, "value": str(value), "data": "0x" + SEL["buy"] + _u256(amount), "chainId": CHAIN_ID}
            summary = f"Buy {_eth(amount)} outcome tokens for at most {_eth(value)} ETH"
        elif action == "sell":
            tokens = args.get("tokens")
            if not tokens or float(tokens) <= 0:
                return _err("sell needs tokens > 0")
            amount = _to_wei(tokens)
            proceeds = _rpc_batch([(token, SEL["proceedsFromSell"] + _u256(amount))])[0]
            tx = {"to": token, "value": "0", "data": "0x" + SEL["sell"] + _u256(amount), "chainId": CHAIN_ID}
            summary = f"Sell {tokens} outcome tokens for about {_eth(proceeds or 0)} ETH"
        elif action == "claim":
            tx = {"to": token, "value": "0", "data": "0x" + SEL["claim"], "chainId": CHAIN_ID}
            summary = "Claim winnings from a resolved winning outcome"
        else:
            return _err("action must be buy, sell or claim")
        return _ok({
            "summary": summary,
            "unsigned_tx": tx,
            "network": {"name": "Robinhood Chain", "chainId": CHAIN_ID, "rpc": RPC},
            "note": "Unsigned. Sign and send it from your own wallet; Hermes holds no keys. Or trade on the market page.",
            "trade_on_site": f"{SITE}/markets",
        })
    except Exception as e:  # noqa: BLE001
        return _err(f"Could not build the transaction: {e}")


def _winner(m):
    label = m.get("winningOptionLabel")
    if label:
        return label
    opts, i = m.get("options") or [], m.get("winningOptionIndex")
    if isinstance(i, int) and 0 <= i < len(opts):
        return opts[i].get("label")
    win = (m.get("winningTokenAddress") or "").lower()
    return next((o.get("label") for o in opts if (o.get("tokenAddress") or "").lower() == win), None)


def results(args: dict, **kwargs) -> str:
    try:
        data = _get("/markets/resolved")
        ms = list(reversed(data.get("markets", [])))
        ms = _filter(ms, args.get("search"), args.get("limit"))
        return _ok({
            "resolved_markets": data.get("resolvedMarketsCount"),
            "markets": [
                {"id": m.get("id"), "question": m.get("question"), "winner": _winner(m),
                 "winning_token_address": m.get("winningTokenAddress"), "volume": m.get("totalVolume"),
                 "page": f"{SITE}/market/{m.get('id')}"}
                for m in ms
            ],
        })
    except Exception as e:  # noqa: BLE001
        return _err(f"Could not load results: {e}")
