"""MCP server exposing the four volatility-engine operations as tools.

Requirement v0.2 §7 A3.  The tools are thin wrappers over :mod:`engine.api` so
that the exact same code path is exercised by the CLI, the batch updater and
MCP clients — there is no second implementation to drift.

Tools
-----
``get_rates``        OHLC bars for a symbol / timeframe / window
``extract_waves``    ZigZag + Merge swing list
``compute_buckets``  80/15/5 class statistics + Range display bounds
``export_table``     write waves + §13 volatility table to disk, return hashes

Run
---
    python -m engine.mcp_server                    # stdio (MCP client default)
    python -m engine.mcp_server --transport sse --port 8765
    python -m engine.mcp_server --list             # print the tool schemas

Every tool returns the same JSON shape as :mod:`engine.api`::

    {"ok": true,  ...payload...}
    {"ok": false, "error": {"code": "...", "message": "..."}}

Expected failures are values, not exceptions, so an MCP client always gets a
structured reason (``no_terminal``, ``unknown_symbol``, ``no_data``,
``insufficient_sample``, ``bad_argument``, ``io_error``) instead of a protocol
error.

The MT5 connection is opened lazily on the first tool call that needs market
data and is shut down when the process exits.
"""

from __future__ import annotations

import argparse
import atexit
import json
import sys
from typing import Any, Dict, List, Optional

from . import api
from .version import ENGINE_VERSION

SERVER_NAME = "tsa-volatility-engine"
SERVER_INSTRUCTIONS = (
    "Martingale Scanner volatility engine (ZigZag 12/5/3 + Merge 35% + 80/15/5 "
    "buckets). Times are MT5 server-time labels 'YYYY-MM-DDTHH:MM'. "
    "Every tool returns {'ok': true, ...} or {'ok': false, 'error': {...}}. "
    "Bar counts are compared first, pips second — that is the vendor's own order."
)


def _shutdown_mt5() -> None:
    """Close the MT5 terminal session if one was opened."""
    try:
        from .sources import mt5_source

        mt5_source.shutdown()
    except Exception:  # pragma: no cover - best effort on interpreter exit
        pass


def build_server() -> Any:
    """Construct the MCPServer with all four tools registered.

    Imported lazily so that ``import engine.api`` never requires the ``mcp``
    package — the engine stays usable with no MCP dependency installed.
    """
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise SystemExit(
            "the 'mcp' package is required for the MCP server "
            "(pip install mcp); the engine itself does not need it"
        ) from exc

    server = MCPServer(
        name=SERVER_NAME,
        version=ENGINE_VERSION,
        instructions=SERVER_INSTRUCTIONS,
        log_level="WARNING",
    )

    @server.tool(
        name="get_rates",
        title="Get OHLC rates",
        description=(
            "Return OHLC bars for one symbol/timeframe/window, with digits, point, "
            "pip size and broker/server provenance. Give either start+end "
            "(server time 'YYYY-MM-DDTHH:MM') or past_bars (most recent N bars). "
            "limit truncates only the returned payload, not the computation."
        ),
    )
    def get_rates(
        symbol: str,
        tf: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        past_bars: Optional[int] = None,
        bars_csv: Optional[str] = None,
        meta_in: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        return api.get_rates(
            symbol,
            tf=tf,
            start=start,
            end=end,
            past_bars=past_bars,
            bars_csv=bars_csv,
            meta_in=meta_in,
            limit=limit,
        )

    @server.tool(
        name="extract_waves",
        title="Extract swing waves",
        description=(
            "Run the ZigZag (Depth/Deviation/Backstep) and Merge Percentage "
            "pipeline and return the swing list: idx, startTime, endTime, bars, "
            "amplitudePips, direction, plus pivot counts and parameters. "
            "Defaults 12/5/3 and 35% reproduce the vendor panel."
        ),
    )
    def extract_waves(
        symbol: str,
        tf: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        past_bars: Optional[int] = None,
        depth: int = 12,
        deviation: int = 5,
        backstep: int = 3,
        merge_pct: float = 35.0,
        merge_mode: str = "drop_next",
        bar_mode: str = "exclusive",
        bars_csv: Optional[str] = None,
        meta_in: Optional[str] = None,
    ) -> Dict[str, Any]:
        return api.extract_waves(
            symbol,
            tf=tf,
            start=start,
            end=end,
            past_bars=past_bars,
            depth=depth,
            deviation=deviation,
            backstep=backstep,
            merge_pct=merge_pct,
            merge_mode=merge_mode,
            bar_mode=bar_mode,
            bars_csv=bars_csv,
            meta_in=meta_in,
        )

    @server.tool(
        name="compute_buckets",
        title="Compute 80/15/5 buckets",
        description=(
            "Return the volatility classes: per-class count, total/average bars, "
            "total/average pips, longest and shortest swing, and the display "
            "range bounds. Either pass amplitudes (+ bar_counts) directly, or "
            "give a symbol and window to run the full pipeline first. "
            "method: count (default, evidence-backed) | rank | inc."
        ),
    )
    def compute_buckets(
        symbol: Optional[str] = None,
        tf: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        past_bars: Optional[int] = None,
        method: str = "count",
        depth: int = 12,
        deviation: int = 5,
        backstep: int = 3,
        merge_pct: float = 35.0,
        merge_mode: str = "drop_next",
        bar_mode: str = "exclusive",
        bars_csv: Optional[str] = None,
        meta_in: Optional[str] = None,
        amplitudes: Optional[List[float]] = None,
        bar_counts: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        return api.compute_buckets(
            symbol=symbol,
            tf=tf,
            start=start,
            end=end,
            past_bars=past_bars,
            method=method,
            depth=depth,
            deviation=deviation,
            backstep=backstep,
            merge_pct=merge_pct,
            merge_mode=merge_mode,
            bar_mode=bar_mode,
            bars_csv=bars_csv,
            meta_in=meta_in,
            amplitudes=amplitudes,
            bar_counts=bar_counts,
        )

    @server.tool(
        name="export_table",
        title="Export volatility table",
        description=(
            "Run the pipeline and write the artefacts to out_dir: "
            "<SYMBOL>_<TF>.waves.csv (+ .meta.json) and "
            "<SYMBOL>_<TF>.table.csv / .table.json. Returns every path with its "
            "sha256 so the caller can verify what landed on disk. "
            "This is what the daily updater calls."
        ),
    )
    def export_table(
        out_dir: str,
        symbol: str,
        tf: str = "H1",
        start: Optional[str] = None,
        end: Optional[str] = None,
        past_bars: Optional[int] = None,
        method: str = "count",
        depth: int = 12,
        deviation: int = 5,
        backstep: int = 3,
        merge_pct: float = 35.0,
        merge_mode: str = "drop_next",
        bar_mode: str = "exclusive",
        bars_csv: Optional[str] = None,
        meta_in: Optional[str] = None,
    ) -> Dict[str, Any]:
        return api.export_table(
            out_dir=out_dir,
            symbol=symbol,
            tf=tf,
            start=start,
            end=end,
            past_bars=past_bars,
            method=method,
            depth=depth,
            deviation=deviation,
            backstep=backstep,
            merge_pct=merge_pct,
            merge_mode=merge_mode,
            bar_mode=bar_mode,
            bars_csv=bars_csv,
            meta_in=meta_in,
        )

    return server


#: names in registration order — kept for the self-test and ``--list``
TOOL_NAMES = ("get_rates", "extract_waves", "compute_buckets", "export_table")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m engine.mcp_server",
        description="MCP server for the TSA volatility engine",
    )
    p.add_argument(
        "--transport",
        choices=("stdio", "sse", "streamable-http"),
        default="stdio",
        help="stdio for local MCP clients (default); sse / streamable-http for network",
    )
    p.add_argument("--host", default="127.0.0.1", help="bind host for sse / streamable-http")
    p.add_argument("--port", type=int, default=8765, help="bind port for sse / streamable-http")
    p.add_argument("--list", action="store_true", help="print tool schemas as JSON and exit")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    server = build_server()

    if args.list:
        print(
            json.dumps(
                {
                    "server": SERVER_NAME,
                    "version": ENGINE_VERSION,
                    "tools": list(TOOL_NAMES),
                    "transports": ["stdio", "sse", "streamable-http"],
                },
                indent=2,
            )
        )
        return 0

    atexit.register(_shutdown_mt5)
    if args.transport == "stdio":
        # stdio owns stdout — anything printed there corrupts the protocol.
        print(
            f"{SERVER_NAME} {ENGINE_VERSION}: serving {len(TOOL_NAMES)} tools on stdio",
            file=sys.stderr,
        )
        server.run(transport="stdio")
    else:
        print(
            f"{SERVER_NAME} {ENGINE_VERSION}: serving {len(TOOL_NAMES)} tools on "
            f"{args.transport} http://{args.host}:{args.port}",
            file=sys.stderr,
        )
        server.run(transport=args.transport, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
