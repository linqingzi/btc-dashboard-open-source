#!/usr/bin/env python3
"""Build deterministic, entirely fictional dashboard fixtures without network access."""

import argparse
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scoring


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
BASE_TIME = datetime(2000, 1, 1, tzinfo=timezone.utc)
GENERATOR = "scripts/generate_demo.py:v1"


def synthetic_point(offset=0):
    """Invent a complete input schema; constants do not come from market data."""
    moment = BASE_TIME + timedelta(hours=offset)
    macro = {
        "fed_assets_trillions": round(7.0 + offset * 0.01, 3),
        "m2_yoy_pct": round(2.5 + offset * 0.02, 3),
        "rrp_billions": 250.0 + offset,
        "dxy": 100.0 + offset * 0.1,
        "real_yield_10y": 2.0,
        "cpi_yoy_pct": 3.0,
        "fed_funds_rate": 4.0,
        "yield_10y": 4.0,
        "gold_usd": 2000.0,
        "btc_gold_ratio": 5.0,
        "vix": {"price": 22.0, "change_pct": 0.5},
        "spx": {"price": 3000.0, "change_pct": 0.5},
        "copper": {"price": 3.0, "change_pct": -0.5},
        "oil": {"price": 90.0, "change_pct": 0.25},
        "etf": {
            name: {"price": 10.0 * (i + 1), "change_pct": 0.25 + offset * 0.01}
            for i, name in enumerate(("ibit", "fbtc", "gbtc", "arkb", "bitb"))
        },
        "usdt_mcap": 130_000_000_000.0,
        "usdc_mcap": 40_000_000_000.0,
        "stablecoin_total_mcap": 170_000_000_000.0,
        "stablecoin_total_vol": 30_000_000_000.0,
        "binance_funding_rate_pct": 0.003,
        "bybit_funding_rate_pct": 0.001,
        "avg_funding_rate_pct": 0.002,
        "binance_basis_pct_annual": 8.0,
        "total_oi_usd_bn": 6.0,
        "bybit_oi_usd_bn": 2.0,
        "fomc": {},
    }
    # The original divergence checks read this nested view of the same inputs.
    macro["derivatives"] = {
        "avg_funding_rate_pct": macro["avg_funding_rate_pct"],
        "oi_change_24h": 0.5,
    }
    return {
        "meta": {
            "synthetic": True,
            "generator": GENERATOR,
            "updated_at": moment.isoformat(),
            "updated_ts": int(moment.timestamp()),
            "description": "Fictional development fixture; not observed market data.",
        },
        "price": {"usd": 10_000.0 + offset * 25.0, "change_24h_pct": 2.5},
        "market": {
            "btc_dominance_pct": 50.0 + offset * 0.05,
            "volume_24h_usd": 20_000_000_000.0,
        },
        "sentiment": {
            "current": {"value": 45, "classification": "合成中性"},
            "reddit": {"net_sentiment": 0, "source": "合成示例"},
            "news": {"net_sentiment": 0, "source": "合成示例"},
        },
        "onchain": {
            "hashrate_1w_avg_eh_s": 500.0 + offset * 0.5,
            "difficulty": 42_000_000_000_000.0,
            "block_height": 500_000 + offset,
            "cm_active_addresses": 500_000,
            "cm_tx_count": 400_000,
            "bc_tx_volume_usd": 4_000_000_000.0,
            "bc_utxo_count": 90_000_000,
            "bc_avg_fee_usd": 2.0,
            "bc_avg_fee_btc": 0.01,
            "bc_miners_revenue": 15_000_000.0,
            "bc_wallet_users": 70_000_000,
            "cm_roi_30d": 5.0 + offset * 0.1,
            "cm_roi_1yr": 10.0 + offset * 0.1,
            "mvrv": 1.7,
            "nupl": 0.4,
            "realized_price_usd": 7500.0,
        },
        "supply": {
            "daily_issuance_btc": 450.0,
            "annual_inflation_rate_pct": 1.0,
            "percent_mined": 80.0,
        },
        "macro": macro,
        "status": {"healthy": True, "quality": "synthetic"},
    }


def history_fixture():
    """Eight invented hourly points, including the latest point."""
    return [synthetic_point(offset) for offset in range(-7, 1)]


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def generate(check=False):
    history = history_fixture()
    history_path = DATA_DIR / "history.json"
    expected_history = json_bytes(history)
    if check:
        if not history_path.is_file() or history_path.read_bytes() != expected_history:
            raise ValueError("data/history.json is not the reproducible synthetic fixture")
    else:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        history_path.write_bytes(expected_history)

    # Keep the original scoring module and its project-relative history reader intact.
    latest = copy.deepcopy(history[-1])
    result = scoring.calculate_score(latest, latest["meta"]["updated_ts"])
    latest["scoring"] = scoring.format_for_frontend(result)
    latest_path = DATA_DIR / "latest.json"
    expected_latest = json_bytes(latest)
    if check:
        if not latest_path.is_file() or latest_path.read_bytes() != expected_latest:
            raise ValueError("data/latest.json is not the reproducible synthetic fixture")
    else:
        latest_path.write_bytes(expected_latest)
    return latest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify fixtures without modifying files")
    args = parser.parse_args(argv)
    try:
        generate(check=args.check)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("Synthetic fixtures verified." if args.check else "Generated data/latest.json and data/history.json (synthetic only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
