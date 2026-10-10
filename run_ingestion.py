"""
run_ingestion.py - Fill the database using Person 1's existing functions.

Put this file in the project ROOT (next to docker-compose.yml, .env, check_data.py).

Run everything:
    python run_ingestion.py

Run only some steps (names: prices news filings forecasts dossiers):
    python run_ingestion.py prices
    python run_ingestion.py news filings
"""
import os
import sys
import time
import traceback

from dotenv import load_dotenv

# 1) Load the root .env, then make sure we point at localhost
#    (inside Docker the host is "postgres"/"redis"; from your laptop it is localhost).
load_dotenv()
if os.getenv("POSTGRES_HOST", "localhost") in ("postgres", ""):
    os.environ["POSTGRES_HOST"] = "localhost"
if os.getenv("POSTGRES_PORT", "5433") == "5432":
    os.environ["POSTGRES_PORT"] = "5433"
if os.getenv("REDIS_HOST", "localhost") in ("redis", ""):
    os.environ["REDIS_HOST"] = "localhost"
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5433")
os.environ.setdefault("REDIS_HOST", "localhost")

# Import AFTER the environment is ready
from ingestion.sources import prices, news, filings, forecasts  # noqa: E402
from ingestion import dossier_builder  # noqa: E402


def step_prices():
    return prices.fetch_all_prices()


def step_news():
    return news.fetch_all_news()


def step_filings():
    return filings.fetch_all_filings()


def step_forecasts():
    return forecasts.fetch_all_forecasts()


def step_dossiers():
    return dossier_builder.build_all_dossiers()


STEPS = {
    "prices": step_prices,
    "news": step_news,
    "filings": step_filings,
    "forecasts": step_forecasts,
    "dossiers": step_dossiers,  # keep last: it merges everything above
}


def main():
    wanted = sys.argv[1:] or list(STEPS)
    unknown = [w for w in wanted if w not in STEPS]
    if unknown:
        print(f"Unknown step(s): {unknown}. Choose from: {list(STEPS)}")
        sys.exit(1)

    results = {}
    for name in wanted:
        print(f"\n--- {name} ---")
        t0 = time.time()
        try:
            out = STEPS[name]()
            results[name] = f"OK ({time.time() - t0:.1f}s)"
            summary = str(out)
            print(f"returned: {summary[:300]}")
        except Exception as e:
            results[name] = f"FAILED: {type(e).__name__}: {str(e)[:150]}"
            traceback.print_exc()

    print("\n" + "=" * 50)
    print("SUMMARY")
    for name, status in results.items():
        icon = "✅" if status.startswith("OK") else "❌"
        print(f"{icon} {name}: {status}")
    print("=" * 50)
    print("Now run:  python check_data.py")


if __name__ == "__main__":
    main()
