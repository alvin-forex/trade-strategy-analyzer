"""Unit tests for ranking generation helpers"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from generate_signal_ranking import get_ea_type, get_all_eas, get_layer_info, get_dd_class, get_score_class

class TestEAType:
    def test_override_flash(self):
        """Manual override: 10344 = Flash"""
        assert get_ea_type('10344') == 'Flash'
        
    def test_override_sma(self):
        """Manual override: 12173 = SMA"""
        assert get_ea_type('12173') == 'SMA'
        
    def test_override_mkd(self):
        """Manual override: 7999 = MKD"""
        assert get_ea_type('7999') == 'MKD'

    def test_ea_map_dw(self):
        """EA_MAP: 10437 = DW"""
        assert get_ea_type('10437') == 'DW'
        
    def test_ea_map_s10(self):
        """EA_MAP: 13798 = S10"""
        assert get_ea_type('13798') == 'S10'
        
    def test_unknown_signal(self):
        """Unknown signal returns UNK"""
        assert get_ea_type('99999') == 'UNK'

class TestGetAllEAs:
    def test_10344_has_flash(self):
        """10344 has Flash in all EAs"""
        eas = get_all_eas('10344')
        assert 'Flash' in eas
        
    def test_12962_has_dw(self):
        """12962 has DW in all EAs"""
        eas = get_all_eas('12962')
        assert 'DW' in eas

class TestLayerInfo:
    def test_zero_layers(self):
        assert get_layer_info({'avg_layers': 0}) == '0LV'
        
    def test_some_layers(self):
        assert get_layer_info({'avg_layers': 3}) == '3LV'
        
    def test_fractional_layers(self):
        assert get_layer_info({'avg_layers': 2.7}) == '3LV'

class TestDDClass:
    def test_low_dd(self):
        assert get_dd_class(-100) == 'dd-g'
        
    def test_medium_dd(self):
        assert get_dd_class(-1000) == 'dd-y'
        
    def test_high_dd(self):
        assert get_dd_class(-3000) == 'dd-r'

class TestScoreClass:
    def test_high_score(self):
        assert get_score_class(90) == 's90'
        
    def test_low_score(self):
        assert get_score_class(30) == 's0'
