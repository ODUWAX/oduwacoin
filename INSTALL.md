# Building OduwaCoin Core

OduwaCoin Core is built from source using the project's Autotools-based build system.

The current public source release is **v2.0.0.2 / EDOSA**.

## Platform build notes

Detailed platform-specific instructions are maintained under the `doc/` directory.

For Unix/Linux systems, start with:

- [doc/build-unix.md](doc/build-unix.md)

Other platform notes are available in the same directory where supported.

## Typical Unix build

From the repository root:

```bash
./autogen.sh
./configure
make
```

Installation is optional:

```bash
make install
```

Before building, install the dependencies listed in the relevant platform build document.

## Wallet compatibility

Wallet-enabled builds depend on Berkeley DB. Use the Berkeley DB version documented by the project when compatibility with existing `wallet.dat` files is required.

Do not replace, overwrite, or delete a production `wallet.dat` while OduwaCoin Core is running. Back up the wallet before upgrades, migrations, or blockchain-data replacement.

## Release binaries

Users who do not need to compile from source can use published release assets:

https://github.com/ODUWAX/oduwacoin/releases

Always verify the release source and back up wallet data before upgrading.
