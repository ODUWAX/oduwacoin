# Release builds

Release binaries are built from the pinned dependencies in `depends/` by the
[Release build workflow](../.github/workflows/release-build.yml). It runs on
pull requests that touch the build system, on manual dispatch, and on `v*` tags.
A tag push also creates a draft GitHub release with all assets and a
`SHA256SUMS` file. Drafts stay private until a maintainer publishes them.

## Pinned dependency versions (v2.0.0.3 ETINOSA)

| Package     | Version | Notes                                              |
|-------------|---------|----------------------------------------------------|
| OpenSSL     | 3.5.9   | LTS branch; replaces the end-of-life 1.1.1         |
| Qt          | 5.15.14 | Static; native Apple Silicon support               |
| Boost       | 1.90.0  | Boost.System is header-only and no longer linked   |
| Berkeley DB | 6.2.32  | Same 6.2 wallet format as v2.0.0.2                 |

Berkeley DB 6.2.38 (used for v2.0.0.2) is no longer downloadable from Oracle,
so 6.2.32 is used. Both write the same 6.2 on-disk format, so wallets move
between v2.0.0.2 and v2.0.0.3 unchanged.

## Targets and assets

| Target            | Built on                     | Assets                                                        |
|-------------------|------------------------------|---------------------------------------------------------------|
| Linux x86_64      | Ubuntu 20.04 (glibc 2.31)    | `-linux.tar.gz` (GUI + daemon), `-ubuntu-daemon.tar.gz`       |
| Windows x86_64    | Ubuntu 20.04, MinGW-w64      | `-win64.zip` (`oduwacoin-qt.exe`, `oduwacoind.exe`, cli, tx)  |
| macOS arm64       | macOS 14, Xcode 15.4         | `-macOS-arm64.dmg`, `-macOS-arm64-daemon.tar.gz` (macOS 11+)  |
| macOS x86_64      | macOS 14, Xcode 15.4         | `-macOS-x86_64.dmg`, `-macOS-x86_64-daemon.tar.gz` (10.15+)   |

The Windows executables only link against Windows system DLLs.

## Linux GUI runtime packages

The Linux `oduwacoin-qt` binary links Qt statically but uses the system X11/XCB,
font and keyboard libraries. Most desktops already have them. On a minimal
Debian or Ubuntu system install:

```bash
sudo apt-get install libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-randr0 \
  libxcb-render-util0 libxcb-shape0 libxcb-shm0 libxcb-sync1 libxcb-xfixes0 \
  libxcb-xinerama0 libxcb-xkb1 libxkbcommon-x11-0 libfontconfig1 libfreetype6
```

The daemon (`oduwacoind`) needs none of these.

## Building locally

```bash
make -C depends HOST=x86_64-pc-linux-gnu NO_UPNP=1 NO_ZMQ=1   # or x86_64-w64-mingw32, aarch64-apple-darwin
./autogen.sh
CONFIG_SITE=$PWD/depends/x86_64-pc-linux-gnu/share/config.site ./configure \
  --prefix=/ --enable-c++17 --disable-bench --enable-reduce-exports \
  --without-miniupnpc --disable-zmq
make
```

For Windows, use the POSIX-threads MinGW compiler
(`update-alternatives --set x86_64-w64-mingw32-g++ /usr/bin/x86_64-w64-mingw32-g++-posix`).
macOS builds run natively on a Mac with Xcode; `make appbundle` produces
`Oduwacoin-Qt.app`.

## macOS signing and notarization

The macOS jobs sign and notarize only when these repository secrets exist
(Settings > Secrets and variables > Actions):

| Secret                     | Contents                                                   |
|----------------------------|------------------------------------------------------------|
| `MACOS_CERT_P12_BASE64`    | Base64 of the exported "Developer ID Application" `.p12`   |
| `MACOS_CERT_PASSWORD`      | Password used when exporting the `.p12`                    |
| `APPLE_API_KEY_P8_BASE64`  | Base64 of the App Store Connect API key (`AuthKey_*.p8`)   |
| `APPLE_API_KEY_ID`         | The API key ID                                             |
| `APPLE_API_ISSUER_ID`      | The issuer ID shown on the App Store Connect keys page     |

Without them the builds still succeed and produce unsigned assets.
