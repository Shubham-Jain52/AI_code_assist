
import pytest
from unittest.mock import MagicMock, patch, mock_open
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.analyzer import Analyzer

class TestAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return Analyzer()

    @patch("subprocess.run")
    def test_run_flake8_success(self, mock_run, analyzer):
        # Mock successful flake8 output
        mock_run.return_value = MagicMock(
            stdout="/tmp/f.py:1:1: E123 error\n/tmp/f.py:2:1: W234 warning",
            returncode=1
        )
        
        errors, tmp_path = analyzer._run_flake8("code")
        
        assert len(errors) == 2
        assert "E123 error" in errors[0]
        # Cleanup happens in analyze, but verifying temp file creation is tricky without mocking tempfile
        # We assume tempfile works
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    @patch("subprocess.run")
    def test_run_bandit_high_severity(self, mock_run, analyzer):
        # Mock bandit output
        bandit_output = {
            "results": [
                {"issue_severity": "HIGH", "issue_text": "Code injection"},
                {"issue_severity": "MEDIUM", "issue_text": "Weak crypto"}
            ]
        }
        mock_run.return_value = MagicMock(
            stdout=json.dumps(bandit_output),
            returncode=1
        )
        
        score_impact, issues = analyzer._run_bandit("dummy_path")
        
        assert score_impact == 45 # 30 (High) + 15 (Medium)
        assert len(issues) == 2
        assert "Security (HIGH)" in issues[0]

    @patch("worker.analyzer.Analyzer._run_bandit")
    @patch("worker.analyzer.Analyzer._run_flake8")
    def test_analyze_integration(self, mock_flake8, mock_bandit, analyzer):
        # Mock internal helpers
        mock_flake8.return_value = (["Lint Error"], "/tmp/mock.py")
        mock_bandit.return_value = (30, ["Security Flag"])
        
        # Mock os.remove and exists to avoid running on fake path
        with patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            
            result = analyzer.analyze("print('eval')", "python")
            
            assert result["risk_score"] == 30
            # Quality = 100 - (1*5) - (30*2) = 100 - 5 - 60 = 35
            assert result["quality_score"] == 35
            assert "Lint Error" in result["comments"]
            assert "Security Flag" in result["flags"]

    def test_heuristics_eval(self, analyzer):
        # Test fallback heuristics when bandit is mocked (return 0)
        with patch("worker.analyzer.Analyzer._run_bandit", return_value=(0, [])):
             # We pass None as tmp_path so bandit isn't called again potentially or handles it gracefully
             # Actually _assess_risk calls _run_bandit internally.
             # We are testing the logic inside _assess_risk
             
             # But let's test analyze() with "eval" in it
             # We need to ensure _run_bandit returns 0 so we trigger the manual heuristic check
             
             with patch("os.path.exists", return_value=False): # Force skip file path check logic for simple heuristic test if needed?
                 # Actually analyze() calls _run_flake8 which returns a path.
                 pass

             # DIRECT TEST of _assess_risk
             diff = "eval(input())"
             risk, flags = analyzer._assess_risk(diff, "dummy_path")
             
             # If bandit (mocked) returns 0, heuristics kick in
             assert risk == 50
             assert "Security: Manual detection of eval/exec" in flags[0]
