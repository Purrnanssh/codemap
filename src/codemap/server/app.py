"""FastAPI application for real-time repository ingestion.

Provides REST endpoints to scan local directories, run the architecture
extraction pipelines asynchronously, and serve the resulting graph
JSON to the frontend.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from codemap.callgraph.builder import build_call_graph
from codemap.callgraph.exporters import to_json

app = FastAPI(title="CodeMap API")

# Allow the Vite frontend to access the API during local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For MVP. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestRequest(BaseModel):
    path: str


# In-memory job store for MVP.
# Maps job_id to status and result.
jobs: Dict[str, Dict[str, Any]] = {}


def _process_ingestion(job_id: str, target_path: Path) -> None:
    """Synchronous worker function that builds the graph."""
    try:
        jobs[job_id]["status"] = "processing"
        
        # Build the graph using our existing Python AST engine
        graph, parse_errors = build_call_graph(target_path)
        
        # Export to JSON payload
        json_payload = to_json(graph, min_complexity=1)
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = json_payload
        jobs[job_id]["errors"] = list(parse_errors.keys())
    except Exception as exc:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error_msg"] = str(exc)


@app.post("/api/v1/workspaces/ingest")
async def ingest_workspace(request: IngestRequest, background_tasks: BackgroundTasks) -> Dict[str, str]:
    """Start an asynchronous ingestion job for a local path."""
    target_path = Path(request.path).resolve()
    
    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {request.path}")
        
    import uuid
    job_id = str(uuid.uuid4())
    
    jobs[job_id] = {
        "status": "queued",
        "path": str(target_path),
        "result": None,
        "errors": None,
        "error_msg": None,
    }
    
    # Offload the heavy CPU-bound parsing to a background thread
    background_tasks.add_task(
        asyncio.to_thread, _process_ingestion, job_id, target_path
    )
    
    return {"job_id": job_id}


@app.get("/api/v1/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Poll the status of an ingestion job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = jobs[job_id]
    return {
        "job_id": job_id,
        "status": job["status"],
        "error_msg": job["error_msg"]
    }


@app.get("/api/v1/workspaces/{job_id}/graph")
async def get_workspace_graph(job_id: str):
    """Retrieve the generated graph JSON."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job is not completed yet")
        
    import json
    from fastapi.responses import JSONResponse
    
    # The to_json exporter already returns a JSON string, so we must load it
    # to return it natively as a JSONResponse, or just return Response(content=..., media_type="application/json")
    from fastapi import Response
    return Response(content=job["result"], media_type="application/json")
