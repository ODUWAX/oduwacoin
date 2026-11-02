# OduwaCoin Core

**Current public release: v2.0.0.3 / ETINOSA**

OduwaCoin Core is the reference implementation for the OduwaCoin network. OWC is the native currency used by the network.

This repository contains the node, wallet, RPC, networking, staking, and supporting code used to build OduwaCoin Core.

## Current release

Version **2.0.0.3 / ETINOSA** modernizes the wallet and node software:

- signed and Apple-notarized macOS apps, with a native build for Apple Silicon (macOS 11+) and a separate Intel build (macOS 10.15+)
- OpenSSL 3.5 (replacing end-of-life OpenSSL 1.1.1), Qt 5.15.14, Boost 1.90 and Berkeley DB 6.2
- Windows 64-bit, Linux desktop and Ubuntu server packages, with SHA-256 checksums for every download
- a fix for a block-template validation crash, and separate inbound/outbound counts in `getnetworkinfo`
- no consensus or protocol changes; existing wallets and staking carry over, and v2.0.0.3 nodes run alongside v2.0.0.2

Release downloads and notes:

https://github.com/ODUWAX/oduwacoin/releases/tag/v2.0.0.3

## Verified blockchain bootstrap

A verified snapshot of the blockchain lets new nodes and wallets start in minutes instead of syncing from block 0. It is rebuilt automatically twice a week by the [Blockchain bootstrap workflow](.github/workflows/bootstrap.yml) from a cleanly stopped node, then tested offline before it is published. The current block height, build date and SHA-256 are listed on the [bootstrap release page](https://github.com/ODUWAX/oduwacoin/releases/tag/bootstrap).

**Download**

https://github.com/ODUWAX/oduwacoin/releases/download/bootstrap/OduwaCoin-DB.zip

**Checksum file**

https://github.com/ODUWAX/oduwacoin/releases/download/bootstrap/OduwaCoin-DB.zip.sha256

To use it, close OduwaCoin Core completely, delete the `blocks` and `chainstate` folders in your data directory, unzip `OduwaCoin-DB.zip` there, and start OduwaCoin Core again.

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
