"""FastAPI backend using FastMCP servers."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import json
import traceback

from src.mcp.client import call_nlp_tool, call_graph_tool

app = FastAPI(title="Family Network API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProcessRequest(BaseModel):
    text: str


class DeleteRequest(BaseModel):
    names: List[str]


# Store processing logs
processing_logs = []


async def extract_entities_with_llm(text: str) -> dict:
    """Extract entities using Ollama."""
    import httpx
    
    prompt = f"""Extract family information. Return ONLY valid JSON, no explanation.

Text: {text}

Format: {{"persons": [{{"name": "Full Name", "gender": "M or F", "location": "City or null"}}], "relationships": [{{"person1": "Name1", "person2": "Name2", "type": "spouse or parent_child or sibling"}}]}}

JSON:"""
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3", "prompt": prompt, "stream": False}
            )
            if response.status_code == 200:
                result_text = response.json().get("response", "")
                start = result_text.find("{")
                end = result_text.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(result_text[start:end])
    except Exception as e:
        print(f"LLM error: {e}")
    return {"persons": [], "relationships": []}


async def process_family_text(text: str) -> dict:
    """Process text through MCP pipeline."""
    results = {"steps": [], "persons": [], "relationships": [], "errors": []}
    
    try:
        # Step 1: Detect language via MCP
        lang = await call_nlp_tool("detect_language", {"text": text})
        results["steps"].append({"tool": "detect_language", "input": text[:50], "output": lang})
    except Exception as e:
        results["errors"].append(f"detect_language: {e}")
    
    try:
        # Step 2: Extract with LLM
        extracted = await extract_entities_with_llm(text)
        results["steps"].append({"tool": "llm_extraction", "output": extracted})
    except Exception as e:
        results["errors"].append(f"llm_extraction: {e}")
        extracted = {"persons": [], "relationships": []}
    
    # Step 3: Process persons via MCP
    for p in extracted.get("persons", []):
        name = p.get("name", "")
        if not name:
            continue
        
        try:
            gender = p.get("gender")
            if not gender:
                g = await call_nlp_tool("infer_gender", {"name": name})
                gender = g.get("gender") if g else None
                results["steps"].append({"tool": "infer_gender", "input": name, "output": g})
            
            result = await call_graph_tool("add_person", {
                "name": name, 
                "gender": gender,
                "family_name": p.get("family_name"),
                "location": p.get("location")
            })
            results["persons"].append({"name": name, "result": result})
            results["steps"].append({"tool": "add_person", "input": name, "output": result})
        except Exception as e:
            results["errors"].append(f"add_person({name}): {e}")
    
    # Step 4: Process relationships via MCP
    for rel in extracted.get("relationships", []):
        t = rel.get("type", "").lower()
        p1, p2 = rel.get("person1", ""), rel.get("person2", "")
        if not p1 or not p2:
            continue
        
        try:
            if t == "spouse":
                r = await call_graph_tool("add_spouse", {"person1": p1, "person2": p2})
            elif t == "parent_child":
                r = await call_graph_tool("add_parent_child", {"parent": p1, "child": p2})
            elif t == "sibling":
                r = await call_graph_tool("add_sibling", {"person1": p1, "person2": p2})
            else:
                continue
            results["relationships"].append({"from": p1, "to": p2, "type": t, "result": r})
            results["steps"].append({"tool": f"add_{t}", "input": f"{p1} -> {p2}", "output": r})
        except Exception as e:
            results["errors"].append(f"add_relationship({p1}->{p2}): {e}")
    
    return results


@app.post("/api/process")
async def process_text(req: ProcessRequest):
    try:
        result = await process_family_text(req.text)

        # Store log
        import datetime
        log_entry = {
            "id": len(processing_logs) + 1,
            "timestamp": datetime.datetime.now().isoformat(),
            "input": req.text,
            "result": result
        }
        processing_logs.append(log_entry)

        return {"success": True, "data": result, "log_id": log_entry["id"]}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e), "detail": traceback.format_exc()}


@app.get("/api/persons")
async def get_persons():
    try:
        return await call_graph_tool("get_all_persons", {})
    except Exception as e:
        return {"count": 0, "persons": [], "error": str(e)}


@app.get("/api/relationships")
async def get_relationships():
    try:
        return await call_graph_tool("get_all_relationships", {})
    except Exception as e:
        return {"count": 0, "relationships": [], "error": str(e)}


@app.get("/api/logs")
async def get_logs():
    return {"logs": processing_logs}


@app.delete("/api/logs/{log_id}")
async def delete_log(log_id: int):
    global processing_logs
    processing_logs = [l for l in processing_logs if l["id"] != log_id]
    return {"success": True}


@app.delete("/api/logs")
async def clear_logs():
    global processing_logs
    processing_logs = []
    return {"success": True}


@app.post("/api/persons/delete")
async def delete_persons(req: DeleteRequest):
    """Delete persons by name."""
    from src.graph import FamilyGraph
    graph = FamilyGraph()

    deleted = []
    for name in req.names:
        if graph.get_person(name):
            graph.delete_person(name)
            deleted.append(name)

    return {"success": True, "deleted": deleted}


@app.get("/", response_class=HTMLResponse)
async def index():
    return open("src/ui/static/index.html").read()
