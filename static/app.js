let ws;
let voterId = '';
let voterName = '';
let selectedCandidate = null;
let showingRealIds = false;

function connect() {
  ws = new WebSocket(`ws://${window.location.host}/ws`);

  ws.onopen = () => {
    updateConnectionStatus(true);
  };

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

  ws.onclose = () => {
    updateConnectionStatus(false);
    setTimeout(connect, 1000);
  };

  ws.onerror = () => {
    updateConnectionStatus(false);
  };
}

function updateConnectionStatus(connected) {
  const statusEl = document.getElementById('connectionStatus');
  if (!statusEl) return;
  
  const indicator = statusEl.querySelector('.status-indicator');
  const text = statusEl.querySelector('.status-text');
  
  if (connected) {
    indicator.style.background = '#22c55e';
    text.textContent = 'Conectado';
  } else {
    indicator.style.background = '#ef4444';
    text.textContent = 'Desconectado';
  }
}

function showPanel(panelId) {
  // Ocultar todos los paneles
  const panels = ['panelIdentity', 'panelVote', 'panelResults', 'panelAudit'];
  panels.forEach(id => {
    const panel = document.getElementById(id);
    if (panel) panel.hidden = (id !== panelId);
  });
}

function nextStep() {
  voterId = document.getElementById('voterId').value.trim();
  voterName = document.getElementById('voterName').value.trim();

  if (!voterId || !voterName) {
    showAlert('identityAlert', '⚠️ Por favor completa todos los campos', 'error');
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
    showPanel('panelVote');
  } else {
    showAlert('identityAlert', '❌ ' + result.error, 'error');
  }
}

function displayCandidates(candidates) {
  const list = document.getElementById('candidatesList');
  if (!list) return;
  
  console.log('Displaying candidates:', candidates); // Debug
  
  list.innerHTML = candidates.map(c => {
    const initials = c.name.split(' ')
      .map(p => p[0])
      .slice(0, 2)
      .join('')
      .toUpperCase();
    
    // Mostrar imagen si existe, sino iniciales
    let avatarContent;
    if (c.image) {
      console.log('Image for', c.name, ':', c.image); // Debug
      avatarContent = `<img src="${c.image}" alt="${c.name}" class="candidate-image">`;
    } else {
      avatarContent = `<div class="candidate-initials">${initials}</div>`;
    }
    
    return `
      <div class="candidate-card" 
           id="card-${c.id}" 
           onclick="selectCandidate('${c.id}')" 
           role="radio" 
           aria-checked="false"
           tabindex="0">
        <div class="candidate-avatar">${avatarContent}</div>
        <div class="candidate-info">
          <div class="candidate-name">${c.name}</div>
          <div class="candidate-party">${c.party || 'ID: ' + c.id}</div>
        </div>
        <div class="vote-count">${c.votes} votos</div>
      </div>
    `;
  }).join('');
}

function selectCandidate(id) {
  selectedCandidate = id;
  
  document.querySelectorAll('.candidate-card').forEach(card => {
    card.classList.remove('selected');
    card.setAttribute('aria-checked', 'false');
  });
  
  const selectedCard = document.getElementById('card-' + id);
  if (selectedCard) {
    selectedCard.classList.add('selected');
    selectedCard.setAttribute('aria-checked', 'true');
  }
}

function submitVote() {
  if (!selectedCandidate) {
    showAlert('voteAlert', '⚠️ Por favor selecciona un candidato', 'error');
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
    showPanel('panelResults');
  } else {
    showAlert('voteAlert', '❌ ' + result.error, 'error');
  }
}

function updateResults(data) {
  // Actualizar estadísticas
  const totalVotesEl = document.getElementById('totalVotes');
  const registeredVotersEl = document.getElementById('registeredVoters');
  const participationEl = document.getElementById('participation');
  
  if (totalVotesEl) totalVotesEl.textContent = data.total_votes;
  if (registeredVotersEl) registeredVotersEl.textContent = data.registered_voters;
  
  const participation = data.registered_voters > 0 
    ? Math.round((data.voters_who_voted / data.registered_voters) * 100) 
    : 0;
  if (participationEl) participationEl.textContent = participation + '%';

  // Actualizar lista de resultados con barras
  const resultsEl = document.getElementById('results');
  if (!resultsEl) return;
  
  resultsEl.innerHTML = data.candidates.map(c => {
    const percentage = data.total_votes > 0 
      ? Math.round((c.votes / data.total_votes) * 100) 
      : 0;
    
    return `
      <div class="result-card">
        <div class="result-header">
          <div class="result-name">${c.name}</div>
          <div class="result-votes">${c.votes} votos (${percentage}%)</div>
        </div>
        <div class="result-bar">
          <div class="result-fill" style="width: ${percentage}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function showAudit() {
  ws.send(JSON.stringify({ action: 'get_audit' }));
  showPanel('panelAudit');
}

function displayAudit(logs) {
  const auditLog = document.getElementById('auditLog');
  if (!auditLog) return;
  
  if (logs.length === 0) {
    auditLog.innerHTML = '<p style="text-align: center; color: var(--text-tertiary); padding: 2rem;">No hay votos registrados aún</p>';
    return;
  }
  
  auditLog.innerHTML = logs.map(log => `
    <div class="audit-entry">
      <strong>📋 Candidato:</strong> ${log.candidate_name}<br>
      <small>🔐 Hash: ${log.hashed_voter} • 🕐 ${new Date(log.timestamp).toLocaleString()}</small>
      <div class="real-id">
        ⚠️ ID Real: ${log.real_voter_id} (${log.voter_name})
      </div>
    </div>
  `).join('');
}

function toggleRealIds() {
  showingRealIds = !showingRealIds;
  
  document.querySelectorAll('.audit-entry').forEach(entry => {
    entry.classList.toggle('show-real', showingRealIds);
  });
  
  const toggleText = document.getElementById('toggleText');
  if (toggleText) {
    toggleText.textContent = showingRealIds 
      ? 'Ocultar IDs Reales' 
      : 'Mostrar IDs Reales';
  }
}

function showAlert(elementId, message, type) {
  const alertDiv = document.getElementById(elementId);
  if (!alertDiv) return;
  
  alertDiv.className = `alert ${type} show`;
  alertDiv.textContent = message;
  
  setTimeout(() => {
    alertDiv.classList.remove('show');
  }, 4000);
}

// Event listeners
window.addEventListener('load', () => {
  // Panel de identidad
  document.getElementById('btnContinue')?.addEventListener('click', nextStep);
  
  // Panel de votación
  document.getElementById('btnConfirm')?.addEventListener('click', submitVote);
  document.getElementById('btnBack1')?.addEventListener('click', () => showPanel('panelIdentity'));
  
  // Panel de resultados
  document.getElementById('btnAudit')?.addEventListener('click', showAudit);
  
  // Panel de auditoría
  document.getElementById('btnToggleIds')?.addEventListener('click', toggleRealIds);
  document.getElementById('btnBack3')?.addEventListener('click', () => showPanel('panelResults'));
  
  // Mostrar panel inicial y conectar WebSocket
  showPanel('panelIdentity');
  connect();
});
