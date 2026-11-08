"""OduwaCoin key and address primitives (pure Python, standard library only).

Mainnet parameters are taken from src/chainparams.cpp:
  PUBKEY_ADDRESS = 23   -> addresses start with "A"
  SECRET_KEY     = 151  -> compressed WIF keys start with "P"

Keys are generated with the operating system CSPRNG (``secrets``) and use
compressed public keys, matching what OduwaCoin Core's ``getnewaddress`` /
``dumpprivkey`` produce, so every key is directly importable with
``importprivkey`` and spendable with ``signrawtransaction``.
"""
import hashlib
import secrets

# --- network parameters -------------------------------------------------------
NETWORKS = {
    "main": {"pubkey": 23, "script": 85, "secret": 151},
    "test": {"pubkey": 111, "script": 196, "secret": 239},
}

# --- secp256k1 ----------------------------------------------------------------
P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)


def _add(a, b):
    if a is None:
        return b
    if b is None:
        return a
    if a[0] == b[0] and (a[1] + b[1]) % P == 0:
        return None
    if a == b:
        lam = 3 * a[0] * a[0] * pow(2 * a[1], -1, P) % P
    else:
        lam = (b[1] - a[1]) * pow(b[0] - a[0], -1, P) % P
    x = (lam * lam - a[0] - b[0]) % P
    return x, (lam * (a[0] - x) - a[1]) % P


def _mul(k, point=G):
    result = None
    addend = point
    while k:
        if k & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        k >>= 1
    return result


def pubkey_from_secret(secret: int, compressed: bool = True) -> bytes:
    x, y = _mul(secret)
    if compressed:
        return bytes([2 + (y & 1)]) + x.to_bytes(32, "big")
    return b"\x04" + x.to_bytes(32, "big") + y.to_bytes(32, "big")


# --- hashing / base58 ---------------------------------------------------------
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def _ripemd160(b: bytes) -> bytes:
    try:
        return hashlib.new("ripemd160", b).digest()
    except ValueError:  # OpenSSL 3 without legacy provider
        from ._ripemd160 import ripemd160
        return ripemd160(b)


def hash160(b: bytes) -> bytes:
    return _ripemd160(hashlib.sha256(b).digest())


def b58check_encode(payload: bytes) -> str:
    data = payload + sha256d(payload)[:4]
    n = int.from_bytes(data, "big")
    out = ""
    while n:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = len(data) - len(data.lstrip(b"\x00"))
    return "1" * pad + out


def b58check_decode(s: str) -> bytes:
    n = 0
    for c in s:
        if c not in B58:
            raise ValueError("invalid base58 character %r" % c)
        n = n * 58 + B58.index(c)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big")
    raw = b"\x00" * (len(s) - len(s.lstrip("1"))) + raw
    if len(raw) < 5 or sha256d(raw[:-4])[:4] != raw[-4:]:
        raise ValueError("bad base58 checksum")
    return raw[:-4]


# --- OduwaCoin encodings ------------------------------------------------------
def address_from_pubkey(pub: bytes, network: str = "main") -> str:
    return b58check_encode(bytes([NETWORKS[network]["pubkey"]]) + hash160(pub))


def secret_to_wif(secret: int, network: str = "main", compressed: bool = True) -> str:
    payload = bytes([NETWORKS[network]["secret"]]) + secret.to_bytes(32, "big")
    if compressed:
        payload += b"\x01"
    return b58check_encode(payload)


def wif_to_secret(wif: str, network: str = "main"):
    """Return (secret_int, compressed) or raise ValueError."""
    raw = b58check_decode(wif.strip())
    if raw[0] != NETWORKS[network]["secret"]:
        raise ValueError("not an OduwaCoin %s private key (version byte %d)" % (network, raw[0]))
    if len(raw) == 34 and raw[33] == 1:
        compressed = True
    elif len(raw) == 33:
        compressed = False
    else:
        raise ValueError("unexpected private key length")
    secret = int.from_bytes(raw[1:33], "big")
    if not 1 <= secret < N:
        raise ValueError("private key out of range")
    return secret, compressed


def address_from_wif(wif: str, network: str = "main") -> str:
    secret, compressed = wif_to_secret(wif, network)
    return address_from_pubkey(pubkey_from_secret(secret, compressed), network)


def is_valid_address(addr: str, network: str = "main") -> bool:
    try:
        raw = b58check_decode(addr.strip())
    except ValueError:
        return False
    return len(raw) == 21 and raw[0] in (NETWORKS[network]["pubkey"], NETWORKS[network]["script"])


def new_keypair(network: str = "main"):
    """Generate a fresh keypair and return (address, wif).

    The result is round-trip checked before being returned so a corrupted
    key can never reach paper.
    """
    secret = secrets.randbelow(N - 1) + 1
    wif = secret_to_wif(secret, network)
    addr = address_from_pubkey(pubkey_from_secret(secret), network)
    if address_from_wif(wif, network) != addr or not is_valid_address(addr, network):
        raise RuntimeError("key self-check failed; refusing to continue")
    return addr, wif


# Known-good pair produced by OduwaCoin Core v2.0.0.3 (getnewaddress + dumpprivkey).
_VECTOR_WIF = "PQywksjED8mtBGLGocdDxN7sva3JiHEqLxpyDb6mbAeZAeXsVzoj"
_VECTOR_ADDR = "AWpwKuYkb92XU3o8aZaxR6Xk3idCHLwZe4"


def self_test():
    if address_from_wif(_VECTOR_WIF) != _VECTOR_ADDR:
        raise RuntimeError("secp256k1/base58 self-test failed; do not use this machine")
