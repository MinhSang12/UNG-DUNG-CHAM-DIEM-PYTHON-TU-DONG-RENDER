/**
 * DSA Grader — Results Page Logic V3
 * Hien thi ket qua cham diem voi rubric dong tu ngan hang bai tap.
 */

// ═══════════════════════════════════════════
//  State
// ═══════════════════════════════════════════
let allResults = [];
let statusFilter = "all";
let searchKeyword = "";

// ═══════════════════════════════════════════
//  Init
// ═══════════════════════════════════════════
document.addEventListener("DOMContentLoaded", () => {
  const raw = sessionStorage.getItem("gradingResults");
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      allResults = parsed.results || [];
      renderSummary(parsed.summary || {});
    } catch (e) {
      console.error("Parse error:", e);
    }
  }
  renderResults();
  bindFilters();
});

// ═══════════════════════════════════════════
//  Summary Dashboard
// ═══════════════════════════════════════════
function renderSummary(summary) {
  const section = document.getElementById("summary-section");
  if (!section || !summary.total_files) return;

  section.innerHTML = `
    <div class="dev-stat-item">
      <div class="dev-stat-label">Tong so bai</div>
      <div class="dev-stat-value">${summary.total_files || 0}</div>
    </div>
    <div class="dev-stat-item">
      <div class="dev-stat-label">Diem trung binh</div>
      <div class="dev-stat-value">${summary.avg_score != null ? summary.avg_score : "—"}</div>
    </div>
    <div class="dev-stat-item">
      <div class="dev-stat-label">Thoi gian xu ly</div>
      <div class="dev-stat-value">${summary.total_time || "—"}</div>
    </div>
    <div class="dev-stat-item">
      <div class="dev-stat-label">Da luu</div>
      <div class="dev-stat-value">${summary.saved_to_db || 0} bai</div>
    </div>
  `;
}

// ═══════════════════════════════════════════
//  Render Result Cards
// ═══════════════════════════════════════════
function renderResults() {
  const container = document.getElementById("results-container");
  if (!container) return;

  let filtered = allResults;

  if (statusFilter !== "all") {
    filtered = filtered.filter(
      (r) => (r.status || "").toUpperCase() === statusFilter.toUpperCase()
    );
  }

  if (searchKeyword) {
    const kw = searchKeyword.toLowerCase();
    filtered = filtered.filter(
      (r) =>
        (r.filename || "").toLowerCase().includes(kw) ||
        (r.algorithms || "").toLowerCase().includes(kw)
    );
  }

  if (!filtered.length) {
    container.innerHTML = `
      <div style="text-align:center; padding:3rem; color:var(--text-muted);">
        <i class="fa-solid fa-inbox" style="font-size:2rem; margin-bottom:1rem; display:block;"></i>
        <p>Chua co ket qua nao.</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map((r, i) => buildCard(r, i)).join("");
}

// ═══════════════════════════════════════════
//  Card Builder
// ═══════════════════════════════════════════
function buildCard(r, index = 0) {
  const card = document.createElement("div");
  card.className = "pipeline-card";
  card.style.animation = `fadeInUp 0.4s ease forwards`;
  card.style.animationDelay = `${index * 0.08}s`;
  card.style.opacity = "0";

  const hasRubric = r.has_rubric === true;
  const totalScore = r.total_score;
  const hasScore = totalScore != null && hasRubric;

  const st = getStatusInfo(r.status, hasScore);
  const scoreColor = hasScore
    ? totalScore >= 80 ? "var(--brand-success)" : totalScore >= 50 ? "var(--brand-warning)" : "var(--brand-danger)"
    : "var(--text-muted)";

  const scoreDisplay = hasScore ? totalScore : "—";
  const filename = (r.filename || "unknown").split(" | ").pop() || r.filename;
  const student = (r.filename || "").includes(" | ") ? r.filename.split(" | ")[0] : "Khong ro";

  // --- PHẦN MỚI: HIỂN THỊ CHI TIẾT TIÊU CHÍ ---
  const criteriaHtml = r.criteria_results && r.criteria_results.length > 0 
    ? `
    <div style="margin-bottom:1.5rem;">
        <h4 style="font-size:0.95rem; font-weight:600; color:var(--text-bright); margin-bottom:0.75rem; display:flex; align-items:center;">
            <i class="fa-solid fa-list-check" style="margin-right:8px; color:var(--brand-primary)"></i>
            Kết quả theo tiêu chí (Rubric)
        </h4>
        <div style="display:grid; gap:0.6rem;">
            ${r.criteria_results.map(c => `
                <div style="background:var(--bg-app); border:1px solid var(--border-pro); border-left:4px solid ${c.score > 0 ? 'var(--brand-success)' : 'var(--brand-danger)'}; padding:0.85rem; border-radius:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:5px;">
                        <strong style="font-size:0.85rem; color:var(--text-bright); line-height:1.4;">${c.criterion}</strong>
                        <span style="font-family:var(--font-code); font-weight:700; color:${c.score > 0 ? 'var(--brand-success)' : 'var(--brand-danger)'}; font-size:0.9rem; margin-left:10px;">
                            ${c.score}đ
                        </span>
                    </div>
                    <p style="font-size:0.82rem; color:var(--text-muted); margin:0; line-height:1.5;">
                        <i class="fa-solid ${c.score > 0 ? 'fa-check-circle' : 'fa-circle-xmark'}" style="margin-right:6px; color:${c.score > 0 ? 'var(--brand-success)' : 'var(--brand-danger)'}"></i>
                        ${c.reason}
                    </p>
                </div>
            `).join('')}
        </div>
    </div>
    ` : '';

  card.innerHTML = `
    <div class="pipeline-header" onclick="this.parentElement.classList.toggle('expanded')">
        <div style="display:flex; align-items:center; gap:1rem; flex:1; min-width:0;">
          <span class="pipeline-status ${st.cls}"><i class="fa-solid ${st.icon}"></i>${st.text}</span>
          <div style="display:flex; flex-direction:column; min-width:0;">
            <span style="font-weight:600; color:var(--text-bright); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${filename}</span>
            <span style="font-size:0.8rem; color:var(--text-muted);"><i class="fa-regular fa-user" style="margin-right:4px;"></i>${student}</span>
          </div>
        </div>
        <div style="display:flex; align-items:center; gap:2rem; margin-left:auto;">
          <div style="text-align:right;"><div style="font-size:0.8rem; color:var(--text-muted);">Diem so</div><div style="font-family:var(--font-code); font-size:1.1rem; font-weight:700; color:${scoreColor};">${scoreDisplay}/10</div></div>
          <i class="fa-solid fa-chevron-down pipeline-toggle-icon"></i>
        </div>
    </div>

   
    <div class="pipeline-body">
    <div style="width:220px; flex-shrink:0; padding-right:1rem; border-right:1px solid var(--border-pro);">
        <div class="score-display">
            <div class="score-box-dev" style="border-color:${scoreColor};">
                <div class="val" style="color:${scoreColor};">${scoreDisplay}</div>
                <div class="max">/ 10 điểm</div>
            </div>

            <div style="display:grid; gap:8px; margin-top:15px;">
                ${(r.criteria_results || []).map(c => 
                    buildScoreRow(c.criterion, c.score, c.max_score || (10 / (r.criteria_results.length || 1)).toFixed(0))
                ).join('')}
            </div>
            </div>
    </div>

    <div style="flex:1; min-width:0; padding-left:1.5rem;">
        
        ${r.strengths || r.weaknesses ? `
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:0.75rem; margin-bottom:1.5rem;">
            ${r.strengths ? `<div style="background:rgba(34,197,94,0.06); border:1px solid rgba(34,197,94,0.15); padding:0.75rem; border-radius:8px;"><h5 style="font-size:0.8rem; color:var(--brand-success); margin-bottom:5px;">Điểm mạnh</h5><p style="font-size:0.82rem; line-height:1.5; margin:0;">${r.strengths}</p></div>` : ''}
            ${r.weaknesses ? `<div style="background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.15); padding:0.75rem; border-radius:8px;"><h5 style="font-size:0.8rem; color:var(--brand-danger); margin-bottom:5px;">Cần cải thiện</h5><p style="font-size:0.82rem; line-height:1.5; margin:0;">${r.weaknesses}</p></div>` : ''}
        </div>` : ''}

        <div style="margin-bottom:1.5rem;">
            <h4 style="font-size:0.95rem; font-weight:600; color:var(--text-bright); margin-bottom:0.75rem; display:flex; align-items:center;">
                <i class="fa-solid fa-comment-dots" style="margin-right:8px; color:${scoreColor}"></i> Đánh giá chi tiết
            </h4>
            <div class="feedback-log" style="border-left:3px solid ${scoreColor}; background:var(--bg-app); border-radius: 0 8px 8px 0;">
                <p style="white-space:pre-line; margin:0; font-size:0.9rem;">${r.reasoning || "AI đang tổng hợp đánh giá..."}</p>
            </div>
        </div>

        ${r.improvement ? `
        <div style="margin-bottom:1rem;">
            <h4 style="font-size:0.95rem; font-weight:600; color:var(--text-bright); margin-bottom:0.75rem; display:flex; align-items:center;">
                <i class="fa-solid fa-lightbulb" style="margin-right:8px; color:var(--brand-primary)"></i> Gợi ý nâng cấp
            </h4>
            <div class="feedback-log" style="border-left:3px solid var(--brand-primary); background:var(--bg-app); border-radius: 0 8px 8px 0;">
                <p style="white-space:pre-line; margin:0; font-size:0.9rem;">${r.improvement}</p>
            </div>
        </div>` : ''}
    </div>
</div>
  `;
  return card.outerHTML;
}

// ═══════════════════════════════════════════
//  Helpers
// ═══════════════════════════════════════════
function getStatusInfo(status, hasScore) {
  if (!hasScore) {
    return { cls: "status-pending", icon: "fa-clock", text: "Chua cap nhat" };
  }
  switch ((status || "").toUpperCase()) {
    case "PASS": return { cls: "status-ac", icon: "fa-circle-check", text: "Dat" };
    case "FAIL": return { cls: "status-wa", icon: "fa-circle-xmark", text: "Chua dat" };
    case "FLAG": return { cls: "status-fl", icon: "fa-flag", text: "Nghi van" };
    default: return { cls: "status-pending", icon: "fa-clock", text: "Cho xu ly" };
  }
}

/* --- Sửa trong results.js (image_cdadd4.jpg) --- */
function buildScoreRow(label, value, max) {
  if (value == null) return '';
  
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  const color = pct >= 80 ? "var(--brand-success)" : 
                pct >= 50 ? "var(--brand-warning)" : "var(--brand-danger)";

  return `
    <div style="background:var(--bg-input); padding:0.6rem; border-radius:6px; border:1px solid var(--border-pro); margin-bottom:8px;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:6px;">
        <span style="font-size:0.75rem; color:var(--text-main); line-height:1.3; flex:1;">${label}</span>
        
        <span style="font-size:0.75rem; font-weight:700; color:${color}; background:rgba(255,255,255,0.03); padding:2px 6px; border-radius:4px; border:1px solid ${color}; white-space:nowrap;">
          ${value}/${max}
        </span>
      </div>
      <div style="height:3px; background:var(--border-pro); border-radius:99px; overflow:hidden;">
        <div style="height:100%; width:${pct}%; background:${color}; border-radius:99px;"></div>
      </div>
    </div>
  `;
}

function bindFilters() {
  document.getElementById("status-filter").addEventListener("change", (e) => {
    statusFilter = e.target.value;
    renderResults();
  });
  document.getElementById("search-filter").addEventListener("input", (e) => {
    searchKeyword = e.target.value.trim();
    renderResults();
  });
}
