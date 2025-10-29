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
  if (!list) return;
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
  const el = document.getElementById('card-' + id);
  if (el) el.classList.add('selected');
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
  const totalVotesEl = document.getElementById('totalVotes');
  const registeredVotersEl = document.getElementById('registeredVoters');
  const participationEl = document.getElementById('participation');
  if (totalVotesEl) totalVotesEl.textContent = data.total_votes;
  if (registeredVotersEl) registeredVotersEl.textContent = data.registered_voters;
  const participation = data.registered_voters > 0 
    ? Math.round(data.voters_who_voted / data.registered_voters * 100) 
    : 0;
  if (participationEl) participationEl.textContent = participation + '%';

  const results = document.getElementById('results');
  if (!results) return;
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
  if (!auditLog) return;
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
  if (!alertDiv) return;
  alertDiv.className = 'alert alert-' + type;
  alertDiv.textContent = message;
  setTimeout(() => alertDiv.innerHTML = '', 3000);
}

function goBack(step) {
  showStep(step);
}

// Event bindings
window.addEventListener('load', () => {
  document.getElementById('btnContinue')?.addEventListener('click', nextStep);
  document.getElementById('btnConfirm')?.addEventListener('click', submitVote);
  document.getElementById('btnBack1')?.addEventListener('click', () => goBack(1));
  document.getElementById('btnAudit')?.addEventListener('click', showAudit);
  document.getElementById('btnToggleIds')?.addEventListener('click', toggleRealIds);
  document.getElementById('btnBack3')?.addEventListener('click', () => goBack(3));
  connect();
});
