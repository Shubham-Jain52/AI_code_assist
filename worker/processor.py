import json
import time
import sys
import os

# Add parent directory to path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.config import config
from shared.redis_client import get_redis_client
from analyzer import Analyzer

redis_client = get_redis_client()
analyzer = Analyzer()

def process_jobs():
    print("Worker started. Waiting for jobs...")
    while True:
        # BLPOP blocks until an item is available
        # It returns a tuple (queue_name, data)
        queue_name, data = redis_client.blpop(config.SUBMISSION_QUEUE)
        
        if data:
            job = json.loads(data)
            submission_id = job['id']
            diff = job['diff']
            language = job.get('language', 'python')
            
            print(f"Processing job {submission_id}...")
            
            # Run analysis
            results = analyzer.analyze(diff, language)
            
            # Save results
            redis_client.hset(f"result:{submission_id}", mapping={
                "status": "completed",
                "submission_id": submission_id,
                "risk_score": results['risk_score'],
                "quality_score": results['quality_score'],
                "comments": json.dumps(results['comments']),
                "flags": json.dumps(results['flags'])
            })
            print(f"Job {submission_id} completed.")

if __name__ == "__main__":
    process_jobs()
