# AI Code Review Assistant

A lightweight, local-first code review tool that actually catches bugs before you commit. Think of it as a second pair of eyes that doesn't get tired.

## What is it?
It's a microservices-based system that accepts code snippets (currently Python), runs them through a gauntlet of static analysis (`flake8`) and security scanners (`bandit`), and gives you a risk score, quality metrics, and actionable feedback.

We built this because copying code into ChatGPT for review is tedious and potentially unsafe. This runs locally.

## Features
- **Security First**: Automatically flags hardcoded secrets, `eval()` usage, and SQL injection risks (via Bandit).
- **Quality Metrics**: Calculates a "Risk Score" and "Quality Score" based on linting errors and security severities.
- **Deep Analysis**: Doesn't just regex; it parses the AST to find logic flaws.
- **Modern UI**: A clean, dark-mode web interface to drop your code and see results instantly. Glassmorphism included because we like nice things.
- **Async Architecture**: Uses Redis queues to handle heavy analysis tasks without blocking the API.

## Tech Stack
- **Backend Service**: Python 3.9, FastAPI
- **Worker Service**: Python, Redis-py, Flake8, Bandit
- **Queue**: Redis
- **Frontend**: One-page HTML/CSS/JS (Vanilla, zero build steps required)
- **Containerization**: Docker & Docker Compose

## Quick Start
You have two options: the "I have Docker" way (recommended) and the "I want to install everything manually" way.

### Option 1: Docker (Recommended for Production)
This runs the full microservices architecture:
- **API**: Async, non-blocking.
- **Worker**: Dedicated background processing.
- **Redis**: Persistent job queue.

1.  Make sure you have Docker installed.
2.  Build and run:
    ```bash
    # We use a shared network for the services
    docker network create app-network || true
    
    # Spin up Redis
    docker run -d --name redis --network app-network redis:alpine
    
    # Build the app image
    docker build -t aicodeassist .
    
    # Run API and Worker
    docker run -d --name api --network app-network -p 8000:8000 -e REDIS_HOST=redis aicodeassist uvicorn api.main:app --host 0.0.0.0 --port 8000
    docker run -d --name worker --network app-network -e REDIS_HOST=redis aicodeassist python worker/processor.py
    ```
3.  Go to `http://localhost:8000`.

### Option 2: Serverless / Vercel (Fastest for Demos)
This runs in "Synchronous Mode" (No Redis, No Worker). Ideal for hosting a quick demo on Vercel's free tier.
- **API**: Handles analysis directly in the request.
- **Deploy**: Connect your GitHub repo to Vercel and it just works (config is in `vercel.json`).

### Option 3: Local Dev (Manual)
If you want to hack on the code:

1.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Start Redis**: (You'll need a local redis-server running on default port 6379, or use docker for just redis).
3.  **Start the Worker**:
    ```bash
    python worker/processor.py
    ```
4.  **Start the API** (in a new tab):
    ```bash
    uvicorn api.main:app --reload
    ```

## Usage
1.  Open the web UI.
2.  Paste a chunk of Python code (e.g., `def foo(): eval(input())`).
3.  Hit **Analyze**.
4.  Watch the score drop and the security flags pop up.

## Testing
We take reliability seriously. Run the full suite (Unit + Integration) with:
```bash
pytest
```
Currently passing 100% of tests.

## Roadmap
- [ ] Add support for JavaScript/TypeScript analysis.
- [ ] Authentication layer for multi-user teams.
- [ ] GitHub App integration for PR comments.

---
*Built with coffee and Python.*
