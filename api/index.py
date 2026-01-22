
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import sys
import traceback

app = FastAPI()

@app.post("/review")
async def submit_review(request: Request):
    try:
        # Lazy import everything to catch ImportErrors
        import json
        import uuid
        import subprocess
        import tempfile
        from pydantic import BaseModel

        # Parse body manually to avoid Pydantic validation errors causing 422s (which might look like errors)
        try:
            body = await request.json()
            diff = body.get("diff", "")
            language = body.get("language", "python")
        except Exception:
            diff = ""
            language = "python"

        # --- Define Analyzer Logic Locally ---
        class VercelAnalyzer:
            def analyze(self, diff: str, language: str = "python"):
                lint_errors = []
                flags = []
                risk_score = 0
                
                if language == "python":
                    lint_errors, tmp_path = self._run_flake8(diff)
                    if tmp_path and os.path.exists(tmp_path):
                        risk_score, flags = self._assess_risk(diff, tmp_path)
                        try: os.remove(tmp_path) 
                        except: pass
                    else:
                        risk_score, flags = self._assess_risk(diff, None)
                else:
                    risk_score, flags = self._assess_risk(diff, None)
                
                quality_score = max(0, 100 - (len(lint_errors) * 5) - (risk_score * 2))
                return {
                    "risk_score": risk_score,
                    "quality_score": quality_score,
                    "comments": lint_errors,
                    "flags": flags
                }

            def _run_flake8(self, code: str):
                # Explicitly use /tmp for Vercel
                tmp_path = os.path.join('/tmp', f'analysis_{uuid.uuid4().hex}.py')
                try:
                    with open(tmp_path, 'w') as f:
                        f.write(code)
                    
                    # Run flake8
                    cmd = [sys.executable, '-m', 'flake8', tmp_path, '--format=default']
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    errors = []
                    if result.stdout:
                        for line in result.stdout.splitlines():
                            parts = line.split(':', 3)
                            if len(parts) >= 4:
                                errors.append(parts[3].strip())
                    return errors, tmp_path
                except Exception as e:
                    return [f"Lint Error: {str(e)}"], tmp_path

            def _run_bandit(self, file_path: str):
                try:
                    cmd = [sys.executable, '-m', 'bandit', '-f', 'json', '-ll', file_path]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if not result.stdout.strip():
                        if result.stderr: return 0, [f"Bandit Error: {result.stderr}"]
                        return 0, []

                    output = json.loads(result.stdout)
                    issues = []
                    score = 0
                    for issue in output.get('results', []):
                        severity = issue['issue_severity']
                        issues.append(f"Security ({severity}): {issue['issue_text']}")
                        score += 30 if severity == 'HIGH' else 15
                    return score, issues
                except Exception as e:
                    return 0, [f"Bandit Failed: {str(e)}"]

            def _assess_risk(self, diff: str, tmp_path: str):
                risk = 0
                flags = []
                if tmp_path:
                    b_score, b_flags = self._run_bandit(tmp_path)
                    risk += b_score
                    flags.extend(b_flags)
                
                if "eval(" in diff or "exec(" in diff:
                    if not any("eval" in f for f in flags):
                        risk += 50
                        flags.append("Security: Use of eval/exec detected")
                
                if "password" in diff.lower():
                     if not any("hardcoded" in f.lower() for f in flags):
                        risk += 30
                        flags.append("Security: Potential hardcoded password")
                        
                return min(risk, 100), flags

        # Execute
        analyzer = VercelAnalyzer()
        results = analyzer.analyze(diff, language)
        
        return {
            "submission_id": str(uuid.uuid4()),
            "status": "completed",
            "risk_score": results['risk_score'],
            "quality_score": results['quality_score'],
            "comments": results['comments'],
            "flags": results['flags']
        }

    except Exception as e:
        # Catch-all: Return 200 with error details to display in Frontend
        return JSONResponse(content={
            "submission_id": "error",
            "status": "failed",
            "risk_score": 0,
            "quality_score": 0,
            "comments": [],
            "flags": [f"System Error: {str(e)}", traceback.format_exc()]
        }, status_code=200)

# Serve static files for frontend
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(static_dir, 'index.html'))
