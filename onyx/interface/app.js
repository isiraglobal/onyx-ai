document.addEventListener("DOMContentLoaded", () => {
    // --- Navigation Tabs ---
    const navItems = document.querySelectorAll(".nav-item");
    const tabPanes = document.querySelectorAll(".tab-pane");

    navItems.forEach(btn => {
        btn.addEventListener("click", () => {
            navItems.forEach(b => b.classList.remove("active"));
            tabPanes.forEach(p => p.classList.remove("active"));
            btn.classList.add("active");
            const targetId = `tab-${btn.getAttribute("data-tab")}`;
            const targetPane = document.getElementById(targetId);
            if (targetPane) targetPane.classList.add("active");
        });
    });

    // --- System Status Polling ---
    async function updateSystemHealth() {
        try {
            const res = await fetch("/api/v1/system/health");
            if (res.ok) {
                const data = await res.json();
                document.getElementById("lbl-model").innerText = data.active_model || "None";
                document.getElementById("lbl-records").innerText = `${data.memory_records_count} items`;
                const hw = data.hardware;
                document.getElementById("lbl-hw").innerText = `${hw.architecture} (${hw.cpu_cores}C, ${hw.ram_gb}GB)`;
                const hwRaw = document.getElementById("hw-raw");
                if (hwRaw) hwRaw.innerText = JSON.stringify(hw, null, 2);
            }
        } catch (e) {
            console.error("Health check error:", e);
        }
    }
    updateSystemHealth();
    setInterval(updateSystemHealth, 10000);

    // --- Chat System ---
    const chatLog = document.getElementById("chat-log");
    const chatInput = document.getElementById("chat-input");
    const btnSend = document.getElementById("btn-send");

    async function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;
        chatInput.value = "";

        // Append User Bubble
        const userDiv = document.createElement("div");
        userDiv.className = "message user";
        userDiv.innerText = text;
        chatLog.appendChild(userDiv);
        chatLog.scrollTop = chatLog.scrollHeight;

        // Create Assistant Bubble
        const asstDiv = document.createElement("div");
        asstDiv.className = "message assistant";
        asstDiv.innerHTML = "<em>Thinking and executing...</em>";
        chatLog.appendChild(asstDiv);
        chatLog.scrollTop = chatLog.scrollHeight;

        try {
            const resp = await fetch("/api/v1/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });

            if (resp.ok) {
                const data = await resp.json();
                asstDiv.innerText = data.response;
            } else {
                asstDiv.innerText = `Error: ${resp.statusText}`;
            }
        } catch (err) {
            asstDiv.innerText = `Connection failed: ${err.message}`;
        }
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    btnSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    // --- Memory Manager ---
    const memoryGrid = document.getElementById("memory-grid");
    const memSearch = document.getElementById("mem-search");
    const memCatSelect = document.getElementById("mem-cat-select");
    const btnRefreshMemory = document.getElementById("btn-refresh-memory");

    async function loadMemories() {
        if (!memoryGrid) return;
        const query = memSearch.value.trim();
        const cat = memCatSelect.value;
        let url = `/api/v1/memory?limit=30`;
        if (query) url += `&query=${encodeURIComponent(query)}`;
        if (cat) url += `&category=${encodeURIComponent(cat)}`;

        try {
            const res = await fetch(url);
            if (res.ok) {
                const items = await res.json();
                memoryGrid.innerHTML = "";
                if (items.length === 0) {
                    memoryGrid.innerHTML = "<p style='color: var(--text-muted);'>No matching memory records found.</p>";
                    return;
                }

                items.forEach(item => {
                    const rec = item.record || item;
                    const card = document.createElement("div");
                    card.className = "card";
                    card.innerHTML = `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
                            <span class="badge" style="background:#30363d;">${rec.category}</span>
                            <small style="color: var(--text-muted);">${new Date(rec.created_at * 1000).toLocaleTimeString()}</small>
                        </div>
                        <p style="color: var(--text-heading); font-size: 0.95rem; margin-bottom: 8px;">${rec.content}</p>
                        <small style="color: var(--text-muted);">Source: ${rec.source}</small>
                    `;
                    memoryGrid.appendChild(card);
                });
            }
        } catch (e) {
            console.error("Load memories failed:", e);
        }
    }

    if (btnRefreshMemory) btnRefreshMemory.addEventListener("click", loadMemories);
    if (memSearch) memSearch.addEventListener("input", () => {
        clearTimeout(window._memSearchDebounce);
        window._memSearchDebounce = setTimeout(loadMemories, 300);
    });
    if (memCatSelect) memCatSelect.addEventListener("change", loadMemories);

    // --- Document Ingestion ---
    const btnIngest = document.getElementById("btn-ingest");
    const ingestPath = document.getElementById("ingest-path");
    const ingestStatus = document.getElementById("ingest-status");

    if (btnIngest) {
        btnIngest.addEventListener("click", async () => {
            const path = ingestPath.value.trim();
            if (!path) return;
            ingestStatus.innerText = "Ingesting and chunking document...";
            try {
                const res = await fetch("/api/v1/learning/ingest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file_path: path, category: "knowledge" })
                });
                if (res.ok) {
                    const data = await res.json();
                    ingestStatus.innerText = `Ingestion complete! Created ${data.chunks_count} indexed chunks.`;
                    updateSystemHealth();
                } else {
                    const err = await res.json();
                    ingestStatus.innerText = `Ingestion error: ${err.detail || res.statusText}`;
                }
            } catch (err) {
                ingestStatus.innerText = `Request failed: ${err.message}`;
            }
        });
    }

    // --- Benchmark Model ---
    const btnBenchmark = document.getElementById("btn-benchmark");
    if (btnBenchmark) {
        btnBenchmark.addEventListener("click", async () => {
            btnBenchmark.disabled = true;
            btnBenchmark.innerText = "Benchmarking...";
            try {
                const res = await fetch("/api/v1/models/benchmark", { method: "POST" });
                if (res.ok) {
                    const data = await res.json();
                    alert(`Benchmark Complete:\n- TTFT: ${data.ttft_seconds}s\n- Throughput: ${data.tokens_per_second} tokens/sec\n- Total Time: ${data.total_seconds}s`);
                }
            } catch (e) {
                alert(`Benchmark failed: ${e.message}`);
            } finally {
                btnBenchmark.disabled = false;
                btnBenchmark.innerText = "Run Benchmark";
            }
        });
    }

    // --- QLA Deal-Making Dashboard Logic ---
    const btnLoadBriefing = document.getElementById("btn-load-briefing");
    if (btnLoadBriefing) {
        btnLoadBriefing.addEventListener("click", async () => {
            const out = document.getElementById("qla-briefing-text");
            out.innerText = "Retrieving morning battle orders...";
            try {
                const res = await fetch("/api/v1/qla/briefing");
                if (res.ok) {
                    const data = await res.json();
                    let text = `${data.greeting}\n\nTOP 5 CRITICAL ACTIONS:\n`;
                    data.top_5_critical_actions_today.forEach(a => text += `• ${a}\n`);
                    text += `\nMANDATE: ${data.core_mandate}`;
                    out.innerText = text;
                }
            } catch (e) {
                out.innerText = `Error loading briefing: ${e.message}`;
            }
        });
    }

    const btnRefreshPipeline = document.getElementById("btn-refresh-pipeline");
    if (btnRefreshPipeline) {
        const loadPipeline = async () => {
            const stats = document.getElementById("qla-pipeline-stats");
            const list = document.getElementById("qla-deals-list");
            stats.innerText = "Loading pipeline...";
            try {
                const res = await fetch("/api/v1/qla/pipeline");
                if (res.ok) {
                    const data = await res.json();
                    stats.innerText = `${data.summary.total_active_opportunities} Active Targets | Pipeline Value: $${(data.summary.total_pipeline_value || 0).toLocaleString()}`;
                    list.innerHTML = "";
                    if (!data.deals || data.deals.length === 0) {
                        list.innerHTML = "<p style='color:#64748b'>No deals added yet. Add via chat or API.</p>";
                    } else {
                        data.deals.forEach(d => {
                            const item = document.createElement("div");
                            item.style = "padding: 6px; border-bottom: 1px solid #334155;";
                            item.innerHTML = `<strong>${d.company_name}</strong> (${d.industry}) — <span style="color:#10b981">$${d.revenue.toLocaleString()} Rev</span> / <span style="color:#f59e0b">$${d.ebitda.toLocaleString()} EBITDA</span> | Stage: <em>${d.status}</em><br><small style="color:#94a3b8">Next: ${d.next_action || 'None'}</small>`;
                            list.appendChild(item);
                        });
                    }
                }
            } catch (e) {
                stats.innerText = `Error: ${e.message}`;
            }
        };
        btnRefreshPipeline.addEventListener("click", loadPipeline);
        setTimeout(loadPipeline, 1000);
    }

    const btnWeakestDeal = document.getElementById("btn-weakest-deal");
    if (btnWeakestDeal) {
        btnWeakestDeal.addEventListener("click", async () => {
            try {
                const res = await fetch("/api/v1/qla/deals/weakest");
                if (res.ok) {
                    const data = await res.json();
                    if (!data.weakest_deal) {
                        alert("No active deals found to evaluate.");
                    } else {
                        const d = data.weakest_deal;
                        alert(`WEAKEST DEAL IDENTIFIED:\n${d.company_name} (${d.industry})\nFlaw Score: ${d.flaw_score}\nIssues:\n• ` + d.reasons.join("\n• "));
                    }
                }
            } catch (e) {
                alert(`Error: ${e.message}`);
            }
        });
    }

    const btnCheckDreamTeam = document.getElementById("btn-check-dream-team");
    if (btnCheckDreamTeam) {
        btnCheckDreamTeam.addEventListener("click", async () => {
            const statusDiv = document.getElementById("qla-dream-team-status");
            statusDiv.innerText = "Auditing Dream Team readiness...";
            try {
                const res = await fetch("/api/v1/qla/dream-team");
                if (res.ok) {
                    const data = await res.json();
                    const r = data.readiness;
                    let text = `Readiness Score: ${r.readiness_score_pct}%\nVerdict: ${r.verdict}\nMissing Mandatory Roles: ${r.missing_mandatory_roles.join(", ") || "None!"}`;
                    statusDiv.innerText = text;
                }
            } catch (e) {
                statusDiv.innerText = `Error: ${e.message}`;
            }
        });
    }

    const btnCalcLBO = document.getElementById("btn-calc-lbo");
    if (btnCalcLBO) {
        btnCalcLBO.addEventListener("click", async () => {
            const price = parseFloat(document.getElementById("calc-price").value) || 0;
            const ebitda = parseFloat(document.getElementById("calc-ebitda").value) || 0;
            const out = document.getElementById("qla-lbo-output");
            out.innerText = "Modeling LBO capital structure...";
            try {
                const res = await fetch("/api/v1/qla/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ mode: "lbo_model", purchase_price: price, ebitda: ebitda, seller_note_pct: 0.25 })
                });
                if (res.ok) {
                    const json = await res.json();
                    const d = json.results;
                    out.innerText = `Valuation Multiple: ${d.implied_valuation_multiple}x EBITDA\n` +
                        `Senior Commercial Debt: $${d.senior_debt.toLocaleString()} (${d.senior_debt_pct}%)\n` +
                        `Seller Financing Note: $${d.seller_note.toLocaleString()} (${d.seller_note_pct}%)\n` +
                        `Equity / OPM Gap: $${d.equity_opm_required.toLocaleString()} (${d.equity_pct}%)\n` +
                        `Base DSCR: ${d.base_dscr}x [${d.dscr_verdict}]\n` +
                        `Stress Test (-20% EBITDA): ${d.downside_stress_tests.ebitda_down_20pct.stressed_dscr}x (${d.downside_stress_tests.ebitda_down_20pct.solvency_verdict})`;
                }
            } catch (e) {
                out.innerText = `Calculation error: ${e.message}`;
            }
        });
    }

    const btnRunBogusAudit = document.getElementById("btn-run-bogus-audit");
    if (btnRunBogusAudit) {
        btnRunBogusAudit.addEventListener("click", async () => {
            const out = document.getElementById("qla-bogus-output");
            out.innerText = "Auditing financial verification flags...";
            try {
                const res = await fetch("/api/v1/qla/analyze", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        mode: "bogus_books_audit",
                        revenue: 4000000,
                        has_tax_returns: false,
                        largest_customer_pct: 35.0,
                        top_3_customers_pct: 65.0,
                        owner_actively_runs_daily_ops: true,
                        years_of_financial_records: 2
                    })
                });
                if (res.ok) {
                    const json = await res.json();
                    const r = json.results;
                    out.innerHTML = `<strong style="color:${r.risk_rating === 'CRITICAL RISK' ? '#ef4444' : '#10b981'}">Score: ${r.bogus_books_risk_score}/100 [${r.risk_rating}]</strong><br>` +
                        `<strong>Recommendation:</strong> ${r.recommendation}<br>` +
                        `<strong>Red Flags:</strong><br>• ${r.red_flags.join('<br>• ') || 'None'}`;
                }
            } catch (e) {
                out.innerText = `Audit error: ${e.message}`;
            }
        });
    }

    // Directives buttons (trigger chat with pre-filled directive)
    document.querySelectorAll(".btn-directive").forEach(btn => {
        btn.addEventListener("click", () => {
            const prompt = btn.getAttribute("data-prompt");
            const chatNav = document.querySelector(".nav-item[data-tab='chat']");
            if (chatNav) chatNav.click();
            const input = document.getElementById("chat-input");
            if (input) {
                input.value = prompt;
                const sendBtn = document.getElementById("btn-send");
                if (sendBtn) sendBtn.click();
            }
        });
    });

    // Initial load
    loadMemories();
});
