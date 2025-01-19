import argparse

import hupper

try:
    import waitress
except ImportError:
    waitress = None


def main():
    parser = argparse.ArgumentParser(
        "server", description="ATProto Feed Generator Server"
    )
    parser.add_argument(
        "--update-lists-now",
        action="store_true",
        help="update user lists immediately at startup/reload",
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="run development server - DO NOT USE IN PRODUCTION",
    )
    parser.add_argument(
        "--no-reload",
        action="store_false",
        dest="reload",
        help="disable reloading on source/config file changes",
    )
    args = parser.parse_args()

    if args.reload:
        reloader = hupper.start_reloader("server.__main__.main", shutdown_interval=60)
        reloader.watch_files([".env", "lists"])

    if not args.dev and waitress is None:
        raise RuntimeError(
            "waitress is not installed, run 'pip install waitress' and try again"
        )

    # Do the imports here instead of the top to prevent an old DB connection becoming
    # unused after a graceful reload
    from server.app import app, firehose_setup

    firehose_setup(args.update_lists_now)

    host = "127.0.0.1"
    port = 8000
    if args.dev:
        app.run(host=host, port=port, debug=True, use_reloader=False)
    else:
        waitress.serve(app, host=host, port=port)


if __name__ == "__main__":
    main()
