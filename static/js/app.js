// Tab Switching logic using event delegation
document.addEventListener("click", (event) => {
  const btn = event.target.closest(".sidebar-button");
  if (btn) {
    const targetTab = btn.getAttribute("data-tab");
    const tabButtons = document.querySelectorAll(".sidebar-button");
    const tabContents = document.querySelectorAll(".tab-content");

    tabButtons.forEach(b => b.classList.remove("active"));
    tabContents.forEach(c => c.classList.remove("active"));

    btn.classList.add("active");
    const activeContent = document.getElementById(`tab-${targetTab}`);
    if (activeContent) {
      activeContent.classList.add("active");
      // Load rosters when the roster tab is activated
      if (targetTab === "roster") {
        loadRosters();
      }
    }
  }

  // Rankings sub-tab switching
  const rankingsBtn = event.target.closest(".rankings-tab");
  if (rankingsBtn) {
    const targetRankings = rankingsBtn.getAttribute("data-rankings");
    const rankingsButtons = document.querySelectorAll(".rankings-tab");
    const rankingsContents = document.querySelectorAll(".rankings-content");

    rankingsButtons.forEach(b => b.classList.remove("active"));
    rankingsContents.forEach(c => c.classList.remove("active"));

    rankingsBtn.classList.add("active");
    const activeRankings = document.getElementById(`rankings-${targetRankings}`);
    if (activeRankings) {
      activeRankings.classList.add("active");
    }
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const toast = document.querySelector(".toast");
  if (toast) {
    setTimeout(() => toast.remove(), 3500);
  }

  const presentationCheckbox = document.querySelector("#presentation");
  const qaInput = document.querySelector("#presentation_qa");
  if (presentationCheckbox && qaInput) {
    const toggleQa = () => {
      qaInput.disabled = !presentationCheckbox.checked;
      if (!presentationCheckbox.checked) qaInput.value = "0";
    };
    presentationCheckbox.addEventListener("change", toggleQa);
    toggleQa();
  }
});

document.body.addEventListener("htmx:afterSwap", (event) => {
  if (event.detail.target.id === "dashboard-main") {
    const toast = document.querySelector(".toast");
    if (toast) {
      setTimeout(() => toast.remove(), 3500);
    }

    const presentationCheckbox = document.querySelector("#presentation");
    const qaInput = document.querySelector("#presentation_qa");
    if (presentationCheckbox && qaInput) {
      qaInput.disabled = !presentationCheckbox.checked;
    }
  }
});

// Game detail modal
async function showGameDetail(gameDay) {
  const modal = document.getElementById("game-modal");
  const modalContent = document.getElementById("game-modal-content");
  
  if (!modal || !modalContent) {
    console.error("Modal elements not found");
    return;
  }
  
  modalContent.innerHTML = '<div class="loading">Loading game details...</div>';
  modal.style.display = "block";
  
  try {
    const response = await fetch(`/api/game/${gameDay}`);
    if (!response.ok) {
      throw new Error("Failed to load game details");
    }
    
    const data = await response.json();
    renderGameDetail(data, modalContent);
  } catch (error) {
    modalContent.innerHTML = `<div class="error">Error loading game: ${error.message}</div>`;
  }
}

function renderGameDetail(data, container) {
  const game = data.game;
  const matchups = data.matchups;
  
  let html = `
    <div class="game-detail">
      <div class="game-detail__header">
        <h3>Day ${game.day} - ${game.date_submitted}</h3>
        <span class="game-result game-result--${game.result === 'W' ? 'win' : 'loss'}">${game.result}</span>
      </div>
      
      <div class="game-detail__section">
        <h4>Your Performance</h4>
        <div class="box-score-detailed">
          <div class="stat-row"><span class="stat-label">Points:</span><span class="stat-value">${game.box_score.PTS}</span></div>
          <div class="stat-row"><span class="stat-label">Assists:</span><span class="stat-value">${game.box_score.AST}</span></div>
          <div class="stat-row"><span class="stat-label">Rebounds:</span><span class="stat-value">${game.box_score.REB}</span></div>
          <div class="stat-row"><span class="stat-label">Steals:</span><span class="stat-value">${game.box_score.STL}</span></div>
          <div class="stat-row"><span class="stat-label">Blocks:</span><span class="stat-value">${game.box_score.BLK}</span></div>
          <div class="stat-row"><span class="stat-label">Turnovers:</span><span class="stat-value">${game.box_score.TO}</span></div>
        </div>
        <div class="mvp-score">MVP Score: ${game.mvp_score}</div>
        ${game.bonuses ? `<div class="bonuses">${game.bonuses.map(b => `<span class="bonus-tag">${b}</span>`).join(' ')}</div>` : ''}
      </div>
  `;
  
  if (matchups && matchups.length > 0) {
    html += `
      <div class="game-detail__section">
        <h4>League Matchups</h4>
        <div class="matchups-list">
    `;
    
    for (const matchup of matchups) {
      html += `
        <div class="matchup-card">
          <div class="matchup-teams">
            <span class="team-name ${matchup.winner === matchup.team1_name ? 'winner' : ''}">${matchup.team1_name}</span>
            <span class="vs">vs</span>
            <span class="team-name ${matchup.winner === matchup.team2_name ? 'winner' : ''}">${matchup.team2_name}</span>
          </div>
          <div class="matchup-score">
            <span>${matchup.team1_score.toFixed(1)} - ${matchup.team2_score.toFixed(1)}</span>
          </div>
          <div class="matchup-winner">Winner: ${matchup.winner}</div>
      `;
      
      // Render player stats tables for each team
      for (const [teamKey, teamName] of [['team1_players', matchup.team1_name], ['team2_players', matchup.team2_name]]) {
        const players = matchup[teamKey];
        if (players && players.length > 0) {
          html += `
            <div class="matchup-players">
              <div class="matchup-team-name">${teamName}</div>
              <table class="matchup-stats-table">
                <thead>
                  <tr>
                    <th class="matchup-player-name">Player</th>
                    <th class="matchup-stat">PTS</th>
                    <th class="matchup-stat">AST</th>
                    <th class="matchup-stat">REB</th>
                    <th class="matchup-stat">STL</th>
                    <th class="matchup-stat">BLK</th>
                    <th class="matchup-stat">TO</th>
                  </tr>
                </thead>
                <tbody>
          `;
          for (const player of players) {
            const bs = player.box_score;
            html += `
              <tr>
                <td class="matchup-player-name">${player.name}${player.position ? ` - ${player.position}` : ''} (${player.ovr})</td>
                <td class="matchup-stat">${bs?.PTS ?? 0}</td>
                <td class="matchup-stat">${bs?.AST ?? 0}</td>
                <td class="matchup-stat">${bs?.REB ?? 0}</td>
                <td class="matchup-stat">${bs?.STL ?? 0}</td>
                <td class="matchup-stat">${bs?.BLK ?? 0}</td>
                <td class="matchup-stat">${bs?.TO ?? 0}</td>
              </tr>
            `;
          }
          html += `</tbody></table></div>`;
        }
      }
      
      html += `</div>`;
    }
    
    html += `</div></div>`;
  }
  
  html += `</div>`;
  container.innerHTML = html;
}

function closeModal() {
  const modal = document.getElementById("game-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

async function initializeRosters() {
  try {
    const response = await fetch("/api/initialize-rosters", {
      method: "POST",
    });
    
    if (!response.ok) {
      throw new Error("Failed to initialize rosters");
    }
    
    const data = await response.json();
    alert(`Success! Generated rosters for ${data.teams} teams.`);
    location.reload();
  } catch (error) {
    alert(`Error: ${error.message}`);
  }
}

// Close modal when clicking outside
window.onclick = function(event) {
  const modal = document.getElementById("game-modal");
  if (event.target === modal) {
    closeModal();
  }
}

// Load and display rosters
async function loadRosters() {
  const container = document.getElementById("rosters-container");
  if (!container) return;
  
  try {
    const response = await fetch("/api/rosters");
    if (!response.ok) {
      throw new Error("Failed to load rosters");
    }
    
    const rosters = await response.json();
    renderRosters(rosters, container);
  } catch (error) {
    container.innerHTML = `<div class="error">Error loading rosters: ${error.message}</div>`;
  }
}

function renderRosters(rosters, container) {
  if (!rosters || rosters.length === 0) {
    return;
  }
  
  let html = "";
  
  for (const roster of rosters) {
    html += `
      <div class="roster-team">
        <div class="roster-team-header">
          <h3 class="roster-team-name">${roster.team_name}</h3>
          <span class="roster-player-count">${roster.players.length} players</span>
        </div>
        <div class="roster-players-list">
    `;
    
    for (const player of roster.players) {
      html += `
        <div class="roster-player-card">
          <div class="roster-player-header">
            <div>
              <div class="roster-player-name">${player.name}</div>
              <div class="roster-player-position">${player.position}</div>
            </div>
            <div class="roster-player-ovr">${player.ovr}</div>
          </div>
          <div class="roster-player-stats">
            <div class="roster-stat">
              <div class="roster-stat__value">${player.games_played}</div>
              <div class="roster-stat__label">GP</div>
            </div>
            <div class="roster-stat">
              <div class="roster-stat__value">${player.total_pts}</div>
              <div class="roster-stat__label">PTS</div>
            </div>
            <div class="roster-stat">
              <div class="roster-stat__value">${player.total_ast}</div>
              <div class="roster-stat__label">AST</div>
            </div>
            <div class="roster-stat">
              <div class="roster-stat__value">${player.total_reb}</div>
              <div class="roster-stat__label">REB</div>
            </div>
            <div class="roster-stat">
              <div class="roster-stat__value">${player.total_stl}</div>
              <div class="roster-stat__label">STL</div>
            </div>
            <div class="roster-stat">
              <div class="roster-stat__value">${player.total_blk}</div>
              <div class="roster-stat__label">BLK</div>
            </div>
          </div>
          <div class="roster-player-record">
            <span class="record-win">${player.wins}W</span>
            <span class="record-loss">${player.losses}L</span>
          </div>
        </div>
      `;
    }
    
    html += `</div></div>`;
  }
  
  container.innerHTML = html;
}
