// ── Page metadata for sidebar & header ──
const PAGE_META = {
  home: {
    title: "Dashboard",
    subtitle: "Player overview, rivalry, and daily submission",
    sidebar: [
      { label: "Player Profile", target: "section-profile" },
      { label: "Season Summary", target: "section-season" },
      { label: "Rivalry Comparison", target: "section-rivalry" },
      { label: "Submit Day", target: "section-submit" },
    ],
  },
  games: {
    title: "Games",
    subtitle: "Game history and box scores",
    sidebar: [{ label: "Game History", target: null }],
  },
  rankings: {
    title: "Rankings",
    subtitle: "League leaderboards — season and career",
    sidebar: [
      { label: "Season Leaders", action: "rankings-season" },
      { label: "Career Leaders", action: "rankings-career" },
    ],
  },
  standings: {
    title: "Standings",
    subtitle: "Conference standings",
    sidebar: [
      { label: "Eastern Conference", target: "section-east" },
      { label: "Western Conference", target: "section-west" },
    ],
  },
  news: {
    title: "News",
    subtitle: "League news feed",
    sidebar: [{ label: "All News", target: null }],
  },
  roster: {
    title: "Roster",
    subtitle: "League team rosters",
    sidebar: [{ label: "All Teams", target: null }],
  },
  seasons: {
    title: "Seasons",
    subtitle: "Career season history",
    sidebar: [{ label: "Season History", target: null }],
  },
};

let activeTab = "home";

function updatePageHeader(tab) {
  const meta = PAGE_META[tab];
  if (!meta) return;
  const titleEl = document.getElementById("page-title");
  const subtitleEl = document.querySelector(".page-subtitle");
  if (titleEl) titleEl.textContent = meta.title;
  if (subtitleEl) subtitleEl.textContent = meta.subtitle;
}

function renderSidebar(tab) {
  const nav = document.getElementById("sidebar-nav");
  if (!nav) return;
  const meta = PAGE_META[tab];
  if (!meta) return;

  nav.innerHTML = meta.sidebar
    .map((item, i) => {
      const active = i === 0 ? " active" : "";
      if (item.action) {
        return `<button class="sidebar-link${active}" data-action="${item.action}">${item.label}</button>`;
      }
      return `<button class="sidebar-link${active}" data-target="${item.target || ""}">${item.label}</button>`;
    })
    .join("");
}

function switchTab(targetTab) {
  activeTab = targetTab;
  const tabButtons = document.querySelectorAll(".topnav-tab");
  const tabContents = document.querySelectorAll(".tab-content");

  tabButtons.forEach((b) => b.classList.remove("active"));
  tabContents.forEach((c) => c.classList.remove("active"));

  const btn = document.querySelector(`.topnav-tab[data-tab="${targetTab}"]`);
  const content = document.getElementById(`tab-${targetTab}`);

  if (btn) btn.classList.add("active");
  if (content) content.classList.add("active");

  updatePageHeader(targetTab);
  renderSidebar(targetTab);

  const dashboardMain = document.querySelector(".dashboard-main");
  if (dashboardMain) dashboardMain.scrollTop = 0;

  if (targetTab === "roster") loadRosters();
}

function scrollToSection(id) {
  if (!id) return;
  const el = document.getElementById(id);
  if (el) {
    el.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function activateRankingsSubTab(which) {
  const rankingsButtons = document.querySelectorAll(".rankings-tab");
  const rankingsContents = document.querySelectorAll(".rankings-content");

  rankingsButtons.forEach((b) => b.classList.remove("active"));
  rankingsContents.forEach((c) => c.classList.remove("active"));

  const btn = document.querySelector(`.rankings-tab[data-rankings="${which}"]`);
  const content = document.getElementById(`rankings-${which}`);

  if (btn) btn.classList.add("active");
  if (content) content.classList.add("active");

  document.querySelectorAll(".sidebar-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.action === `rankings-${which}`);
  });
}

// ── Event delegation ──
document.addEventListener("click", (event) => {
  const topTab = event.target.closest(".topnav-tab");
  if (topTab) {
    switchTab(topTab.getAttribute("data-tab"));
    return;
  }

  const sidebarLink = event.target.closest(".sidebar-link");
  if (sidebarLink) {
    document.querySelectorAll(".sidebar-link").forEach((l) => l.classList.remove("active"));
    sidebarLink.classList.add("active");

    if (sidebarLink.dataset.action) {
      const action = sidebarLink.dataset.action.replace("rankings-", "");
      activateRankingsSubTab(action);
    } else if (sidebarLink.dataset.target) {
      scrollToSection(sidebarLink.dataset.target);
    }
    return;
  }

  const rankingsBtn = event.target.closest(".rankings-tab");
  if (rankingsBtn) {
    const targetRankings = rankingsBtn.getAttribute("data-rankings");
    activateRankingsSubTab(targetRankings);
  }
});

document.addEventListener("DOMContentLoaded", initApp);

function initSidebarToggle() {
  const toggle = document.getElementById("sidebar-toggle");
  const sidebar = document.getElementById("sidebar");
  if (!toggle || !sidebar) return;

  toggle.replaceWith(toggle.cloneNode(true));
  const freshToggle = document.getElementById("sidebar-toggle");
  freshToggle.addEventListener("click", () => {
    const collapsed = sidebar.classList.toggle("collapsed");
    freshToggle.setAttribute("aria-expanded", String(!collapsed));
  });

  if (window.innerWidth <= 768) {
    sidebar.classList.add("collapsed");
    freshToggle.setAttribute("aria-expanded", "false");
  }
}

function initApp() {
  renderSidebar(activeTab);
  updatePageHeader(activeTab);
  initSidebarToggle();

  const toast = document.querySelector(".toast");
  if (toast) setTimeout(() => toast.remove(), 3500);

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
}

document.body.addEventListener("htmx:afterSwap", (event) => {
  const target = event.detail.target;
  if (target.id === "dashboard-main" || target.tagName === "BODY") {
    initApp();
  }
});

// ── Game detail modal ──
async function showGameDetail(gameDay) {
  const modal = document.getElementById("game-modal");
  const modalContent = document.getElementById("game-modal-content");

  if (!modal || !modalContent) return;

  modalContent.innerHTML = '<div class="loading">Loading game details...</div>';
  modal.style.display = "block";

  try {
    const response = await fetch(`/api/game/${gameDay}`);
    if (!response.ok) throw new Error("Failed to load game details");
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
        <span class="game-result game-result--${game.result === "W" ? "win" : "loss"}">${game.result}</span>
      </div>
      <div class="game-detail__section">
        <h4>Your Performance</h4>
        <div class="box-score-detailed">
          <div class="stat-row"><span class="stat-label">Points</span><span class="stat-value">${game.box_score.PTS}</span></div>
          <div class="stat-row"><span class="stat-label">Assists</span><span class="stat-value">${game.box_score.AST}</span></div>
          <div class="stat-row"><span class="stat-label">Rebounds</span><span class="stat-value">${game.box_score.REB}</span></div>
          <div class="stat-row"><span class="stat-label">Steals</span><span class="stat-value">${game.box_score.STL}</span></div>
          <div class="stat-row"><span class="stat-label">Blocks</span><span class="stat-value">${game.box_score.BLK}</span></div>
          <div class="stat-row"><span class="stat-label">Turnovers</span><span class="stat-value">${game.box_score.TO}</span></div>
        </div>
        <div class="mvp-score">MVP Score: ${game.mvp_score}</div>
        ${game.bonuses ? `<div class="bonuses">${game.bonuses.map((b) => `<span class="bonus-tag">${b}</span>`).join("")}</div>` : ""}
      </div>
  `;

  if (matchups && matchups.length > 0) {
    html += `<div class="game-detail__section"><h4>League Matchups</h4><div class="matchups-list">`;

    for (const matchup of matchups) {
      html += `
        <div class="matchup-card">
          <div class="matchup-teams">
            <span class="team-name ${matchup.winner === matchup.team1_name ? "winner" : ""}">${matchup.team1_name}</span>
            <span class="vs">vs</span>
            <span class="team-name ${matchup.winner === matchup.team2_name ? "winner" : ""}">${matchup.team2_name}</span>
          </div>
          <div class="matchup-score">${matchup.team1_score.toFixed(1)} - ${matchup.team2_score.toFixed(1)}</div>
          <div class="matchup-winner">Winner: ${matchup.winner}</div>
      `;

      for (const [teamKey, teamName] of [
        ["team1_players", matchup.team1_name],
        ["team2_players", matchup.team2_name],
      ]) {
        const players = matchup[teamKey];
        if (players && players.length > 0) {
          html += `<div class="matchup-players"><div class="matchup-team-name" style="font-size:0.7rem;font-weight:600;margin:0.35rem 0 0.2rem;">${teamName}</div>
            <table class="matchup-stats-table"><thead><tr>
              <th>Player</th><th>PTS</th><th>AST</th><th>REB</th><th>STL</th><th>BLK</th><th>TO</th>
            </tr></thead><tbody>`;
          for (const player of players) {
            const bs = player.box_score;
            html += `<tr>
              <td class="matchup-player-name">${player.name}${player.position ? ` - ${player.position}` : ""} (${player.ovr})</td>
              <td class="matchup-stat">${bs?.PTS ?? 0}</td>
              <td class="matchup-stat">${bs?.AST ?? 0}</td>
              <td class="matchup-stat">${bs?.REB ?? 0}</td>
              <td class="matchup-stat">${bs?.STL ?? 0}</td>
              <td class="matchup-stat">${bs?.BLK ?? 0}</td>
              <td class="matchup-stat">${bs?.TO ?? 0}</td>
            </tr>`;
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
  if (modal) modal.style.display = "none";
}

window.onclick = function (event) {
  const modal = document.getElementById("game-modal");
  if (event.target === modal) closeModal();
};

// ── Rosters ──
async function loadRosters() {
  const container = document.getElementById("rosters-container");
  if (!container) return;

  try {
    const response = await fetch("/api/rosters");
    if (!response.ok) throw new Error("Failed to load rosters");
    const rosters = await response.json();
    renderRosters(rosters, container);
  } catch (error) {
    container.innerHTML = `<div class="error">Error loading rosters: ${error.message}</div>`;
  }
}

function renderRosters(rosters, container) {
  if (!rosters || rosters.length === 0) return;

  let html = "";

  for (const roster of rosters) {
    html += `
      <div class="roster-team">
        <div class="roster-team-header">
          <h3 class="roster-team-name">${roster.team_name}</h3>
          <span class="roster-player-count">${roster.players.length} players</span>
        </div>
        <div class="roster-players-list">`;

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
            <div class="roster-stat"><div class="roster-stat__value">${player.games_played}</div><div class="roster-stat__label">GP</div></div>
            <div class="roster-stat"><div class="roster-stat__value">${player.total_pts}</div><div class="roster-stat__label">PTS</div></div>
            <div class="roster-stat"><div class="roster-stat__value">${player.total_ast}</div><div class="roster-stat__label">AST</div></div>
            <div class="roster-stat"><div class="roster-stat__value">${player.total_reb}</div><div class="roster-stat__label">REB</div></div>
            <div class="roster-stat"><div class="roster-stat__value">${player.total_stl}</div><div class="roster-stat__label">STL</div></div>
            <div class="roster-stat"><div class="roster-stat__value">${player.total_blk}</div><div class="roster-stat__label">BLK</div></div>
          </div>
          <div class="roster-player-record">
            <span class="record-win">${player.wins}W</span>
            <span class="record-loss">${player.losses}L</span>
          </div>
        </div>`;
    }

    html += `</div></div>`;
  }

  container.innerHTML = html;
}
