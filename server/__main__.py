import argparse

from server.app import app, firehose_setup

try:
    import waitress
except ImportError:
    waitress = None


def main():
    parser = argparse.ArgumentParser(
        "server", description="ATProto Feed Generator Server"
    )
    parser.add_argument(
        "--dev",
        action="store_true",
        help="run development server - DO NOT USE IN PRODUCTION",
    )
    args = parser.parse_args()

    host = "127.0.0.1"
    port = "8000"
    if args.dev:
        firehose_setup()
        app.run(host=host, port=port, debug=True, use_reloader=False)
    elif waitress is None:
        raise RuntimeError(
            "waitress is not installed, run 'pip install waitress' and try again"
        )
    else:
        firehose_setup()
        waitress.serve(app, host=host, port=port)


if __name__ == "__main__":
    main()
