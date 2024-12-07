# @p1timmy.bsky.social's Bluesky feed generator server

Based on [ATProto Feed Generator](https://github.com/MarshalX/bluesky-feed-generator) powered by [The AT Protocol SDK for Python](https://github.com/MarshalX/atproto)

### How to use

`python -m server`, API can be accessed at <http://127.0.0.1:8000/>

If you wanna run the server without the firehose client, use `flask run`

#### Options

- `--dev`: Use Flask's built-in development server, ***not to be used in production***
- `--no-reload`: Disable reloading server on source/config file change

### Feeds

- [LoveLive!Sky](https://bsky.app/profile/did:plc:eakx7mj6uhboh5eqtlauuz63/feed/aaagaucwmakh6) (updated and improved version of [original feed](https://bsky.app/profile/did:plc:s5talxoraotekyqbic7lns67/feed/aaaklhogzhke4) by [@aither.bsky.social](https://bsky.app/profile/did:plc:s5talxoraotekyqbic7lns67))

### License

MIT
