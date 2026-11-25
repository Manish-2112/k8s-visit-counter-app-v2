const visitCountEl = document.getElementById("visit-count");
const podNameEl = document.getElementById("pod-name");
const envBadgeEl = document.getElementById("env-badge");
const verBadgeEl = document.getElementById("ver-badge");
const notesListEl = document.getElementById("notes-list");
const noteForm = document.getElementById("note-form");
const statusMsg = document.getElementById("status-msg");
const refreshBtn = document.getElementById("refresh-btn");

async function loadVisits() {
  try {
    const res = await fetch("/api/visits");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    visitCountEl.textContent = data.total_visits;
    podNameEl.textContent = data.served_by_pod;
    envBadgeEl.textContent = data.environment;
    verBadgeEl.textContent = data.version || "v2.0.0";
    renderNotes(data.recent_notes);
  } catch (err) {
    visitCountEl.textContent = "ERR";
    podNameEl.textContent = "Backend unreachable";
    console.error(err);
  }
}

function renderNotes(notes) {
  if (!notes || notes.length === 0) {
    notesListEl.innerHTML = '<li class="empty">No notes yet. Be the first!</li>';
    return;
  }
  notesListEl.innerHTML = notes
    .map(
      (n) => `
      <li class="note-item">
        <div class="note-meta">
          <span class="note-author">${escapeHtml(n.visitor_name)}</span>
          <span>Pod: ${escapeHtml(n.served_by_pod)} | ${escapeHtml(n.created_at)}</span>
        </div>
        <div>${escapeHtml(n.message)}</div>
      </li>`
    )
    .join("");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

noteForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusMsg.textContent = "Saving...";
  const visitor_name = document.getElementById("visitor-name").value;
  const message = document.getElementById("visitor-message").value;

  try {
    const res = await fetch("/api/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_name, message }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    noteForm.reset();
    statusMsg.textContent = "Note saved to PostgreSQL StatefulSet!";
    await loadVisits();
  } catch (err) {
    statusMsg.textContent = "Failed to save note.";
    console.error(err);
  }
});

refreshBtn.addEventListener("click", loadVisits);
loadVisits();
