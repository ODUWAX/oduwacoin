# OduwaCoin Core

**Current public release: v2.0.0.2 / EDOSA**

OduwaCoin Core is the reference implementation for the OduwaCoin network. OWC is the native currency used by the network.

This repository contains the node, wallet, RPC, networking, staking, and supporting code used to build OduwaCoin Core.

## Current release

Version **2.0.0.2 / EDOSA** includes maintenance and reliability improvements such as:

- `getstakereport` RPC support for staking activity and rewards
- increased outbound peer connectivity
- updated secp256k1, UniValue, and LevelDB components
- Qt and other dependency updates
- wallet, staking, and network stability improvements carried forward from the IVIE release line

Release downloads and notes:

https://github.com/ODUWAX/oduwacoin/releases/tag/v2.0.0.2

## Verified blockchain bootstrap

A bootstrap archive is available for operators who need to initialize the blockchain database more quickly.

**Download**

https://bootstrap.oduwacoin.io/OduwaCoin-DB.zip

**SHA-256**

`0a54fb501f8986ee1dcffed18cf7bb12d7d20b3f39a2ba4f8a1018dfd4ec59bb`

**Checksum file**

https://bootstrap.oduwacoin.io/OduwaCoin-DB.zip.sha256

Always back up `wallet.dat` and fully stop OduwaCoin Core before replacing blockchain data directories.

## Building from source

Start with [INSTALL.md](INSTALL.md), then use the platform-specific instructions under [doc/](doc/).

Typical Unix build flow:

```bash
./autogen.sh
./configure
make
```

Build and dependency requirements vary by operating system. Review the platform-specific build notes before compiling.

## Contributing

OduwaCoin is open source. Contributions should be proposed through focused pull requests and reviewed before merge.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contributor workflow and review expectations.

Consensus-critical changes require substantially more review than documentation, build, testing, or non-consensus maintenance changes.

## Security

Please do not disclose exploitable vulnerabilities in a public issue.

See [SECURITY.md](SECURITY.md) for the responsible disclosure process.

## License

OduwaCoin Core is distributed under the MIT software license. See [COPYING](COPYING).
