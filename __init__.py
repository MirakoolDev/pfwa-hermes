"""PFWA for Hermes Agent: verifiable randomness, prediction markets and the Sherwood game on Robinhood Chain."""

from . import extra, schemas, tools


def register(ctx):
    for name, schema, handler in (
        ("pfwa_random", schemas.RANDOM, extra.random_draw),
        ("pfwa_markets", schemas.MARKETS, tools.markets),
        ("pfwa_quote", schemas.QUOTE, tools.quote),
        ("pfwa_positions", schemas.POSITIONS, tools.positions),
        ("pfwa_build_tx", schemas.BUILD_TX, tools.build_tx),
        ("pfwa_results", schemas.RESULTS, tools.results),
        ("hoodrand_lookup", schemas.HOODRAND_LOOKUP, extra.hoodrand_lookup),
        ("sherwood_game", schemas.SHERWOOD, extra.sherwood),
    ):
        ctx.register_tool(name=name, toolset="pfwa", schema=schema, handler=handler)
