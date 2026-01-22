import uuid
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from shared.config import config
from shared.redis_client import get_redis_client
from .models import ReviewRequest, ReviewResponse, ReviewResult

app = FastAPI(title="AI Code Review Assistant")

import os

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    return FileResponse('api/static/index.html')

redis_client = get_redis_client()

@app.post("/review", response_model=ReviewResponse)
async def submit_review(request: ReviewRequest):
    submission_id = str(uuid.uuid4())
    job_data = {
        "id": submission_id,
        "diff": request.diff,
        "language": request.language
    }
    
    # Store initial status
    redis_client.hset(f"result:{submission_id}", mapping={
        "status": "pending", 
        "submission_id": submission_id
    })
    
    # Push to queue
    redis_client.rpush(config.SUBMISSION_QUEUE, json.dumps(job_data))
    
    return ReviewResponse(submission_id=submission_id, status="queued")

@app.get("/status/{submission_id}", response_model=ReviewResult)
async def get_status(submission_id: str):
    result = redis_client.hgetall(f"result:{submission_id}")
    
    if not result:
        raise HTTPException(status_code=404, detail="Submission not found")
        
    # If processing is complete, parse lists from strings
    if result.get("status") == "completed":
        return ReviewResult(
            submission_id=result["submission_id"],
            status=result["status"],
            risk_score=int(result.get("risk_score", 0)),
            quality_score=int(result.get("quality_score", 0)),
            comments=json.loads(result.get("comments", "[]")),
            flags=json.loads(result.get("flags", "[]")),
            suggestions=json.loads(result.get("suggestions", "[]"))
        )
            
    return ReviewResult(
        submission_id=submission_id,
        status=result.get("status", "unknown"),
        risk_score=0,
        quality_score=0,
        comments=[],
        flags=[],
        suggestions=[]
    )
