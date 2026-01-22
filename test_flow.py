import requests
import time
import sys

API_URL = "http://localhost:8000"

def test_flow():
    print("1. Submitting review request...")
    diff_content = """
def bad_function():
    a = 1
    eval("print(a)")  # Risk!
    password = "secret" # Risk!
    """
    
    try:
        response = requests.post(f"{API_URL}/review", json={"diff": diff_content})
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Is it running?")
        sys.exit(1)
        
    data = response.json()
    submission_id = data["submission_id"]
    print(f"   Submitted! ID: {submission_id}")
    
    print("2. Polling for results...")
    for i in range(10):
        resp = requests.get(f"{API_URL}/status/{submission_id}")
        if resp.status_code == 200:
            result = resp.json()
            status = result["status"]
            print(f"   Attempt {i+1}: Status = {status}")
            
            if status == "completed":
                print("\nSUCCESS! Analysis complete.")
                print(f"Risk Score: {result['risk_score']}")
                print(f"Quality Score: {result['quality_score']}")
                print(f"Flags: {result['flags']}")
                
                # Assertions
                assert result['risk_score'] > 0, "Risk score should be high for eval/password"
                assert any("eval" in f for f in result['flags']), "Flags should mention eval"
                return
        else:
            print(f"   Error fetching status: {resp.status_code}")
            
        time.sleep(1)
        
    print("\nTIMEOUT: Analysis did not complete in time.")
    sys.exit(1)

if __name__ == "__main__":
    test_flow()
