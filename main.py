import argparse


def parse_args():
    parser = argparse.ArgumentParser(description="SSD price tracker")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--once",
        action="store_true",
        help="Check prices once and exit.",
    )
    mode_group.add_argument(
        "--monitor",
        action="store_true",
        help="Keep checking prices at the configured interval.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.once:
        from app.scheduler import run_once

        run_once()
        return

    from app.scheduler import run_monitor

    run_monitor()


if __name__ == "__main__":
    main()
