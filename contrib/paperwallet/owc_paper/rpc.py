"""Minimal JSON-RPC client for OduwaCoin Core (oduwacoind / OduwaCoin-Qt with server=1)."""
import base64
import json
import os
import platform
import urllib.error
import urllib.request
from decimal import Decimal

DEFAULT_PORT = {"main": 26682, "test": 25715}


def default_datadir():
    system = platform.system()
    home = os.path.expanduser("~")
    if system == "Windows":
        return os.path.join(os.environ.get("APPDATA", home), "OduwaCoin")
    if system == "Darwin":
        return os.path.join(home, "Library", "Application Support", "OduwaCoin")
    return os.path.join(home, ".OduwaCoin")


def read_conf(path):
    conf = {}
    if path and os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                line = line.split("#", 1)[0].strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    conf[k.strip()] = v.strip()
    return conf


class RPCError(Exception):
    pass


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)


class CoreRPC:
    def __init__(self, url=None, user=None, password=None, datadir=None, conf=None, network="main"):
        datadir = datadir or default_datadir()
        conf_path = conf or os.path.join(datadir, "OduwaCoin.conf")
        cfg = read_conf(conf_path)
        user = user or cfg.get("rpcuser")
        password = password or cfg.get("rpcpassword")
        if not (user and password):
            cookie = os.path.join(datadir, ".cookie")
            if os.path.exists(cookie):
                user, password = open(cookie).read().strip().split(":", 1)
        if not (user and password):
            raise RPCError(
                "No RPC credentials. Add rpcuser/rpcpassword and server=1 to %s "
                "(then restart the wallet), or pass --rpcuser/--rpcpassword." % conf_path)
        port = cfg.get("rpcport", DEFAULT_PORT[network])
        self.url = url or "http://127.0.0.1:%s/" % port
        self._auth = "Basic " + base64.b64encode(("%s:%s" % (user, password)).encode()).decode()
        self._id = 0

    def call(self, method, *params):
        self._id += 1
        body = json.dumps({"jsonrpc": "1.0", "id": self._id, "method": method,
                           "params": list(params)}, cls=_Enc).encode()
        req = urllib.request.Request(self.url, data=body, headers={
            "Authorization": self._auth, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read(), parse_float=Decimal)
        except urllib.error.HTTPError as e:
            try:
                data = json.loads(e.read(), parse_float=Decimal)
            except Exception:
                raise RPCError("HTTP %s from wallet RPC (check rpcuser/rpcpassword)" % e.code)
        except urllib.error.URLError as e:
            raise RPCError("Cannot reach OduwaCoin Core at %s (%s). Is the wallet running with "
                           "server=1?" % (self.url, e.reason))
        if data.get("error"):
            raise RPCError("%s: %s" % (method, data["error"].get("message", data["error"])))
        return data["result"]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *p: self.call(name, *p)
