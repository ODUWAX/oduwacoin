UNIX BUILD NOTES
====================
Some notes on how to build OduwaCoin in Unix.

(for OpenBSD specific instructions, see [build-openbsd.md](build-openbsd.md);
for the portable release binaries built from `depends/`, see [release-builds.md](release-builds.md))

Note
---------------------
Always use absolute paths to configure and compile oduwacoin and the dependencies,
for example, when specifying the path of the dependency:

	../dist/configure --enable-cxx --disable-shared --with-pic --prefix=$BDB_PREFIX

Here BDB_PREFIX must be an absolute path - it is defined using $(pwd) which ensures
the usage of the absolute path.

To Build
---------------------

```bash
./autogen.sh
./configure
make
make install # optional
```

This will build oduwacoin-qt as well if the dependencies are met.

Dependencies
---------------------

These dependencies are required:

 Library     | Purpose          | Description
 ------------|------------------|----------------------
 libssl      | Crypto           | Random Number Generation, Elliptic Curve Cryptography
 libboost    | Utility          | Library for threading, data structures, etc
 libevent    | Networking       | OS independent asynchronous networking

Optional dependencies:

 Library     | Purpose          | Description
 ------------|------------------|----------------------
 miniupnpc   | UPnP Support     | Firewall-jumping support
 libdb6.2    | Berkeley DB      | Wallet storage (only needed when wallet enabled)
 qt          | GUI              | GUI toolkit (only needed when GUI enabled)
 protobuf    | Payments in GUI  | Data interchange format used for payment protocol (only needed when GUI enabled)
 libqrencode | QR codes in GUI  | Optional for generating QR codes (only needed when GUI enabled)
 univalue    | Utility          | JSON parsing and encoding (bundled version will be used unless --with-system-univalue passed to configure)
 libzmq3     | ZMQ notification | Optional, allows generating ZMQ notifications (requires ZMQ version >= 4.x)

For the versions used in the release, see [release-process.md](release-process.md) under *Fetch and build inputs*.

Memory Requirements
--------------------

C++ compilers are memory-hungry. It is recommended to have at least 1.5 GB of
memory available when compiling OduwaCoin. On systems with less, gcc can be
tuned to conserve memory with additional CXXFLAGS:


    ./configure CXXFLAGS="--param ggc-min-expand=1 --param ggc-min-heapsize=32768"

Dependency Build Instructions: Ubuntu & Debian
----------------------------------------------
The daemon and CLI are built in CI on Ubuntu 20.04, 22.04, 24.04 and 26.04,
and on Fedora 43 and 44
(see [`.github/workflows/linux-build.yml`](../.github/workflows/linux-build.yml)).
The core unit test suite and the wallet smoke regression run on Ubuntu 20.04.

Build requirements (all supported releases):

    sudo apt-get install build-essential libtool autotools-dev automake pkg-config python3 git bsdmainutils libssl-dev libevent-dev

Boost libraries (all supported releases):

    sudo apt-get install libboost-system-dev libboost-filesystem-dev libboost-chrono-dev libboost-program-options-dev libboost-test-dev libboost-thread-dev libboost-random-dev

Boost.System is header-only in Boost 1.69 and later. `configure` detects this
and does not try to link a separate `boost_system` library, so newer Boost
releases (including 1.90) work without extra flags. `libboost-all-dev` can be
used instead of the individual packages above if preferred.

Berkeley DB (wallet support):

| Ubuntu release | Berkeley DB packages              |
|----------------|-----------------------------------|
| 20.04, 22.04   | `libdb-dev libdb++-dev`           |
| 24.04, 26.04   | `libdb-dev libdb5.3++-dev`        |

On Ubuntu 24.04 and later the plain `libdb++-dev` package does not provide the
C++ headers that configure needs, so install `libdb5.3++-dev` instead.

### Configure flags by release

| Ubuntu release | Default compiler / Boost / OpenSSL | Extra configure flags                    |
|----------------|------------------------------------|------------------------------------------|
| 20.04          | GCC 9 / Boost 1.71 / OpenSSL 1.1   | `--with-incompatible-bdb`                |
| 22.04          | GCC 11 / Boost 1.74 / OpenSSL 3.0  | `--with-incompatible-bdb`                |
| 24.04          | GCC 13 / Boost 1.83 / OpenSSL 3.0  | `--with-incompatible-bdb --enable-c++17` |
| 26.04          | GCC 15 / Boost 1.90 / OpenSSL 3.5  | `--with-incompatible-bdb --enable-c++17` |

Boost 1.82 and later require at least C++14, so `--enable-c++17` is required on
Ubuntu 24.04 and newer (the project otherwise defaults to C++11).

Example daemon/CLI build on Ubuntu 24.04 or 26.04:

```bash
./autogen.sh
./configure --with-incompatible-bdb --enable-c++17 --without-gui --without-miniupnpc --disable-zmq
make -j"$(nproc)"
```

Berkeley DB 6.2 is the wallet-compatibility target documented for the v2.0.0.2 release line.

The distribution packages above install Berkeley DB 5.3, which differs from the
release-wallet build. That is why `--with-incompatible-bdb` is passed; CI uses
it to validate compilation and tests across supported Linux build environments.

For production wallet portability, use the project-documented Berkeley DB
version (see *Berkeley DB* below) rather than assuming the distribution package
is wallet-compatible.

The current CI build keeps wallet support enabled because the v2.0.0.2 mining/RPC path still references wallet symbols.

Optional:

    sudo apt-get install libminiupnpc-dev (see --with-miniupnpc and --enable-upnp-default)

ZMQ dependencies:

    sudo apt-get install libzmq3-dev (provides ZMQ API 4.x)

Dependencies for the GUI: Ubuntu & Debian
-----------------------------------------

If you want to build Oduwacoin-Qt, make sure that the required packages for Qt development
are installed. Either Qt 5 or Qt 4 are necessary to build the GUI.
If both Qt 4 and Qt 5 are installed, Qt 5 will be used. Pass `--with-gui=qt4` to configure to choose Qt4.
To build without GUI pass `--without-gui`.

To build with Qt 5 (recommended) you need the following:

    sudo apt-get install libqt5gui5 libqt5core5a libqt5dbus5 qttools5-dev qttools5-dev-tools libprotobuf-dev protobuf-compiler

Alternatively, to build with Qt 4 you need the following:

    sudo apt-get install libqt4-dev libprotobuf-dev protobuf-compiler

libqrencode (optional) can be installed with:

    sudo apt-get install libqrencode-dev

Once these are installed, they will be found by configure and a oduwacoin-qt executable will be
built by default.

Dependency Build Instructions: Fedora
-------------------------------------
Build requirements:

    sudo dnf install gcc-c++ libtool make autoconf automake python3 openssl-devel libevent-devel boost-devel libdb-devel libdb-cxx-devel

Current Fedora releases ship Berkeley DB 5.3 (`libdb-devel`, `libdb-cxx-devel`)
and a recent Boost, so configure with `--with-incompatible-bdb --enable-c++17`.
The `libdb4-*` packages referenced in older guides no longer exist. CI builds
the daemon and CLI on Fedora 43 and 44 with these packages.

Optional:

    sudo dnf install miniupnpc-devel

To build with Qt 5 (recommended) you need the following:

    sudo dnf install qt5-qttools-devel qt5-qtbase-devel protobuf-devel

libqrencode (optional) can be installed with:

    sudo dnf install qrencode-devel

Notes
-----
The release is built with GCC and then "strip oduwacoind" to strip the debug
symbols, which reduces the executable size by about 90%.


miniupnpc
---------

[miniupnpc](http://miniupnp.free.fr/) may be used for UPnP port mapping.  It can be downloaded from [here](
http://miniupnp.tuxfamily.org/files/).  UPnP support is compiled in and
turned off by default.  See the configure options for upnp behavior desired:

	--without-miniupnpc      No UPnP support miniupnp not required
	--disable-upnp-default   (the default) UPnP support turned off by default at runtime
	--enable-upnp-default    UPnP support turned on by default at runtime


Berkeley DB
-----------
It is recommended to use Berkeley DB 6.2. If you have to build it yourself:

```bash
BITCOIN_ROOT=$(pwd)

# Pick some path to install BDB to, here we create a directory within the oduwacoin directory
BDB_PREFIX="${BITCOIN_ROOT}/build"
mkdir -p $BDB_PREFIX

# Fetch the source and verify that it is not tampered with
wget 'http://download.oracle.com/berkeley-db/db-6.2.32.tar.gz'
echo 'a9c5e2b004a5777aa03510cfe5cd766a4a3b777713406b02809c17c8e0e7a8fb  db-6.2.32.tar.gz' | sha256sum -c
# -> db-6.2.32.tar.gz: OK
tar -xzvf db-6.2.32.tar.gz

# Build the library and install to our prefix
cd db-6.2.32/build_unix/
#  Note: Do a static build so that it can be embedded into the executable, instead of having to find a .so at runtime
../dist/configure --enable-cxx --disable-shared --with-pic --prefix=$BDB_PREFIX
make install

# Configure OduwaCoin to use our own-built instance of BDB
cd $BITCOIN_ROOT
./autogen.sh
./configure LDFLAGS="-L${BDB_PREFIX}/lib/" CPPFLAGS="-I${BDB_PREFIX}/include/" # (other args...)
```

**Note**: You only need Berkeley DB if the wallet is enabled (see the section *Disable-Wallet mode* below).

Boost
-----
If you need to build Boost yourself:

	sudo su
	./bootstrap.sh
	./bjam install


Security
--------
To help make your oduwacoin installation more secure by making certain attacks impossible to
exploit even if a vulnerability is found, binaries are hardened by default.
This can be disabled with:

Hardening Flags:

	./configure --enable-hardening
	./configure --disable-hardening


Hardening enables the following features:

* Position Independent Executable
    Build position independent code to take advantage of Address Space Layout Randomization
    offered by some kernels. Attackers who can cause execution of code at an arbitrary memory
    location are thwarted if they don't know where anything useful is located.
    The stack and heap are randomly located by default but this allows the code section to be
    randomly located as well.

    On an AMD64 processor where a library was not compiled with -fPIC, this will cause an error
    such as: "relocation R_X86_64_32 against `......' can not be used when making a shared object;"

    To test that you have built PIE executable, install scanelf, part of paxutils, and use:

    	scanelf -e ./oduwacoin

    The output should contain:

     TYPE
    ET_DYN

* Non-executable Stack
    If the stack is executable then trivial stack based buffer overflow exploits are possible if
    vulnerable buffers are found. By default, oduwacoin should be built with a non-executable stack
    but if one of the libraries it uses asks for an executable stack or someone makes a mistake
    and uses a compiler extension which requires an executable stack, it will silently build an
    executable without the non-executable stack protection.

    To verify that the stack is non-executable after compiling use:
    `scanelf -e ./oduwacoin`

    the output should contain:
	STK/REL/PTL
	RW- R-- RW-

    The STK RW- means that the stack is readable and writeable but not executable.

Wallet-disabled build status
----------------------------
The configure script exposes `--disable-wallet`, but the current v2.0.0.2 source still has mining/RPC code paths that reference wallet symbols. A wallet-disabled build is therefore **not part of the supported CI configuration at this time**.

The public Linux CI build validates the daemon and CLI with wallet support enabled and uses:

    ./configure --with-incompatible-bdb --without-gui --without-miniupnpc --disable-zmq --disable-tests --disable-bench

This is a build-compatibility check. It does not change consensus rules, staking behavior, or wallet data formats.

Additional Configure Flags
--------------------------
A list of additional configure flags can be displayed with:

    ./configure --help


Setup and Build Example: Arch Linux
-----------------------------------
This example lists the steps necessary to setup and build a command line only, non-wallet distribution of the latest changes on Arch Linux:

    pacman -S git base-devel boost libevent python
    git clone https://github.com/ODUWAX/oduwacoin.git
    cd oduwacoin/
    ./autogen.sh
    ./configure --disable-wallet --without-gui --without-miniupnpc
    make check

Note:
Enabling wallet support requires either compiling against a Berkeley DB newer than 6.2 (package `db`) using `--with-incompatible-bdb`,
or building and depending on a local version of Berkeley DB 6.2.
As mentioned above, when maintaining portability of the wallet between the standard OduwaCoin distributions and independently built
node software is desired, Berkeley DB 6.2 must be used.


ARM Cross-compilation
-------------------
These steps can be performed on, for example, an Ubuntu VM. The depends system
will also work on other Linux distributions, however the commands for
installing the toolchain will be different.

Make sure you install the build requirements mentioned above.
Then, install the toolchain and curl:

    sudo apt-get install g++-arm-linux-gnueabihf curl

To build executables for ARM:

    cd depends
    make HOST=arm-linux-gnueabihf NO_QT=1
    cd ..
    ./configure --prefix=$PWD/depends/arm-linux-gnueabihf --enable-glibc-back-compat --enable-reduce-exports LDFLAGS=-static-libstdc++
    make


For further documentation on the depends system see [README.md](../depends/README.md) in the depends directory.

Building on FreeBSD
--------------------

(Updated as of FreeBSD 11.0)

Clang is installed by default as `cc` compiler, this makes it easier to get
started than on [OpenBSD](build-openbsd.md). Installing dependencies:

    pkg install autoconf automake libtool pkgconf
    pkg install boost-libs openssl libevent2

(`libressl` instead of `openssl` will also work)

For the wallet (optional):

    pkg install db5

This will give a warning "configure: WARNING: Found Berkeley DB other
than 4.8; wallets opened by this build will not be portable!", but as FreeBSD never
had a binary release, this may not matter. If backwards compatibility
with 4.8-built Bitcoin Core is needed follow the steps under "Berkeley DB" above.

Then build using:

    ./autogen.sh
    ./configure --with-incompatible-bdb BDB_CFLAGS="-I/usr/local/include/db5" BDB_LIBS="-L/usr/local/lib -ldb_cxx-5"
    make

*Note on debugging*: The version of `gdb` installed by default is [ancient and considered harmful](https://wiki.freebsd.org/GdbRetirement).
It is not suitable for debugging a multi-threaded C++ program, not even for getting backtraces. Please install the package `gdb` and
use the versioned gdb command e.g. `gdb7111`.
