import argparse
import asyncio
from . import monitor_solana


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor Solana transactions")
    parser.add_argument("--max-events", type=int, default=5, help="number of events to collect")
    parser.add_argument("--threshold-sol", type=float, default=0.001, help="minimum SOL delta to display")
    args = parser.parse_args()

    results = asyncio.run(
        monitor_solana(max_events=args.max_events, threshold_SOL=args.threshold_sol)
    )
    print("FINAL RESULTS:")
    for r in results:
        print(r)


if __name__ == "__main__":
    main()
