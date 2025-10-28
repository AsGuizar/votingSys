from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, List, Set
import json
import hashlib
from datetime import datetime

app = FastAPI()

# Base de datos en memoria
class VotingSystem:
    def __init__(self):
        self.voters: Dict[str, dict] = {}
        self.candidates: List[dict] = [
            {"id": "c1", "name": "Alexandria Ocasio-Cortez", "votes": 0},
            {"id": "c2", "name": "Ron DeSantis", "votes": 0},
            {"id": "c3", "name": "Bernie Sanders", "votes": 0},
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
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Votación Electrónica</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .content { padding: 30px; }
        
        .step {
            display: none;
        }
        .step.active {
            display: block;
            animation: fadeIn 0.3s;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .step-title {
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            text-align: center;
        }
        
        input {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            width: 100%;
            padding: 15px;
            margin: 10px 0;
            border: none;
            border-radius: 10px;
            font-size: 18px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #f0f0f0;
            color: #666;
        }
        
        .btn-small {
            width: auto;
            padding: 8px 15px;
            font-size: 14px;
            margin: 10px 0;
        }
        
        .candidate-card {
            background: #f8f9fa;
            padding: 20px;
            margin: 15px 0;
            border-radius: 12px;
            cursor: pointer;
            border: 3px solid transparent;
            transition: all 0.3s;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .candidate-card:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        .candidate-card.selected {
            border-color: #667eea;
            background: linear-gradient(135deg, #f0f4ff 0%, #e9ecff 100%);
        }
        .candidate-name {
            font-size: 20px;
            font-weight: bold;
            color: #333;
        }
        .vote-badge {
            background: #667eea;
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 16px;
        }
        
        .alert {
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            text-align: center;
            font-weight: 500;
            animation: slideDown 0.3s;
        }
        @keyframes slideDown {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin: 20px 0;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-number {
            font-size: 28px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
        }
        
        .audit-log {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            max-height: 400px;
            overflow-y: auto;
            margin-top: 15px;
        }
        .audit-entry {
            background: white;
            padding: 12px;
            margin: 8px 0;
            border-radius: 8px;
            font-size: 14px;
            border-left: 4px solid #667eea;
        }
        .audit-entry .real-id {
            display: none;
            color: #dc3545;
            font-weight: bold;
            margin-top: 5px;
        }
        .audit-entry.show-real .real-id {
            display: block;
        }
        
        .back-link {
            text-align: center;
            margin-top: 20px;
        }
        .back-link a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗳️ Votación Electrónica</h1>
            <p>Sistema Seguro y Transparente</p>
        </div>
        
        <div class="content">
            <!-- PASO 1: Identificación -->
            <div id="step1" class="step active">
                <div class="step-title">Identificación de Votante</div>
                <input type="text" id="voterId" placeholder="Tu ID (ej: DNI123456)" autocomplete="off">
                <input type="text" id="voterName" placeholder="Tu Nombre Completo" autocomplete="off">
                <button class="btn-primary" onclick="nextStep()">Continuar →</button>
                <div id="identityAlert"></div>
            </div>
            
            <!-- PASO 2: Votación -->
            <div id="step2" class="step">
                <div class="step-title">Selecciona tu Opción</div>
                <div id="candidatesList"></div>
                <button class="btn-primary" onclick="submitVote()">✓ Confirmar Voto</button>
                <button class="btn-secondary" onclick="goBack(1)">← Volver</button>
                <div id="voteAlert"></div>
            </div>
            
            <!-- PASO 3: Confirmación y Resultados -->
            <div id="step3" class="step">
                <div class="step-title">¡Voto Registrado Exitosamente!</div>
                
                <div class="stats">
                    <div class="stat-box">
                        <div class="stat-number" id="totalVotes">0</div>
                        <div class="stat-label">Votos</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="registeredVoters">0</div>
                        <div class="stat-label">Registrados</div>
                    </div>
                    <div class="stat-box">
                        <div class="stat-number" id="participation">0%</div>
                        <div class="stat-label">Participación</div>
                    </div>
                </div>
                
                <div style="margin-top: 30px;">
                    <h3 style="color: #667eea; margin-bottom: 15px;">Resultados en Tiempo Real</h3>
                    <div id="results"></div>
                </div>
                
                <button class="btn-secondary" onclick="showAudit()" style="margin-top: 20px;">Ver Auditoría</button>
                <div class="back-link">
                    <a href="javascript:location.reload()">← Nueva votación</a>
                </div>
            </div>
            
            <!-- PASO 4: Auditoría -->
            <div id="step4" class="step">
                <div class="step-title">Log de Auditoría</div>
                <button class="btn-secondary btn-small" onclick="toggleRealIds()">🔓 Mostrar IDs Reales (Testing)</button>
                <div class="audit-log" id="auditLog"></div>
                <button class="btn-secondary" onclick="goBack(3)">← Volver a Resultados</button>
            </div>
        </div>
    </div>

    <script>
        let ws;
        let currentStep = 1;
        let voterId = '';
        let voterName = '';
        let selectedCandidate = null;
        let showingRealIds = false;
        
        function connect() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);
            
            ws.onmessage = (event) => {
                const message = JSON.parse(event.data);
                
                if (message.type === 'initial_state' || message.type === 'results_update') {
                    updateResults(message.data);
                    displayCandidates(message.data.candidates);
                } else if (message.type === 'register_result') {
                    handleRegisterResult(message.data);
                } else if (message.type === 'vote_result') {
                    handleVoteResult(message.data);
                } else if (message.type === 'audit') {
                    displayAudit(message.data);
                }
            };
            
            ws.onclose = () => setTimeout(connect, 1000);
        }
        
        function showStep(step) {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById('step' + step).classList.add('active');
            currentStep = step;
        }
        
        function nextStep() {
            voterId = document.getElementById('voterId').value.trim();
            voterName = document.getElementById('voterName').value.trim();
            
            if (!voterId || !voterName) {
                showAlert('identityAlert', 'Por favor completa todos los campos', 'error');
                return;
            }
            
            ws.send(JSON.stringify({
                action: 'register',
                voter_id: voterId,
                name: voterName
            }));
        }
        
        function handleRegisterResult(result) {
            if (result.success) {
                showStep(2);
            } else {
                showAlert('identityAlert', result.error, 'error');
            }
        }
        
        function displayCandidates(candidates) {
            const list = document.getElementById('candidatesList');
            list.innerHTML = candidates.map(c => `
                <div class="candidate-card" id="card-${c.id}" onclick="selectCandidate('${c.id}')">
                    <span class="candidate-name">${c.name}</span>
                </div>
            `).join('');
        }
        
        function selectCandidate(id) {
            selectedCandidate = id;
            document.querySelectorAll('.candidate-card').forEach(card => {
                card.classList.remove('selected');
            });
            document.getElementById('card-' + id).classList.add('selected');
        }
        
        function submitVote() {
            if (!selectedCandidate) {
                showAlert('voteAlert', 'Por favor selecciona una opción', 'error');
                return;
            }
            
            ws.send(JSON.stringify({
                action: 'vote',
                voter_id: voterId,
                candidate_id: selectedCandidate
            }));
        }
        
        function handleVoteResult(result) {
            if (result.success) {
                showStep(3);
            } else {
                showAlert('voteAlert', result.error, 'error');
            }
        }
        
        function updateResults(data) {
            document.getElementById('totalVotes').textContent = data.total_votes;
            document.getElementById('registeredVoters').textContent = data.registered_voters;
            const participation = data.registered_voters > 0 
                ? Math.round(data.voters_who_voted / data.registered_voters * 100) 
                : 0;
            document.getElementById('participation').textContent = participation + '%';
            
            const results = document.getElementById('results');
            results.innerHTML = data.candidates.map(c => {
                const percentage = data.total_votes > 0 ? Math.round(c.votes/data.total_votes*100) : 0;
                return `
                    <div class="candidate-card">
                        <span class="candidate-name">${c.name}</span>
                        <span class="vote-badge">${c.votes} (${percentage}%)</span>
                    </div>
                `;
            }).join('');
        }
        
        function showAudit() {
            ws.send(JSON.stringify({ action: 'get_audit' }));
            showStep(4);
        }
        
        function displayAudit(logs) {
            const auditLog = document.getElementById('auditLog');
            if (logs.length === 0) {
                auditLog.innerHTML = '<p style="text-align: center; color: #999;">No hay votos registrados aún</p>';
                return;
            }
            auditLog.innerHTML = logs.map(log => `
                <div class="audit-entry">
                    <strong>Candidato:</strong> ${log.candidate_name}<br>
                    <small>Votante Hash: ${log.hashed_voter} • ${new Date(log.timestamp).toLocaleString()}</small>
                    <div class="real-id">
                        ⚠️ ID Real: ${log.real_voter_id} (${log.voter_name})
                    </div>
                </div>
            `).join('');
        }
        
        function toggleRealIds() {
            showingRealIds = !showingRealIds;
            const entries = document.querySelectorAll('.audit-entry');
            entries.forEach(entry => {
                if (showingRealIds) {
                    entry.classList.add('show-real');
                } else {
                    entry.classList.remove('show-real');
                }
            });
        }
        
        function showAlert(elementId, message, type) {
            const alertDiv = document.getElementById(elementId);
            alertDiv.className = 'alert alert-' + type;
            alertDiv.textContent = message;
            setTimeout(() => alertDiv.innerHTML = '', 3000);
        }
        
        function goBack(step) {
            showStep(step);
        }
        
        connect();
    </script>
</body>
</html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)