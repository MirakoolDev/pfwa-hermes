"""HoodRand randomness and Sherwood game tools. Standard library only; handlers return JSON and never raise."""

import hashlib
import json
import time
import urllib.error
import urllib.request

SITE = "https://www.pfwa.fun"
UA = {"User-Agent": "pfwa-hermes-plugin/1.0"}
DRAND = ["https://api.drand.sh", "https://api2.drand.sh", "https://api3.drand.sh"]
EVMNET_GENESIS, EVMNET_PERIOD = 1727521075, 3
EVMNET_HASH = "04f1e9062b8a81f848fded9c12306733282b2727ecced50032187751166ec8c3"


def _ok(data):
    return json.dumps(data, default=str)


def _err(msg):
    return json.dumps({"error": msg})


def _drand_round(rnd):
    for relay in DRAND:
        try:
            req = urllib.request.Request(f"{relay}/v2/beacons/evmnet/rounds/{rnd}", headers=UA)
            with urllib.request.urlopen(req, timeout=6) as r:
                sig = json.loads(r.read().decode("utf-8")).get("signature")
                if sig:
                    return sig
        except Exception:  # noqa: BLE001
            continue
    return None


def random_draw(args: dict, **kwargs) -> str:
    try:
        kind = args.get("kind", "number")
        seed = str(args.get("seed", ""))[:256]
        options = [str(o) for o in (args.get("options") or [])]
        lo, hi = int(args.get("min", 1)), int(args.get("max", 100))
        count = max(1, min(int(args.get("count", 1)), 100))
        if kind not in ("number", "coin", "pick", "shuffle"):
            return _err("kind must be number, coin, pick or shuffle")
        if kind in ("pick", "shuffle") and not options:
            return _err("pick and shuffle need options")
        if kind == "number" and hi < lo:
            return _err("max must be >= min")
        # Commit first: the draw uses a drand round that doesn't exist yet when the request is made,
        # so neither Hermes nor the user can know or choose the outcome in advance.
        now = time.time()
        target = int((now - EVMNET_GENESIS) // EVMNET_PERIOD) + 2
        sig = None
        for _ in range(12):
            time.sleep(1.5)
            sig = _drand_round(target)
            if sig:
                break
        if not sig:
            return _err("drand evmnet did not answer; try again in a few seconds")
        root = hashlib.sha256(bytes.fromhex(sig)).digest()

        def stream(i):
            return int.from_bytes(hashlib.sha256(root + seed.encode() + i.to_bytes(4, "big")).digest(), "big")

        if kind == "number":
            span = hi - lo + 1
            result = [lo + stream(i) % span for i in range(count)]
        elif kind == "coin":
            result = ["heads" if stream(i) % 2 == 0 else "tails" for i in range(count)]
        elif kind == "pick":
            pool, result = list(options), []
            for i in range(min(count, len(pool))):
                result.append(pool.pop(stream(i) % len(pool)))
        else:  # shuffle (Fisher-Yates)
            result = list(options)
            for j in range(len(result) - 1, 0, -1):
                k = stream(j) % (j + 1)
                result[j], result[k] = result[k], result[j]
        return _ok({
            "result": result,
            "kind": kind,
            "proof": {
                "source": "drand evmnet (League of Entropy), the beacon HoodRand verifies onchain on Robinhood Chain",
                "round": target,
                "round_chosen_before_it_existed": True,
                "requested_at_unix": int(now),
                "signature": sig,
                "verify_round": f"https://api.drand.sh/v2/beacons/evmnet/rounds/{target}",
                "chain_hash": EVMNET_HASH,
                "derivation": "root = sha256(signature); stream(i) = sha256(root || seed || uint32 i); "
                              "number = min + stream(i) mod (max-min+1); coin = heads if stream(i) even; "
                              "pick takes pool[stream(i) mod remaining]; shuffle is Fisher-Yates with stream(j) mod (j+1)",
                "seed": seed,
                "options": options or None,
            },
            "onchain_option": "For a number verified by a contract on Robinhood Chain, use HoodRand: https://www.pfwa.fun/hoodrand",
        })
    except Exception as e:  # noqa: BLE001
        return _err(f"Random draw failed: {e}")


def hoodrand_lookup(args: dict, **kwargs) -> str:
    try:
        seq = str(args.get("sequence", ""))
        if not seq.isdigit():
            return _err("sequence must be a number")
        req = urllib.request.Request(f"{SITE}/api/hoodrand/result?sequence={seq}", headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.read().decode("utf-8") or _err(f"HTTP {e.code}")
    except Exception as e:  # noqa: BLE001
        return _err(f"Lookup failed: {e}")


def sherwood(args: dict, **kwargs) -> str:
    try:
        game = args.get("game") or "pfwa"
        if game not in ("pfwa", "imd", "wif"):
            return _err("game must be pfwa, imd or wif")
        req = urllib.request.Request(f"{SITE}/api/sherwood/state?instance={game}", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            s = json.loads(r.read().decode("utf-8"))
        usd = s.get("ethUsd") or 0
        left = max(0, int((s.get("roundEnd") or 0) - time.time()))
        names = s.get("names") or {}
        return _ok({
            "game": "Sherwood x $" + str(s.get("token")),
            "how_it_works": "Every move is a buy in the pool. Moves score points; when the round ends the top 3 and the "
                            "King of the Hill split the ETH pot, and part of every pot buys the token back and burns it.",
            "round": s.get("round"),
            "ends_in": f"{left // 3600}h {left % 3600 // 60}m",
            "pot_eth": s.get("pot"),
            "pot_usd": round((s.get("pot") or 0) * usd, 2),
            "players_this_round": s.get("players"),
            "leaderboard": [
                {"player": b["player"], "name": names.get(b["player"].lower()), "points": b["points"], "would_win_eth": b.get("payout")}
                for b in s.get("board", [])
            ],
            "king_of_the_hill": (s.get("king") or {}).get("holder"),
            "burned": s.get("burned"),
            "play": {"pfwa": "https://sherwood.pfwa.fun", "imd": "https://sherwood.pfwa.fun/v1", "wif": "https://sherwood.pfwa.fun/wif"}[game],
        })
    except Exception as e:  # noqa: BLE001
        return _err(f"Could not load Sherwood: {e}")
