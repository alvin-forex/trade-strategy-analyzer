"""
TSA (Trade Strategy Analyzer) Configuration

This module contains the single source of truth for EA-related mappings and configurations.
All other modules should import from this file instead of defining their own copies.
"""

# =============================================================================
# EA Type Mapping
# =============================================================================
# Maps EA type tags to lists of signal IDs (as strings for consistency)

EA_MAP = {
    'DW': ['10437','106','11984','12962','13790','16538','17547','20846','21698','22200','22278','25830','31593','32541','32719','34259','36338','36397','36511','19625','35434','35436'],
    'SMA': ['537','1470','1980','5001','5275','5566','10864','11984','14581','14724','16698','17611','19849','23617','30359','33101','34574','2739','16777','35362','5636'],
    'SMAPro': ['2351','32278','32541','17823','31781','14158'],
    'MKD': ['13461','14592','25260','16266'],
    'MKDPro': ['8325','25668','31781','3291','7919'],
    'S10': ['13798','16596'],
    'Flash': ['7919','11889','13863','14158','14341','16706','17962','20805','19849'],
    'GC': ['10437','10864','32541'],
    'GS': ['13461','1470','34574','36511'],
    'GEM': ['14581'],
    'MAN': ['12173'],
}

# =============================================================================
# EA Name Normalization
# =============================================================================
# Maps various EA name formats to standardized tags

EA_NORMALIZE = {
    'DragonWave': 'DW', 'Dragon Wave': 'DW',
    'Flash': 'Flash',
    'SMA': 'SMA', 'SMAPro': 'SMAPro', 'SMA Pro': 'SMAPro',
    'MKD': 'MKD', 'MKDPro': 'MKDPro', 'MKD Pro': 'MKDPro',
    'S10': 'S10',
    'GeminiClient': 'GC', 'Gemini Client': 'GC',
    'GeminiServer': 'GS', 'Gemini Server': 'GS',
    'StableHelper': None, 'Stable Helper': None,
}

# =============================================================================
# EA Override Mapping
# =============================================================================
# Manual overrides for specific signals (takes precedence over EA_MAP lookup)

EA_OVERRIDES = {
    '10344': 'Flash',
    '12173': 'SMA',
    '7999': 'MKD',
    '38678': 'DW',
}

# =============================================================================
# EA Display Names
# =============================================================================

EA_FULL_NAMES = {
    'DW': 'DragonWare',
    'SMA': 'SMA_EA',
    'SMAPro': 'SMA_Pro',
    'MKD': 'MKD_Scalper',
    'MKDPro': 'MKD_Pro',
    'S10': 'S10_Strategy',
    'Flash': 'Flash_Scalper',
    'GC': 'Gemini_Client',
    'GS': 'Gemini_Server',
    'GEM': 'GEM_Trader',
    'MAN': 'Manual',
    'UNK': 'Unknown',
}

# =============================================================================
# EA Colors (for charts and styling)
# =============================================================================
# Each tuple is (background_color, foreground_color)

EA_COLORS = {
    'DW':      ('#4a148c', '#ce93d8'),
    'SMA':     ('#1b5e20', '#a5d6a7'),
    'SMAPro':  ('#1b5e20', '#c8e6c9'),
    'MKD':     ('#e65100', '#ffcc80'),
    'MKDPro':  ('#bf360c', '#ffab91'),
    'Flash':   ('#0d47a1', '#90caf9'),
    'S10':     ('#004d40', '#80cbc4'),
    'GC':      ('#0d47a1', '#90caf9'),
    'GS':      ('#1a237e', '#9fa8da'),
    'GEM':     ('#880e4f', '#f48fb1'),
    'MAN':     ('#4527a0', '#b39ddb'),
    'UNK':     ('#333', 'var(--text2)'),
}

# =============================================================================
# Helper Functions
# =============================================================================

def get_ea_type(signal_id):
    """
    Get the EA type for a given signal ID.
    
    Args:
        signal_id: Signal ID (string or int)
    
    Returns:
        EA type tag (string), defaults to 'UNK' if not found
    """
    s = str(signal_id)
    
    # Check overrides first
    if s in EA_OVERRIDES:
        return EA_OVERRIDES[s]
    
    # Look up in EA_MAP
    for ea, ids in EA_MAP.items():
        if s in ids:
            return ea
    
    return 'UNK'


def get_ea_types(signal_id):
    """
    Get all EA types for a given signal ID (some signals belong to multiple EAs).
    
    Args:
        signal_id: Signal ID (string or int)
    
    Returns:
        List of EA type tags
    """
    s = str(signal_id)
    eas = []
    
    # Check overrides first
    if s in EA_OVERRIDES:
        eas.append(EA_OVERRIDES[s])
    
    # Look up in EA_MAP
    for ea, ids in EA_MAP.items():
        if s in ids and ea not in eas:
            eas.append(ea)
    
    return eas if eas else ['UNK']


def get_ea_style(ea_tag):
    """
    Get the color style for an EA tag.
    
    Args:
        ea_tag: EA type tag (may contain multiple EAs separated by '/')
    
    Returns:
        Tuple of (background_color, foreground_color)
    """
    first = ea_tag.split('/')[0]
    return EA_COLORS.get(first, EA_COLORS['UNK'])


def get_ea_full_name(ea_type):
    """
    Get the full display name for an EA type.
    
    Args:
        ea_type: EA type tag
    
    Returns:
        Full display name (string)
    """
    return EA_FULL_NAMES.get(ea_type, ea_type)


def normalize_ea_name(ea_name):
    """
    Normalize an EA name to its standard tag.
    
    Args:
        ea_name: EA name in various formats
    
    Returns:
        Standardized EA tag, or None if should be ignored
    """
    return EA_NORMALIZE.get(ea_name, ea_name)