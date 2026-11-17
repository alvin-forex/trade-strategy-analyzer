"""TSA wave-indicator reconstruction engine (indicator line A, stage A1).

Reimplements the MartingaleScanner amplitude engine without using any
MT4/MT5 built-in ZigZag indicator: the swing detector is a from-scratch
Python port of the published MQL4 ZigZag algorithm (reference copy kept in
``engine/evidence/a1/mt4_zigzag_reference.mq4``), so behaviour is
deterministic and portable.
"""

from .version import ENGINE_VERSION

__all__ = ["ENGINE_VERSION"]
