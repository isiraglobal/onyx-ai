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

    // Initial load
    loadMemories();
});
