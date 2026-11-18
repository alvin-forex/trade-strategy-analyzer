"""Reproduce the CCY Power `Period` findings from a `Power History` directory.

Usage
-----
    python -m engine.research.period_probe_run --dir "C:\\path\\to\\Power History"

Everything here is read-only against the supplied directory; nothing is written
except to stdout. The two reported laws are computed from the `.dat` files
alone, so they need no MT5 terminal and no market data.
"""

from __future__ import annotations

import argparse
import glob
import math
import os

from .ccy_period_probe import (
    DatFile,
    acf1,
    lattice_denominator,
    mean_abs_step,
    read_dat,
    stdev,
)

CURRENCIES = ("EUR", "GBP", "AUD", "NZD", "CHF", "JPY", "CAD", "USD", "XAU")


def _family(directory: str, tf: str) -> dict[int, DatFile]:
    """Map Period suffix -> DatFile for one timeframe prefix (D1/H4/H1/M30/M15)."""
    out: dict[int, DatFile] = {}
    for path in sorted(glob.glob(os.path.join(directory, f"PowerHistory_{tf}_*.dat"))):
        tail = os.path.basename(path)[len(f"PowerHistory_{tf}_") : -len(".dat")]
        if not tail.isdigit():
            continue
        out[int(tail)] = read_dat(path)
    return out


def law_acf(family: dict[int, DatFile], ccy: str = "EUR") -> list[tuple[int, float, float, float]]:
    """Law 1: acf1(Power_P) ~= (P-1)/(P+1.5), independent of broker feed.

    Returns rows of (P, observed acf1, predicted, error).
    """
    rows = []
    for p in sorted(family):
        dat = family[p]
        if ccy not in dat.codes:
            continue
        obs = acf1(dat.column(ccy))
        pred = (p - 1) / (p + 1.5)
        rows.append((p, obs, pred, obs - pred))
    return rows


def law_variance(family: dict[int, DatFile], ccy: str = "EUR") -> list[tuple[int, float, float]]:
    """Law 2: sd stays flat while acf1 rises, so Period is NOT a low-pass on the output.

    `sd(Power_P) / [ sd(Power_P0) / sqrt(P) ]` should stay near 1 if the operator
    merely averages P independent measurements.  Report (P, sd, ratio).
    """
    base_p = min(family)
    base = family[base_p]
    if ccy not in base.codes:
        return []
    sd0 = stdev(base.column(ccy))
    rows = []
    for p in sorted(family):
        dat = family[p]
        if ccy not in dat.codes:
            continue
        sd = stdev(dat.column(ccy))
        rows.append((p, sd, sd / (sd0 / math.sqrt(p))))
    return rows


def lattice_table(family: dict[int, DatFile]) -> list[tuple[str, dict[str, int | None]]]:
    """Per-file minimal denominator; equals C*N/9 when Power = 9Σ/(C·N)."""
    rows = []
    for p in sorted(family):
        dat = family[p]
        cells = {c: (lattice_denominator(dat.column(c)) if c in dat.codes else None) for c in CURRENCIES}
        rows.append((os.path.basename(dat.path), cells))
    return rows


def _fmt(rows, header) -> None:
    print(header)
    for r in rows:
        print("  " + "  ".join(f"{x:>8.3f}" if isinstance(x, float) else f"{x:>8}" for x in r))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True, help="directory holding PowerHistory_*.dat")
    ap.add_argument("--tf", default="H4", choices=("D1", "H4", "H1", "M30", "M15"))
    ap.add_argument("--ccy", default="EUR")
    args = ap.parse_args(argv)

    fam = _family(args.dir, args.tf)
    if not fam:
        print(f"no PowerHistory_{args.tf}_*.dat in {args.dir}")
        return 2

    print(f"== {args.tf} family: {len(fam)} file(s), Period = {sorted(fam)} ==")
    names = sorted(fam)
    print(f"{'Period':>7s} {'rows':>7s} {'codes[0]':>9s} {'mean|d|':>8s} {'sd':>7s} {'acf1':>7s}")
    for p in names:
        dat = fam[p]
        col = dat.column(args.ccy)
        print(
            f"{p:7d} {len(dat.rows):7d} {dat.codes[0]:>9s} "
            f"{mean_abs_step(col):8.4f} {stdev(col):7.4f} {acf1(col):7.4f}"
        )

    print(f"\n== Law 1: acf1(P) ~= (P-1)/(P+1.5)  [{args.ccy}] ==")
    for p, obs, pred, err in law_acf(fam, args.ccy):
        print(f"  P={p:<3d} obs={obs:7.4f}  pred={pred:7.4f}  err={err:+7.4f}")

    print(f"\n== Law 2: sd(P) / [sd(P_min)/sqrt(P)]  (1.0 => plain average) ==")
    for p, sd, ratio in law_variance(fam, args.ccy):
        print(f"  P={p:<3d} sd={sd:7.4f}  ratio={ratio:6.3f}")

    print("\n== Lattice denominators (== C*N/9 when Power = 9Σ/(C·N)) ==")
    print("  " + "".join(f"{c:>5s}" for c in CURRENCIES))
    for name, cells in lattice_table(fam):
        print(f"  {name:<26s}" + "".join(f"{(cells[c] if cells[c] else 0):5d}" for c in CURRENCIES))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
