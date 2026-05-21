"""Unit tests for dde_v4_scorer.py — DDE v4 scoring logic"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dde_v4_scorer import score_v4, read_csv_trades

class TestReadCSVTrades:
    def test_read_valid_csv(self):
        """Can read a valid CSV file"""
        trades = read_csv_trades('samples/forex-forest-signals-page-12962.csv')
        assert trades is not None
        assert len(trades) > 0
        
    def test_trade_has_required_fields(self):
        """Each trade has required fields"""
        trades = read_csv_trades('samples/forex-forest-signals-page-12962.csv')
        required = ['symbol', 'net_pips', 'net_profit', 'type', 'lots']
        for t in trades[:5]:
            for field in required:
                assert field in t, f"Missing field: {field}"
                
    def test_nonexistent_file(self):
        """Raises FileNotFoundError for missing file"""
        import pytest
        with pytest.raises(FileNotFoundError):
            read_csv_trades('/nonexistent/file.csv')

class TestScoreV4:
    def test_score_returns_dict(self):
        """score_v4 returns a dict with expected keys"""
        trades = read_csv_trades('samples/forex-forest-signals-page-12962.csv')
        if not trades:
            return  # Skip if no data
        result = score_v4(trades)
        assert result is not None
        assert 'score' in result
        assert 'red_card' in result
        
    def test_score_range(self):
        """Score should be between 0 and 100"""
        trades = read_csv_trades('samples/forex-forest-signals-page-12962.csv')
        if not trades:
            return
        result = score_v4(trades)
        if result:
            assert 0 <= result['score'] <= 100, f"Score {result['score']} out of range"

    def test_empty_trades(self):
        """score_v4 handles empty trade list"""
        result = score_v4([])
        assert result is None
