"""Decode every `PowerHistory_<TF>_<Period>.dat` in a directory into CSV.

    python -m engine.research.powerhistory_decode --dir "<dir>" --out decoded/

Deliverable for GitHub issue #27, stage 0.5. Two things make this auditable:

1. Each source file's sha256 is recomputed and reported, so it can be checked
   against `PowerHistory_MANIFEST.json` without trusting either side.
2. Each output CSV is written with LF line endings and a fixed column order, so
   a re-run on any machine produces byte-identical files.

The reader itself lives in `ccy_period_probe` and parses the currency codes out
of each file's own header. That matters: the two sample families store the nine
codes in *different* orders, so a hard-coded order would silently mis-assign
columns.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys

from .ccy_period_probe import read_dat, utc

MANIFEST_NAME = "PowerHistory_MANIFEST.json"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest_hashes(directory: str, explicit: str | None = None) -> dict[str, dict]:
    """Return {filename: manifest entry} from an explicit path or `<directory>/manifest`."""
    path = explicit or os.path.join(directory, MANIFEST_NAME)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        blob = json.load(fh)
    return {row["file"]: row for row in blob.get("files", [])}


def decode_one(src: str, out_csv: str) -> dict:
    dat = read_dat(src)
    os.makedirs(os.path.dirname(out_csv) or ".", exist_ok=True)
    # newline="" plus explicit "\n" keeps the file identical across platforms
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["timestamp_utc", "epoch", *dat.codes])
        for stamp, row in zip(dat.stamps, dat.rows):
            w.writerow([utc(stamp).strftime("%Y-%m-%d %H:%M:%S"), stamp, *[repr(v) for v in row]])
    return {
        "rows": len(dat.rows),
        "codes": list(dat.codes),
        "first": utc(dat.stamps[0]).strftime("%Y-%m-%d") if dat.stamps else None,
        "last": utc(dat.stamps[-1]).strftime("%Y-%m-%d") if dat.stamps else None,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="directory holding PowerHistory_*.dat")
    ap.add_argument("--out", default=None, help="output directory (default: <dir>/decoded)")
    ap.add_argument("--manifest", default=None, help="PowerHistory_MANIFEST.json to cross-check sha256 against")
    ap.add_argument("--manifest-out", default=None, help="where to write the decode manifest")
    args = ap.parse_args(argv)

    src_dir = args.dir
    out_dir = args.out or os.path.join(src_dir, "decoded")
    manifest_out = args.manifest_out or os.path.join(out_dir, "decode_manifest.json")

    if not os.path.isdir(src_dir):
        print(f"not a directory: {src_dir}", file=sys.stderr)
        return 2

    names = sorted(n for n in os.listdir(src_dir) if n.startswith("PowerHistory_") and n.endswith(".dat"))
    if not names:
        print(f"no PowerHistory_*.dat in {src_dir}", file=sys.stderr)
        return 2

    expected = load_manifest_hashes(src_dir, args.manifest)
    entries: list[dict] = []
    mismatch = 0
    missing_in_manifest = 0

    for name in names:
        src = os.path.join(src_dir, name)
        digest = sha256_of(src)
        csv_name = name.replace(".dat", ".csv")
        out_csv = os.path.join(out_dir, csv_name)
        info = decode_one(src, out_csv)

        exp = expected.get(name)
        if exp is None:
            missing_in_manifest += 1
            status = "no-manifest-entry"
        elif exp.get("sha256") == digest:
            status = "match"
        else:
            mismatch += 1
            status = "MISMATCH"

        entries.append(
            {
                "file": name,
                "csv": os.path.basename(out_csv),
                "bytes": os.path.getsize(src),
                "sha256": digest,
                "manifest_sha256": (exp or {}).get("sha256"),
                "sha256_status": status,
                "rows": info["rows"],
                "codes": info["codes"],
                "first": info["first"],
                "last": info["last"],
            }
        )

    os.makedirs(os.path.dirname(manifest_out) or ".", exist_ok=True)
    with open(manifest_out, "w", encoding="utf-8", newline="") as fh:
        json.dump(
            {
                "source_dir": os.path.abspath(src_dir),
                "file_count": len(entries),
                "manifest_present": bool(expected),
                "sha256_mismatch": mismatch,
                "no_manifest_entry": missing_in_manifest,
                "files": entries,
            },
            fh,
            ensure_ascii=False,
            indent=2,
        )
        fh.write("\n")

    print(f"decoded {len(entries)} file(s) -> {out_dir}")
    print(f"manifest -> {manifest_out}")
    if not expected:
        print("note: no PowerHistory_MANIFEST.json next to the samples; sha256 not cross-checked")
    elif mismatch or missing_in_manifest:
        print(f"sha256: {mismatch} mismatch, {missing_in_manifest} without manifest entry")
        return 1
    else:
        print(f"sha256: {len(entries)}/{len(entries)} match manifest")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
