
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys
import uuid
import json

app = FastAPI(title="AI Code Review Assistant (Vercel)")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Inlined Analyzer (to avoid path/import issues on Vercel) ---
import subprocess
import tempfile

class VercelAnalyzer:
    def analyze(self, diff: str, language: str = "python"):
        # 1. Static Analysis
        lint_errors = []
        if language == "python":
            lint_errors, tmp_path = self._run_flake8(diff)
            
            # 2. Risk Classification
            if tmp_path and os.path.exists(tmp_path):
                risk_score, flags = self._assess_risk(diff, tmp_path)
                try:
                    os.remove(tmp_path) 
                except: 
                    pass
            else:
                 risk_score, flags = self._assess_risk(diff, None)
        else:
            risk_score, flags = self._assess_risk(diff, None)
        
        # 3. Quality Score
        quality_score = max(0, 100 - (len(lint_errors) * 5) - (risk_score * 2))
        
        return {
            "risk_score": risk_score,
            "quality_score": quality_score,
            "comments": lint_errors,
            "flags": flags
        }

    def _run_flake8(self, code: str) -> tuple:
        # Create a temp file to run flake8 on
        # Use simple name in /tmp explicitly if needed, but NamedTemporaryFile defaults to secure temp
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(code)
            tmp_path = tmp.name
            
        try:
            # Run flake8 using python -m
            result = subprocess.run(
                [sys.executable, '-m', 'flake8', tmp_path, '--format=default'], 
                capture_output=True, 
                text=True
            )
            
            errors = []
            if result.stdout:
                for line in result.stdout.splitlines():
                    parts = line.split(':', 3)
                    if len(parts) >= 4:
                        errors.append(parts[3].strip())
            return errors, tmp_path
        except Exception as e:
            if os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass
            # Log error but don't crash
            return [f"Lint Error (System): {str(e)}"], None

    def _run_bandit(self, file_path: str) -> tuple:
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'bandit', '-f', 'json', '-ll', file_path],
                capture_output=True,
                text=True
            )
            
            # Reset pointer or check output
            output_str = result.stdout
            if not output_str.strip():
                 # fallback if stdout empty, check stderr
                 if result.stderr:
                     return 0, [f"Security Scan Error: {result.stderr}"]
                 return 0, []

            output = json.loads(output_str)
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
        if tmp_path:
            bandit_score, bandit_flags = self._run_bandit(tmp_path)
            risk_score += bandit_score
            flags.extend(bandit_flags)
        
        # 2. Heuristics (Fallback)
        if "eval(" in diff or "exec(" in diff:
            if not any("eval" in f for f in flags):
                risk_score += 50
                flags.append("Security: Manual detection of eval/exec")
            
        if "password" in diff.lower() or "secret" in diff.lower():
             if not any("hardcoded" in f.lower() for f in flags):
                risk_score += 30
                flags.append("Security: Potential sensitive data hardcoded")
            
        if len(diff.splitlines()) > 100:
            risk_score += 10
            flags.append("Maintainability: Large change set (>100 lines)")
            
        return min(risk_score, 100), flags

analyzer = VercelAnalyzer()

class ReviewRequest(BaseModel):
    diff: str
    language: str = "python"

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.post("/review")
async def submit_review(request: ReviewRequest):
    # Synchronous processing for Serverless/Vercel
    try:
        results = analyzer.analyze(request.diff, request.language)
        
        return {
            "submission_id": str(uuid.uuid4()),
            "status": "completed",
            "risk_score": results['risk_score'],
            "quality_score": results['quality_score'],
            "comments": results['comments'],
            "flags": results['flags']
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(error_details)  # Log to Vercel console
        
        # Return error as special failed result so frontend can display it
        return {
            "submission_id": "error",
            "status": "failed",
            "risk_score": 0,
            "quality_score": 0,
            "comments": [],
            "flags": [f"System Error: {str(e)}"] 
        }
