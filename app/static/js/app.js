let cachedHistory = [];

function switchTab(tabName) {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.tab === tabName);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        panel.classList.toggle("active", panel.id === `panel-${tabName}`);
    });
}

async function loadMetrics() {
    try {
        const res = await fetch("/api/v1/metrics");
        if (!res.ok) return;
        const data = await res.json();
        document.getElementById("kpi-total").textContent = data.total_products ?? 0;
        document.getElementById("kpi-anvisa").textContent = data.with_anvisa_alerts ?? 0;
        document.getElementById("kpi-nova4").textContent = data.ultraprocessed_nova4 ?? 0;
        document.getElementById("kpi-nova1").textContent = data.in_natura_nova1 ?? 0;
    } catch (err) {
        console.error("Erro ao carregar métricas:", err);
    }
}

function renderAnvisaSeals(anvisa) {
    const container = document.getElementById("anvisa-seals");
    const note = document.getElementById("anvisa-threshold-note");
    const unit = anvisa.is_beverage ? "100ml (líquidos)" : "100g (sólidos)";
    note.textContent = `Limites para ${unit}: açúcar >= ${anvisa.thresholds_used.sugars_g}g | gord. sat. >= ${anvisa.thresholds_used.saturated_fat_g}g | sódio >= ${anvisa.thresholds_used.sodium_mg}mg`;

    if (!anvisa.warnings_list || anvisa.warnings_list.length === 0) {
        container.innerHTML = `<div class="anvisa-clean">Nenhum limite de alerta frontal excedido (RDC 429/2020)</div>`;
        return;
    }

    container.innerHTML = anvisa.warnings_list
        .map(
            (w) => `
            <div class="anvisa-lupa">
                <span class="anvisa-lupa-icon">LUPA ANVISA</span>
                <span>${w}</span>
            </div>`
        )
        .join("");
}

function renderProduct(prod) {
    document.getElementById("prod-ean").textContent = `EAN ${prod.barcode}`;
    document.getElementById("prod-name").textContent = prod.product_name;
    document.getElementById("prod-meta").textContent = `${prod.brand} • ${prod.quantity} • ${prod.categories}`;
    document.getElementById("prod-unit").textContent = prod.is_beverage ? "Porção base: 100ml" : "Porção base: 100g";

    renderAnvisaSeals(prod.anvisa);

    document.querySelectorAll("#nutriscore-bar .ns-step").forEach((el) => {
        el.classList.toggle("active", el.dataset.grade === prod.nutriscore_grade);
    });

    const novaBadge = document.getElementById("nova-badge");
    novaBadge.textContent = `NOVA ${prod.nova_group}`;
    novaBadge.className = `nova-badge nova-${prod.nova_group}`;
    document.getElementById("nova-label").textContent = prod.nova_label;

    document.getElementById("prod-ingredients").textContent = prod.ingredients_text;

    const allergensEl = document.getElementById("prod-allergens");
    if (prod.allergens && prod.allergens.length > 0) {
        allergensEl.innerHTML = prod.allergens
            .map((a) => `<span class="allergen-tag">Alergênico: ${a}</span>`)
            .join("");
    } else {
        allergensEl.innerHTML = `<span class="threshold-note">Sem alergênicos destacados na base.</span>`;
    }

    const n = prod.nutrition;
    const t = prod.anvisa.thresholds_used;
    const rows = [
        ["Valor energético", `${n.energy_kcal} kcal`, "Referência 2000 kcal/dia"],
        ["Carboidratos", `${n.carbohydrates_g} g`, "Energia glicídica"],
        [
            "Açúcares totais",
            `${n.sugars_g} g`,
            prod.anvisa.high_sugar ? `Acima do limite (${t.sugars_g}g)` : `Abaixo do limite (${t.sugars_g}g)`,
        ],
        ["Gorduras totais", `${n.fat_g} g`, "Lipídios totais"],
        [
            "Gorduras saturadas",
            `${n.saturated_fat_g} g`,
            prod.anvisa.high_saturated_fat
                ? `Acima do limite (${t.saturated_fat_g}g)`
                : `Abaixo do limite (${t.saturated_fat_g}g)`,
        ],
        ["Proteínas", `${n.proteins_g} g`, "Construção muscular"],
        ["Fibras alimentares", `${n.fiber_g} g`, "Recomendado >= 3g"],
        [
            "Sódio",
            `${n.sodium_mg} mg`,
            prod.anvisa.high_sodium ? `Acima do limite (${t.sodium_mg}mg)` : `Abaixo do limite (${t.sodium_mg}mg)`,
        ],
    ];

    document.getElementById("nutrition-tbody").innerHTML = rows
        .map(
            ([label, val, ref]) => `
        <tr>
            <td>${label}</td>
            <td><strong>${val}</strong></td>
            <td class="threshold-note">${ref}</td>
        </tr>`
        )
        .join("");

    const addCount = prod.additives ? prod.additives.length : 0;
    document.getElementById("additives-count-pill").textContent = `${addCount} aditivo(s)`;
    const addList = document.getElementById("additives-list");
    if (addCount === 0) {
        addList.innerHTML = `<div class="anvisa-clean">Nenhum aditivo cosmético, corante ou edulcorante listado.</div>`;
    } else {
        addList.innerHTML = prod.additives
            .map(
                (item) => `
            <div class="additive-item">
                <div>
                    <span class="additive-code">${item.code}</span>
                    <span>${item.name}</span>
                </div>
                <span class="additive-func">${item.function}</span>
            </div>`
            )
            .join("");
    }
}

async function scanProduct(queryOrBarcode) {
    const clean = queryOrBarcode.trim();
    if (!clean) return;

    try {
        let product = null;
        if (/^\d{8,14}$/.test(clean)) {
            const res = await fetch(`/api/v1/product/${encodeURIComponent(clean)}`);
            if (res.ok) {
                product = await res.json();
            }
        }
        if (!product) {
            const sRes = await fetch(`/api/v1/search?q=${encodeURIComponent(clean)}`);
            if (sRes.ok) {
                const list = await sRes.json();
                if (list.length > 0) product = list[0];
            }
        }
        if (product) {
            renderProduct(product);
            await loadMetrics();
            await loadHistory();
        }
    } catch (err) {
        console.error("Falha na consulta:", err);
    }
}

async function loadHistory() {
    try {
        const res = await fetch("/api/v1/history");
        if (!res.ok) return;
        cachedHistory = await res.json();

        const tbody = document.getElementById("history-tbody");
        tbody.innerHTML = cachedHistory
            .map((p) => {
                const alertsText =
                    p.anvisa.warnings_count > 0
                        ? `<span class="text-amber">${p.anvisa.warnings_list.join(", ")}</span>`
                        : `<span class="text-emerald">Sem alertas</span>`;
                return `
                <tr>
                    <td><code>${p.barcode}</code></td>
                    <td><strong>${p.product_name}</strong></td>
                    <td>${p.brand}</td>
                    <td><span class="ns-step ns-${p.nutriscore_grade.toLowerCase()} active" style="padding:2px 8px;display:inline-block;">${p.nutriscore_grade}</span></td>
                    <td><span class="nova-badge nova-${p.nova_group}">NOVA ${p.nova_group}</span></td>
                    <td>${alertsText}</td>
                    <td>${p.nutrition.energy_kcal} kcal</td>
                    <td>${p.nutrition.sugars_g} g</td>
                    <td>${p.nutrition.sodium_mg} mg</td>
                    <td><button class="btn-link" onclick="openFromHistory('${p.barcode}')">Ver ficha</button></td>
                </tr>`;
            })
            .join("");

        populateCompareSelectors();
    } catch (err) {
        console.error("Erro ao carregar histórico:", err);
    }
}

function populateCompareSelectors() {
    const selA = document.getElementById("compare-select-a");
    const selB = document.getElementById("compare-select-b");
    if (!cachedHistory.length) return;

    const currentA = selA.value || "3017620422003";
    const currentB = selB.value || "7891000053508";

    const optionsHtml = cachedHistory
        .map((p) => `<option value="${p.barcode}">${p.product_name} (${p.brand}) [${p.barcode}]</option>`)
        .join("");

    selA.innerHTML = optionsHtml;
    selB.innerHTML = optionsHtml;

    if ([...selA.options].some((o) => o.value === currentA)) selA.value = currentA;
    if ([...selB.options].some((o) => o.value === currentB)) selB.value = currentB;
}

function renderCompareMiniCard(elId, prod) {
    const el = document.getElementById(elId);
    const warnings =
        prod.anvisa.warnings_count > 0
            ? prod.anvisa.warnings_list.map((w) => `<span class="anvisa-lupa" style="font-size:11px;padding:4px 8px;">${w}</span>`).join(" ")
            : `<span class="anvisa-clean">Sem alerta frontal ANVISA</span>`;
    el.innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">
            <div>
                <span class="ean-badge">EAN ${prod.barcode}</span>
                <h3 style="font-size:16px;margin-top:4px;">${prod.product_name}</h3>
                <p class="threshold-note">${prod.brand} • ${prod.quantity}</p>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
                <span class="ns-step ns-${prod.nutriscore_grade.toLowerCase()} active" style="padding:4px 10px;">Nutri-Score ${prod.nutriscore_grade}</span>
                <span class="nova-badge nova-${prod.nova_group}">NOVA ${prod.nova_group}</span>
            </div>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${warnings}</div>
    `;
}

async function runComparison() {
    const codeA = document.getElementById("compare-select-a").value || "3017620422003";
    const codeB = document.getElementById("compare-select-b").value || "7891000053508";

    try {
        const res = await fetch(
            `/api/v1/compare?barcode_a=${encodeURIComponent(codeA)}&barcode_b=${encodeURIComponent(codeB)}`
        );
        if (!res.ok) return;
        const data = await res.json();

        renderCompareMiniCard("comp-card-a", data.product_a);
        renderCompareMiniCard("comp-card-b", data.product_b);

        document.getElementById("th-prod-a").textContent = data.product_a.product_name;
        document.getElementById("th-prod-b").textContent = data.product_b.product_name;

        document.getElementById("compare-deltas-tbody").innerHTML = data.deltas
            .map((d) => {
                const sign = d.diff > 0 ? `+${d.diff}` : `${d.diff}`;
                let favName = "Empate técnico";
                if (d.favorable_barcode === data.product_a.barcode) {
                    favName = `<span class="text-emerald">${data.product_a.product_name}</span>`;
                } else if (d.favorable_barcode === data.product_b.barcode) {
                    favName = `<span class="text-emerald">${data.product_b.product_name}</span>`;
                }
                return `
                <tr>
                    <td><strong>${d.label}</strong></td>
                    <td>${d.value_a} ${d.unit}</td>
                    <td>${d.value_b} ${d.unit}</td>
                    <td><code>${sign} ${d.unit}</code></td>
                    <td>${favName}</td>
                </tr>`;
            })
            .join("");

        document.getElementById("compare-notes").innerHTML = data.summary_notes
            .map((n) => `<div>• ${n}</div>`)
            .join("");
    } catch (err) {
        console.error("Erro na comparação:", err);
    }
}

window.openFromHistory = function (barcode) {
    document.getElementById("barcode-input").value = barcode;
    switchTab("scanner");
    scanProduct(barcode);
};

document.addEventListener("DOMContentLoaded", async () => {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            switchTab(btn.dataset.tab);
            if (btn.dataset.tab === "compare") runComparison();
        });
    });

    document.getElementById("btn-scan").addEventListener("click", () => {
        scanProduct(document.getElementById("barcode-input").value);
    });

    document.getElementById("barcode-input").addEventListener("keydown", (e) => {
        if (e.key === "Enter") scanProduct(e.target.value);
    });

    document.querySelectorAll(".chip-btn").forEach((chip) => {
        chip.addEventListener("click", () => {
            document.querySelectorAll(".chip-btn").forEach((c) => c.classList.remove("active"));
            chip.classList.add("active");
            const code = chip.dataset.barcode;
            document.getElementById("barcode-input").value = code;
            scanProduct(code);
        });
    });

    document.getElementById("btn-run-compare").addEventListener("click", runComparison);

    const params = new URLSearchParams(window.location.search);
    const initialTab = params.get("tab");
    if (initialTab && ["scanner", "compare", "history"].includes(initialTab)) {
        switchTab(initialTab);
    }

    await loadMetrics();
    await loadHistory();
    await scanProduct(document.getElementById("barcode-input").value || "3017620422003");
    await runComparison();
});
