from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, List, Set
import json
import hashlib
from datetime import datetime

app = FastAPI()

# Servir archivos estáticos desde la carpeta `static`
app.mount("/static", StaticFiles(directory="static"), name="static")

# Base de datos en memoria
class VotingSystem:
    def __init__(self):
        self.voters: Dict[str, dict] = {}
        self.candidates: List[dict] = [
            {
                "id": "c1", 
                "name": "Alexandria Ocasio-Cortez", 
                "votes": 0,
                "party": "Partido Demócrata",
                "image": "/static/images/aoc.jpg"
            },
            {
                "id": "c2", 
                "name": "Ron DeSantis", 
                "votes": 0,
                "party": "Partido Republicano",
                "image": "/static/images/desantis.jpg"
            },
            {
                "id": "c3", 
                "name": "Bernie Sanders", 
                "votes": 0,
                "party": "Independiente",
                "image": "/static/images/sanders.jpg"
            },
        ]
        self.vote_log: List[dict] = []
        self.active_connections: Set[WebSocket] = set()
    
    def register_voter(self, voter_id: str, name: str) -> dict:
        if voter_id in self.voters:
            return {"success": False, "error": "Votante ya registrado"}
        
        hashed_id = hashlib.sha256(voter_id.encode()).hexdigest()[:16]
        self.voters[voter_id] = {
            "name": name,
            "voted": False,
            "hashed_id": hashed_id,
            "timestamp": None
        }
        return {"success": True, "message": "Registrado exitosamente"}
    
    def cast_vote(self, voter_id: str, candidate_id: str) -> dict:
        if voter_id not in self.voters:
            return {"success": False, "error": "Votante no registrado"}
        
        if self.voters[voter_id]["voted"]:
            return {"success": False, "error": "Ya has votado"}
        
        candidate = next((c for c in self.candidates if c["id"] == candidate_id), None)
        if not candidate:
            return {"success": False, "error": "Candidato inválido"}
        
        candidate["votes"] += 1
        self.voters[voter_id]["voted"] = True
        self.voters[voter_id]["timestamp"] = datetime.now().isoformat()
        
        # Log de auditoría con ID hasheado y real
        self.vote_log.append({
            "hashed_voter": self.voters[voter_id]["hashed_id"],
            "real_voter_id": voter_id,
            "voter_name": self.voters[voter_id]["name"],
            "candidate_id": candidate_id,
            "candidate_name": candidate["name"],
            "timestamp": datetime.now().isoformat()
        })
        
        return {"success": True, "message": "¡Voto registrado!"}
    
    def get_results(self) -> dict:
        total_votes = sum(c["votes"] for c in self.candidates)
        return {
            "candidates": self.candidates,
            "total_votes": total_votes,
            "registered_voters": len(self.voters),
            "voters_who_voted": sum(1 for v in self.voters.values() if v["voted"])
        }
    
    def get_audit_log(self) -> List[dict]:
        return self.vote_log

voting_system = VotingSystem()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    voting_system.active_connections.add(websocket)
    
    try:
        await websocket.send_json({
            "type": "initial_state",
            "data": voting_system.get_results()
        })
        
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            if action == "register":
                result = voting_system.register_voter(
                    data.get("voter_id"),
                    data.get("name")
                )
                await websocket.send_json({"type": "register_result", "data": result})
            
            elif action == "vote":
                result = voting_system.cast_vote(
                    data.get("voter_id"),
                    data.get("candidate_id")
                )
                await websocket.send_json({"type": "vote_result", "data": result})
                
                if result["success"]:
                    results = voting_system.get_results()
                    for conn in voting_system.active_connections:
                        try:
                            await conn.send_json({
                                "type": "results_update",
                                "data": results
                            })
                        except:
                            pass
            
            elif action == "get_audit":
                audit = voting_system.get_audit_log()
                await websocket.send_json({"type": "audit", "data": audit})
    
    except WebSocketDisconnect:
        voting_system.active_connections.remove(websocket)

@app.get("/")
async def get():
    # Servir el HTML principal desde el directorio static (archivo index.html)
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)