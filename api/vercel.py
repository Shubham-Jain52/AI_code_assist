
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import sys
import uuid
import json

# Add project root to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from worker.analyzer import Analyzer

app = FastAPI(title="AI Code Review Assistant (Vercel)")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

analyzer = Analyzer()

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
