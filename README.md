# [@p1timmy.weee.ee](https://bsky.app/profile/did:plc:eakx7mj6uhboh5eqtlauuz63)'s Bluesky feed generator server

Based on [ATProto Feed Generator](https://github.com/MarshalX/bluesky-feed-generator) powered by [The AT Protocol SDK for Python](https://github.com/MarshalX/atproto)

### How to use

`pip install -r requirements.txt` (must be done after cloning/updating repo), then `python -m server`

API can be accessed at <http://127.0.0.1:8000/>

If you wanna run the server without the firehose client, use `flask run`

#### Options

- `--dev`: Use Flask's built-in development server, ***not to be used in production***
- `--no-reload`: Disable reloading server on source/config file change
- `--update-lists-now`: Check for user list updates every time the server (re)starts

### Feeds

- [LoveLive!Sky](https://bsky.app/profile/did:plc:eakx7mj6uhboh5eqtlauuz63/feed/aaagaucwmakh6) - updated and improved version of these feeds:
  - [LoveLive!](https://bsky.app/profile/did:plc:s5talxoraotekyqbic7lns67/feed/aaaklhogzhke4) by [@aither.bsky.social](https://bsky.app/profile/did:plc:s5talxoraotekyqbic7lns67) (abandoned and unmaintained as of December 1st, 2024)
  - [ラブライブ！シリーズ](https://bsky.app/profile/did:plc:at746otrujvgvdmykrtgsdq5/feed/aaadj7zfg33zg) by [@lovelive-cal.bsky.social](https://bsky.app/profile/did:plc:at746otrujvgvdmykrtgsdq5/)

### License

MIT
