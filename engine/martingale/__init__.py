"""Extra Martingale Scanner -- engine only, no strategy logic.

Five concerns, one module each, because they fail independently:

``ingest``      trade-history CSV in, :class:`Trade` out (four header shapes,
                junk rows counted rather than dropped silently)
``layers``      lot tiers, by both the Excel v8.5 rule and the linear rule
``scanner``     baskets and their step geometry
``hst_reader``  MT4 ``.hst`` in, :class:`Bar` out
``waves``       rolling swing-amplitude bands over those bars

Nothing here decides entries, exits, or recommended parameters -- per the
dispatch, that belongs to LEGEND and the owner.
"""
