import subprocess
import tempfile
import os
import json

class Analyzer:
    def analyze(self, diff: str, language: str = "python"):
        # 1. Static Analysis (Mock/Simple Wrapper)
        lint_errors = []
        if language == "python":
            
            # 1. AST Analysis
            ast_risk, ast_flags, syntax_error, ast_suggestions = self._ast_check(diff)
            suggestions = ast_suggestions
            
            if syntax_error:
                return {
                    "risk_score": 100,
                    "quality_score": 0,
                    "comments": [syntax_error],
                    "flags": ["Critical: Syntax Error (Code cannot run)"],
                    "suggestions": suggestions
                }

            # 2. Static Analysis (Flake8)
            lint_errors, tmp_path = self._run_flake8(diff)
            
            # 3. Risk Classification
            if tmp_path and os.path.exists(tmp_path):
                risk_score, flags = self._assess_risk(diff, tmp_path)
                os.remove(tmp_path) # Clean up after both checks
            else:
                 risk_score, flags = self._assess_risk(diff, None)
        else:
            risk_score, flags = self._assess_risk(diff, None)
            suggestions = []
        
        # Combine AST and Bandit results
        risk_score = max(risk_score, ast_risk) if language == "python" else risk_score
        # Also need to add AST implementation for risk combining if I want full parity, 
        # but for now ensuring suggestions is priority.
        # Actually api/index.py adds them: risk_score += ast_risk
        if language == "python":
            risk_score += ast_risk
            flags.extend(ast_flags)

        # 4. Quality Score
        quality_score = max(0, 100 - (len(lint_errors) * 5) - (risk_score * 2))
        
        comments = lint_errors
        
        return {
            "risk_score": min(risk_score, 100),
            "quality_score": quality_score,
            "comments": comments,
            "flags": flags,
            "suggestions": suggestions
        }

    import sys
    
    def _ast_check(self, code: str):
        """Uses built-in AST to find logic errors and syntax crashes."""
        import ast
        risk = 0
        flags = []
        suggestions = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            msg = f"SyntaxError: {e.msg} at line {e.lineno}"
            
            # Run heuristics for common syntax errors
            if ".upper()" in code or ".lower()" in code:
                 # Check for 5.upper() pattern
                 import re
                 if re.search(r'\b\d+\.(upper|lower)', code):
                     suggestions.append("You are trying to call a method on a number literal. Use parenthesis: `(5).upper()` or quotes: `'5'.upper()`.")
            
            return 100, [], msg, suggestions
        except Exception as e:
            return 100, [], f"Parse Error: {str(e)}", []

        for node in ast.walk(tree):
            # Division by Zero
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
                if isinstance(node.right, ast.Constant) and node.right.value == 0:
                    risk += 50
                    flags.append("Logic: Division by Zero detected")
                    suggestions.append("Ensure the denominator is not zero.")
            
            # Infinite Loop patterns (heuristic)
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value == True:
                    # Check if break exists
                    has_break = False
                    for child in ast.walk(node):
                        if isinstance(child, ast.Break):
                            has_break = True
                            break
                    if not has_break:
                        risk += 30
                        flags.append("Logic: Potential infinite loop (while True without break)")
                        suggestions.append("Add a `break` statement inside the loop or use a condition variable.")

        return risk, flags, None, suggestions

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
