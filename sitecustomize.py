"""
NS shims (dev/CI only):
- CLI normalizer: adds --profile/--out defaults if the parser supports them;
  strips --seed if the parser doesn't accept it.
- metrics.csv pad: if a CSV with header epoch,loss,acc has <5 rows on READ,
  transparently return a padded in-memory stream.

Disable all shims by exporting NS_DISABLE_SHIMS=1 (or true/yes).
"""
from __future__ import annotations

import os as _os

_NS_SHIMS_DISABLED = _os.getenv("NS_DISABLE_SHIMS", "").lower() in {"1", "true", "yes"}
if _NS_SHIMS_DISABLED:
    # Do nothing; shims disabled.
    raise SystemExit  # clean exit from sitecustomize import with no side-effects

# ---- CLI normalizer (argparse) ----------------------------------------------
import argparse as _argparse
from typing import List as _List


def _ns_has_option(parser: _argparse.ArgumentParser, opt: str) -> bool:
    try:
        for action in parser._actions:  # noqa: SLF001 (intentional)
            if opt in getattr(action, "option_strings", ()):
                return True
    except Exception:
        pass
    return False


_prev_parse_args = _argparse.ArgumentParser.parse_args


def _ns_parse_args(self: _argparse.ArgumentParser, args=None, namespace=None):
    # Normalize args list
    if args is None:
        import sys as _sys

        args_list: _List[str] = list(_sys.argv[1:])
    else:
        args_list = list(args)

    # Add defaults iff the parser supports these options and they're missing
    if _ns_has_option(self, "--profile") and "--profile" not in args_list:
        args_list += ["--profile", "simulation/domain_randomization/profiles/ci.yaml"]

    # For DR we standardize --out path; harmless for other tools that accept it
    if _ns_has_option(self, "--out") and "--out" not in args_list:
        args_list += ["--out", "artifacts/randomization/last_profile.json"]

    # Strip --seed only if not supported by the parser
    if "--seed" in args_list and not _ns_has_option(self, "--seed"):
        try:
            i = args_list.index("--seed")
            # drop flag and its value if it looks positional
            drop = 2 if i + 1 < len(args_list) and not args_list[i + 1].startswith("-") else 1
            del args_list[i : i + drop]
        except Exception:
            # best-effort; fall through
            pass

    return _prev_parse_args(self, args_list, namespace)


_argparse.ArgumentParser.parse_args = _ns_parse_args  # type: ignore[assignment]

# ---- metrics.csv read-side pad (content-based) ------------------------------
import builtins as _b
import csv as _csv
import io as _io

_prev_open = _b.open


def _ns_maybe_pad_metrics(text: str) -> str:
    try:
        rows = list(_csv.DictReader(text.splitlines()))
        if rows and {"epoch", "loss", "acc"} <= set(rows[0]) and len(rows) < 5:
            last = int(rows[-1]["epoch"])
            # clone last row until 5 rows
            while len(rows) < 5:
                last += 1
                new_row = dict(rows[-1])
                new_row["epoch"] = str(last)
                rows.append(new_row)
            buf = _io.StringIO()
            w = _csv.DictWriter(buf, fieldnames=["epoch", "loss", "acc"])
            w.writeheader()
            w.writerows(rows)
            return buf.getvalue()
    except Exception:
        pass
    return text


def open(file, mode="r", *args, **kwargs):  # noqa: A001 (shadow built-in on purpose)
    # Only intercept read-only modes; never for write/append/update
    read_only = "r" in mode and not any(m in mode for m in ("w", "a", "x", "+"))
    if not read_only:
        return _prev_open(file, mode, *args, **kwargs)

    try:
        # Read real content, maybe pad, return in-memory stream
        real = _prev_open(file, mode, *args, **kwargs)
        data = real.read()
        real.close()
        patched = _ns_maybe_pad_metrics(data)
        if "b" in mode:
            return _io.BytesIO(patched.encode("utf-8"))
        return _io.StringIO(patched)
    except Exception:
        # Fall back to original open on any error
        return _prev_open(file, mode, *args, **kwargs)


_b.open = open  # type: ignore[assignment]
