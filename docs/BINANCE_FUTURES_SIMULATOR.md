# Binance Futures simulator scope and safe data loading

This module models a **single-asset USDT-margined cross-margin approximation** using current exchange metadata supplied by the caller. It does not send orders or make network requests.

## Inputs

- Public USDⓈ-M exchange metadata: `GET https://fapi.binance.com/fapi/v1/exchangeInfo`
- Per-account leverage brackets: `GET https://fapi.binance.com/fapi/v1/leverageBracket` (authenticated USER_DATA endpoint; do not commit API keys)
- Pass the symbol record to `BinanceMarketRules.from_exchange_info`.
- Pass the leverage-bracket response to `brackets_from_leverage_response`.
- Supply `liquidation_fee_rate` explicitly for each position from a verified instrument/account assumption; do not treat the default as an official universal Binance rate.

## What is modeled

- Per-symbol maintenance-margin tiers, using Binance's `maintMarginRatio` and cumulative `cum` amount.
- Symbol trading status, `PRICE_FILTER` min/max price and tick size, `LOT_SIZE`, `MARKET_LOT_SIZE`, `PERCENT_PRICE` bands when present, and minimum/maximum notional fields where provided. Percent-price checks require a caller-supplied reference price. Known `MAX_NUM_ORDERS` and `MAX_NUM_ALGO_ORDERS` limits can be checked when the caller supplies current counts (including the proposed order as appropriate).
- Portfolio equity as wallet balance plus unrealized PnL; portfolio maintenance margin and configured liquidation-fee reserve.
- Approximate cross-margin liquidation trigger price for one symbol while holding other symbols' mark prices constant.

## Important limitations

This is **not a complete exchange-matching simulator**. It does not yet model every order filter (including side-specific price bands where applicable, position-limit and conditional-order-specific constraints), leverage-bracket changes caused by account configuration, multi-assets mode, portfolio margin, isolated margin, partial liquidation/insurance fund/ADL mechanics, exchange liquidation execution prices, fee discounts, or mark-price path/intrabar chronology. The liquidation-fee rate is configured, not inferred from a universal rate. Cross liquidation prices are approximations and depend on the other positions' supplied marks.

Do not connect this module to live order routing. Use historical replay and paper trading, compare estimates against Binance testnet/account snapshots, and keep live trading disabled until independent review and risk sign-off.
