import subprocess
import tempfile
import os
import json

class Analyzer:
    def analyze(self, diff: str, language: str = "python"):
        # 1. Static Analysis (Mock/Simple Wrapper)
        lint_errors = []
        if language == "python":
            lint_errors, tmp_path = self._run_flake8(diff)
            
            # 2. Risk Classification
            if tmp_path and os.path.exists(tmp_path):
                risk_score, flags = self._assess_risk(diff, tmp_path)
                os.remove(tmp_path) # Clean up after both checks
            else:
                 risk_score, flags = self._assess_risk(diff, None)
        else:
            risk_score, flags = self._assess_risk(diff, None)  # Fallback for non-python
        
        # 3. Quality Score
        quality_score = max(0, 100 - (len(lint_errors) * 5) - (risk_score * 2))
        
        comments = lint_errors
        
        return {
            "risk_score": risk_score,
            "quality_score": quality_score,
            "comments": comments,
            "flags": flags
        }

    import sys
    
    def _run_flake8(self, code: str) -> tuple:
        # Create a temp file to run flake8 on
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
            
        try:
            # Run flake8 using python -m to avoid PATH issues
            result = subprocess.run(
                [sys.executable, '-m', 'flake8', tmp_path, '--format=default'], 
                capture_output=True, 
                text=True
            )
            
            # Parse output
            errors = []
            if result.stdout:
                for line in result.stdout.splitlines():
                    # Format: /tmp/file.py:1:1: E123 error
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        errors.append(parts[3].strip())
            return errors, tmp_path
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return [f"Static analysis failed: {str(e)}"], None

    def _run_bandit(self, file_path: str) -> tuple:
        """Runs bandit for security analysis."""
        try:
            # -ll: report only medium and high severity
            # -f json: output in json format
            result = subprocess.run(
                [sys.executable, '-m', 'bandit', '-f', 'json', '-ll', file_path],
                capture_output=True,
                text=True
            )
            
            # Bandit returns exit code 1 if issues are found, so we don't check returncode check for success
            
            output = json.loads(result.stdout)
            issues = []
            score_impact = 0
            
            results = output.get('results', [])
            for issue in results:
                severity = issue['issue_severity']
                msg = f"Security ({severity}): {issue['issue_text']}"
                issues.append(msg)
                
                if severity == 'HIGH':
                    score_impact += 30
                elif severity == 'MEDIUM':
                    score_impact += 15
                    
            return score_impact, issues
            
        except Exception as e:
            return 0, [f"Security analysis failed: {str(e)}"]

    def _assess_risk(self, diff: str, tmp_path: str) -> tuple:
        risk_score = 0
        flags = []
        
        # 1. Run Bandit (Security)
        bandit_score, bandit_flags = self._run_bandit(tmp_path)
        risk_score += bandit_score
        flags.extend(bandit_flags)
        
        # 2. Heuristics (Fallback & Complexity)
        if "eval(" in diff or "exec(" in diff:
            # Still good to keep as a catch-all high risk pattern if bandit misses it or for other langs
            if not any("eval" in f for f in flags):
                risk_score += 50
                flags.append("Security: Manual detection of eval/exec")
            
        if "password" in diff.lower() or "secret" in diff.lower():
             if not any("hardcoded" in f.lower() for f in flags):
                risk_score += 30
                flags.append("Security: Potential sensitive data hardcoded")
            
        # Complexity heuristic (length-based)
        if len(diff.splitlines()) > 100:
            risk_score += 10
            flags.append("Maintainability: Large change set (>100 lines)")
            
        return min(risk_score, 100), flags
