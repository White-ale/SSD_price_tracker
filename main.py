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
    mode_group.add_argument(
        "--api",
        action="store_true",
        help="Run the FastAPI server.",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Reload the API server when code changes. Use with --api.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.once:
        from app.scheduler import run_once

        run_once()
        return

    if args.api:
        import uvicorn

        from app.config import API_HOST, API_PORT

        uvicorn.run("app.api:app", host=API_HOST, port=API_PORT, reload=args.reload)
        return

    from app.scheduler import run_monitor

    run_monitor()


if __name__ == "__main__":
    main()
