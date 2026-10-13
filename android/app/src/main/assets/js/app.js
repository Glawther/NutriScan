let cachedHistory = [];
let currentDietSummary = null;
let currentOcrResult = null;
let currentScannedProduct = null;
let currentSampleId = "rotulo_whey";
let uploadedFileObj = null;

// Native Android Bridge Helpers (Haptic feedback & Share via NutriScanNative)
window.triggerHaptic = function (durationMs = 40) {
    if (window.NutriScanNative && typeof window.NutriScanNative.vibrate === "function") {
        try {
            window.NutriScanNative.vibrate(durationMs);
            return;
        } catch (_) {}
    }
    if (navigator.vibrate) {
        try {
            navigator.vibrate(durationMs);
        } catch (_) {}
    }
};

window.shareNutriScanText = function (title, text) {
    if (window.NutriScanNative && typeof window.NutriScanNative.shareText === "function") {
        try {
            window.NutriScanNative.shareText(title, text);
            return;
        } catch (_) {}
    }
    if (navigator.share) {
        navigator.share({ title, text }).catch(() => {});
    }
};

const IS_FILE_PROTOCOL = typeof window !== "undefined" && window.location && window.location.protocol === "file:";
const ASSET_BASE = IS_FILE_PROTOCOL ? "samples" : "/static/samples";

const OFFLINE_SAMPLES = {
    rotulo_whey: {
        sample_id: "rotulo_whey",
        product_name: "Whey Protein Concentrado 80%",
        portion_label_g: 30,
        default_consumed_g: 45,
        image_url: `${ASSET_BASE}/rotulo_whey.png`,
        raw_text:
            "INFORMAÇÃO NUTRICIONAL\nProduto: Whey Protein Concentrado 80%\nPorção de 30g (2 dosadores)\nValor energético: 120 kcal\nCarboidratos: 3,2 g\nAçúcares totais: 2,1 g\nAçúcares adicionados: 0,0 g\nProteínas: 24,0 g\nGorduras totais: 1,8 g\nGorduras saturadas: 1,0 g\nFibra alimentar: 0,0 g\nSódio: 55 mg",
    },
    rotulo_pasta_amendoim: {
        sample_id: "rotulo_pasta_amendoim",
        product_name: "Pasta de Amendoim Integral Torrado",
        portion_label_g: 20,
        default_consumed_g: 30,
        image_url: `${ASSET_BASE}/rotulo_pasta_amendoim.png`,
        raw_text:
            "INFORMAÇÃO NUTRICIONAL\nProduto: Pasta de Amendoim Integral Torrado\nPorção de 20g (1 colher de sopa)\nValor energético: 121 kcal\nCarboidratos: 3,4 g\nAçúcares totais: 0,9 g\nProteínas: 5,8 g\nGorduras totais: 9,8 g\nGorduras saturadas: 1,4 g\nFibra alimentar: 1,6 g\nSódio: 2 mg",
    },
    rotulo_pao_integral: {
        sample_id: "rotulo_pao_integral",
        product_name: "Pão de Forma 100% Integral com Grãos",
        portion_label_g: 50,
        default_consumed_g: 50,
        image_url: `${ASSET_BASE}/rotulo_pao_integral.png`,
        raw_text:
            "INFORMAÇÃO NUTRICIONAL\nProduto: Pão de Forma 100% Integral com Grãos\nPorção de 50g (2 fatias)\nValor energético: 118 kcal\nCarboidratos: 19,0 g\nAçúcares totais: 1,5 g\nProteínas: 6,2 g\nGorduras totais: 1,8 g\nGorduras saturadas: 0,4 g\nFibra alimentar: 4,2 g\nSódio: 195 mg",
    },
    rotulo_iogurte_proteico: {
        sample_id: "rotulo_iogurte_proteico",
        product_name: "Iogurte Desnatado Proteico 15g",
        portion_label_g: 160,
        default_consumed_g: 160,
        image_url: `${ASSET_BASE}/rotulo_iogurte_proteico.png`,
        raw_text:
            "INFORMAÇÃO NUTRICIONAL\nProduto: Iogurte Desnatado Proteico 15g\nPorção de 160g (1 pote)\nValor energético: 96 kcal\nCarboidratos: 6,4 g\nAçúcares totais: 4,8 g\nProteínas: 15,0 g\nGorduras totais: 0,5 g\nGorduras saturadas: 0,3 g\nFibra alimentar: 0,0 g\nSódio: 72 mg",
    },
};

const OFFLINE_CATALOG = [
    {
        barcode: "3017620422003",
        product_name: "Creme de Avelã com Cacau Nutella",
        brand: "Ferrero",
        quantity: "350g",
        categories: "Cremes de avelã e cacau",
        is_beverage: false,
        nutriscore_grade: "E",
        nova_group: 4,
        nova_label: "Ultraprocessado",
        ingredients_text: "Açúcar, óleo de palma, avelãs (13%), leite desnatado em pó (8,7%), cacau magro (7,4%), emulsificante lecitinas (soja), vanilina.",
        allergens: ["Leite e derivados", "Castanhas / nozes / avelãs", "Soja"],
        additives: [{ code: "E322", name: "Lecitina de soja", function: "Emulsificante" }],
        nutrition: { energy_kcal: 539, carbohydrates_g: 57.5, sugars_g: 56.3, fat_g: 30.9, saturated_fat_g: 10.6, proteins_g: 6.3, fiber_g: 3.4, sodium_mg: 42 },
        anvisa: { is_beverage: false, high_sugar: true, high_saturated_fat: true, high_sodium: false, warnings_count: 2, warnings_list: ["ALTO EM AÇÚCAR", "ALTO EM GORDURA SATURADA"], thresholds_used: { sugars_g: 15, saturated_fat_g: 6, sodium_mg: 600 } }
    },
    {
        barcode: "7891000053508",
        product_name: "Aveia em Flocos Finos Integral",
        brand: "Quaker",
        quantity: "165g",
        categories: "Cereais matinais, Aveia em flocos",
        is_beverage: false,
        nutriscore_grade: "A",
        nova_group: 1,
        nova_label: "In natura ou minimamente processado",
        ingredients_text: "Aveia em flocos finos 100% integral.",
        allergens: ["Glúten", "Aveia"],
        additives: [],
        nutrition: { energy_kcal: 346, carbohydrates_g: 57.0, sugars_g: 1.0, fat_g: 7.3, saturated_fat_g: 1.5, proteins_g: 14.3, fiber_g: 9.1, sodium_mg: 0 },
        anvisa: { is_beverage: false, high_sugar: false, high_saturated_fat: false, high_sodium: false, warnings_count: 0, warnings_list: [], thresholds_used: { sugars_g: 15, saturated_fat_g: 6, sodium_mg: 600 } }
    },
    {
        barcode: "7891025101604",
        product_name: "Iogurte Natural Integral (2 Ingredientes)",
        brand: "Danone",
        quantity: "170g",
        categories: "Laticínios, Iogurtes naturais",
        is_beverage: false,
        nutriscore_grade: "A",
        nova_group: 1,
        nova_label: "In natura ou minimamente processado",
        ingredients_text: "Leite integral e fermento lácteo.",
        allergens: ["Leite e derivados"],
        additives: [],
        nutrition: { energy_kcal: 62, carbohydrates_g: 4.8, sugars_g: 4.8, fat_g: 3.2, saturated_fat_g: 2.1, proteins_g: 4.1, fiber_g: 0, sodium_mg: 52 },
        anvisa: { is_beverage: false, high_sugar: false, high_saturated_fat: false, high_sodium: false, warnings_count: 0, warnings_list: [], thresholds_used: { sugars_g: 15, saturated_fat_g: 6, sodium_mg: 600 } }
    }
];

function switchTab(rawTabName) {
    if (typeof window.triggerHaptic === "function") window.triggerHaptic(25);
    const tabName = rawTabName === "compare" ? "comparar" : rawTabName;
    document.querySelectorAll(".tab-btn").forEach((btn) => {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
        btn.setAttribute("tabindex", isActive ? "0" : "-1");
    });
    document.querySelectorAll(".mob-nav-btn").forEach((btn) => {
        const isActive = btn.dataset.tab === tabName;
        btn.classList.toggle("active", isActive);
        btn.setAttribute("aria-selected", isActive ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
        const isActive = panel.id === `panel-${tabName}`;
        panel.classList.toggle("active", isActive);
        panel.hidden = !isActive;
    });
}
window.switchTab = switchTab;

function getLocalDietData() {
    const saved = localStorage.getItem("nutriscan_diet_state_v1");
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (_) {}
    }
    const initial = {
        goals: {
            goal_type: "cutting",
            weight_kg: 78,
            height_cm: 176,
            age: 29,
            activity_level: "moderado",
            daily_kcal_limit: 2000,
            carbs_limit_g: 200,
            proteins_limit_g: 150,
            fat_limit_g: 65,
            sodium_limit_mg: 2000,
            water_goal_ml: 2730,
        },
        entries: [],
    };
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(initial));
    return initial;
}

/**
 * NutriScan Profile Management (Mifflin-St Jeor + Macro distribution)
 */
function calculateMifflinStJeor(gender, weightKg, heightCm, age, activityLevel, goalType) {
    const weight = Number(weightKg) || 70;
    const height = Number(heightCm) || 170;
    const ageNum = Number(age) || 25;
    const isMale = String(gender).toLowerCase() === "masculino" || String(gender).toLowerCase() === "m";

    // TMB Mifflin-St Jeor
    // TMB Masculino: 10 * weight + 6.25 * height - 5 * age + 5
    // TMB Feminino: 10 * weight + 6.25 * height - 5 * age - 161
    const tmb = isMale
        ? 10 * weight + 6.25 * height - 5 * ageNum + 5
        : 10 * weight + 6.25 * height - 5 * ageNum - 161;

    // Fatores de atividade
    const activityFactors = {
        sedentario: 1.2,
        leve: 1.375,
        moderado: 1.55,
        intenso: 1.725,
    };
    const actFactor = activityFactors[String(activityLevel).toLowerCase()] || 1.2;
    const tdee = tmb * actFactor;

    // Ajustes de objetivo: cutting: -400 kcal, manutencao: 0 kcal, bulking: +350 kcal
    const goalNorm = String(goalType).toLowerCase();
    let goalAdjustment = 0;
    if (goalNorm === "cutting") {
        goalAdjustment = -400;
    } else if (goalNorm === "bulking") {
        goalAdjustment = 350;
    } else {
        goalAdjustment = 0;
    }

    const dailyKcalLimit = Math.max(1000, Math.round(tdee + goalAdjustment));

    // Macros:
    // Proteína: 2.0 g/kg para cutting/bulking, 1.6 g/kg para manutenção
    const isCuttingOrBulking = goalNorm === "cutting" || goalNorm === "bulking";
    const proteinFactor = isCuttingOrBulking ? 2.0 : 1.6;
    const proteinsLimitG = Math.round(weight * proteinFactor);

    // Gordura: 0.8 g/kg
    const fatLimitG = Math.round(weight * 0.8);

    // Carboidratos: calorias restantes / 4 (onde cal restantes = dailyKcalLimit - (prot * 4 + fat * 9))
    const proteinCalories = proteinsLimitG * 4;
    const fatCalories = fatLimitG * 9;
    const remainingCalories = dailyKcalLimit - (proteinCalories + fatCalories);
    const carbsLimitG = Math.max(0, Math.round(remainingCalories / 4));

    // Água: round(weightKg * 35) ml
    const waterGoalMl = Math.round(weight * 35);

    return {
        tmb: Math.round(tmb),
        tdee: Math.round(tdee),
        daily_kcal_limit: dailyKcalLimit,
        proteins_limit_g: proteinsLimitG,
        carbs_limit_g: carbsLimitG,
        fat_limit_g: fatLimitG,
        water_goal_ml: waterGoalMl,
        sodium_limit_mg: 2000,
    };
}

function getUserProfile() {
    try {
        const stored = localStorage.getItem("nutriscan_user_profile_v1");
        return stored ? JSON.parse(stored) : null;
    } catch (_) {
        return null;
    }
}

async function resetAllUserData() {
    // Clears all meals and water for today, resetting entries: [], water to 0 ml
    try {
        await fetch(`/api/v1/diet/water?date=${currentDietDate}`, { method: "DELETE" });
    } catch (_) {}

    const state = getLocalDietData();
    state.entries = [];
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(state));

    try {
        localStorage.setItem(`nutriscan_water_${currentDietDate}`, "0");
    } catch (_) {}

    renderDietToday(buildOfflineSummary(state));
    renderWater({ amount_ml: 0, goal_ml: (state.goals && state.goals.water_goal_ml) || 2500, pct: 0 });
}

async function saveUserProfile(profileData) {
    // Saves to localStorage
    localStorage.setItem("nutriscan_user_profile_v1", JSON.stringify(profileData));

    // Calculate goals based on profile
    const calculatedGoals = calculateMifflinStJeor(
        profileData.gender,
        profileData.weight_kg,
        profileData.height_cm,
        profileData.age,
        profileData.activity_level,
        profileData.goal_type
    );

    const goalsPayload = {
        goal_type: profileData.goal_type,
        activity_level: profileData.activity_level,
        weight_kg: Number(profileData.weight_kg),
        height_cm: Number(profileData.height_cm),
        age: Number(profileData.age),
        auto_calculate: true,
        daily_kcal_limit: calculatedGoals.daily_kcal_limit,
        proteins_limit_g: calculatedGoals.proteins_limit_g,
        carbs_limit_g: calculatedGoals.carbs_limit_g,
        fat_limit_g: calculatedGoals.fat_limit_g,
        sodium_limit_mg: calculatedGoals.sodium_limit_mg || 2000,
        water_goal_ml: calculatedGoals.water_goal_ml,
    };

    // Update goals in diet state and sync to API/localStorage
    try {
        await fetch("/api/v1/diet/goals", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(goalsPayload),
        });
    } catch (_) {}

    // Resets daily entries to [] and water to 0 so the app starts 100% clean
    const state = getLocalDietData();
    state.goals = goalsPayload;
    state.entries = [];
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(state));

    try {
        await fetch(`/api/v1/diet/water?date=${currentDietDate}`, { method: "DELETE" });
    } catch (_) {}
    try {
        localStorage.setItem(`nutriscan_water_${currentDietDate}`, "0");
    } catch (_) {}

    renderDietToday(buildOfflineSummary(state));
    renderWater({ amount_ml: 0, goal_ml: calculatedGoals.water_goal_ml || 2500, pct: 0 });

    // Update greeting if name provided
    updateUserGreeting();

    // Dispatches custom event nutriscan:profile-saved and starts tour if available
    window.dispatchEvent(new CustomEvent("nutriscan:profile-saved", { detail: profileData }));
    if (window.NutriScanTour && typeof window.NutriScanTour.startTour === "function") {
        window.NutriScanTour.startTour(true);
    }
}

function updateUserGreeting() {
    if (typeof document === "undefined") return;
    const profile = getUserProfile();
    const greetingEl = document.getElementById("user-greeting-text");
    if (!greetingEl) return;
    if (profile && profile.name && profile.name.trim()) {
        greetingEl.textContent = `Olá, ${profile.name.trim()}!`;
    } else {
        greetingEl.textContent = "Olá! Seja bem-vindo";
    }
}

const NutriScanProfile = {
    calculateMifflinStJeor,
    getUserProfile,
    saveUserProfile,
    resetAllUserData,
    updateUserGreeting,
};
window.NutriScanProfile = NutriScanProfile;

function buildOfflineSummary(state) {
    const g = state.goals;
    const entries = state.entries || [];
    const consumed = {
        kcal: Number(entries.reduce((s, e) => s + Number(e.kcal || 0), 0).toFixed(1)),
        carbohydrates_g: Number(entries.reduce((s, e) => s + Number(e.carbohydrates_g || 0), 0).toFixed(1)),
        proteins_g: Number(entries.reduce((s, e) => s + Number(e.proteins_g || 0), 0).toFixed(1)),
        fat_g: Number(entries.reduce((s, e) => s + Number(e.fat_g || 0), 0).toFixed(1)),
        fiber_g: Number(entries.reduce((s, e) => s + Number(e.fiber_g || 0), 0).toFixed(1)),
        sodium_mg: Number(entries.reduce((s, e) => s + Number(e.sodium_mg || 0), 0).toFixed(1)),
    };
    const remaining = {
        kcal: Number((g.daily_kcal_limit - consumed.kcal).toFixed(1)),
        carbohydrates_g: Number((g.carbs_limit_g - consumed.carbohydrates_g).toFixed(1)),
        proteins_g: Number((g.proteins_limit_g - consumed.proteins_g).toFixed(1)),
        fat_g: Number((g.fat_limit_g - consumed.fat_g).toFixed(1)),
        sodium_mg: Number((g.sodium_limit_mg - consumed.sodium_mg).toFixed(1)),
    };
    const pct = (val, lim) => (lim > 0 ? Number(((val / lim) * 100).toFixed(1)) : 0);
    const within = consumed.kcal <= g.daily_kcal_limit;
    return {
        goals: g,
        consumed,
        remaining,
        percentages: {
            kcal: pct(consumed.kcal, g.daily_kcal_limit),
            carbohydrates_g: pct(consumed.carbohydrates_g, g.carbs_limit_g),
            proteins_g: pct(consumed.proteins_g, g.proteins_limit_g),
            fat_g: pct(consumed.fat_g, g.fat_limit_g),
            sodium_mg: pct(consumed.sodium_mg, g.sodium_limit_mg),
        },
        within_kcal_limit: within,
        status_label: within
            ? `Dentro do limite diário (restam ${Math.round(remaining.kcal)} kcal)`
            : `Limite diário excedido em ${Math.round(Math.abs(remaining.kcal))} kcal`,
        entries,
    };
}

function renderDietToday(summary) {
    currentDietSummary = summary;
    if (typeof document === "undefined") return;
    const g = summary.goals;
    const c = summary.consumed;
    const r = summary.remaining;
    const p = summary.percentages;

    document.getElementById("top-kcal-consumed").textContent = Math.round(c.kcal);
    document.getElementById("top-kcal-limit").textContent = Math.round(g.daily_kcal_limit);
    const badge = document.getElementById("top-kcal-badge");
    if (summary.within_kcal_limit) {
        badge.textContent = `Restam ${Math.round(r.kcal)} kcal`;
        badge.className = "status-pill";
    } else {
        badge.textContent = `+${Math.round(Math.abs(r.kcal))} kcal acima`;
        badge.className = "status-pill exceeded";
    }
    document.getElementById("top-bar-kcal").style.width = `${Math.min(100, p.kcal)}%`;

    document.getElementById("top-prot-consumed").textContent = `${c.proteins_g}g`;
    document.getElementById("top-prot-limit").textContent = Math.round(g.proteins_limit_g);
    document.getElementById("top-prot-pct").textContent = `${Math.round(p.proteins_g)}%`;
    document.getElementById("top-bar-prot").style.width = `${Math.min(100, p.proteins_g)}%`;

    document.getElementById("top-carb-consumed").textContent = `${c.carbohydrates_g}g`;
    document.getElementById("top-carb-limit").textContent = Math.round(g.carbs_limit_g);
    document.getElementById("top-carb-pct").textContent = `${Math.round(p.carbohydrates_g)}%`;
    document.getElementById("top-bar-carb").style.width = `${Math.min(100, p.carbohydrates_g)}%`;

    document.getElementById("top-fat-consumed").textContent = `${c.fat_g}g`;
    document.getElementById("top-fat-limit").textContent = Math.round(g.fat_limit_g);
    document.getElementById("top-fat-pct").textContent = `${Math.round(p.fat_g)}%`;
    document.getElementById("top-bar-fat").style.width = `${Math.min(100, p.fat_g)}%`;

    document.getElementById("diet-status-subtitle").textContent =
        `${summary.status_label} • Sódio hoje: ${Math.round(c.sodium_mg)} / ${Math.round(g.sodium_limit_mg)} mg • Fibras: ${c.fiber_g}g`;

    // Preencher campos de meta
    document.getElementById("goal-type").value = g.goal_type || "cutting";
    document.getElementById("goal-activity").value = g.activity_level || "moderado";
    document.getElementById("goal-weight").value = g.weight_kg || 78;
    document.getElementById("goal-height").value = g.height_cm || 176;
    document.getElementById("goal-age").value = g.age || 29;
    document.getElementById("limit-kcal").value = Math.round(g.daily_kcal_limit);
    document.getElementById("limit-prot").value = Math.round(g.proteins_limit_g);
    document.getElementById("limit-carb").value = Math.round(g.carbs_limit_g);
    document.getElementById("limit-fat").value = Math.round(g.fat_limit_g);
    document.getElementById("limit-sodium").value = Math.round(g.sodium_limit_mg);

    const sourceNames = {
        foto_ficha: "Foto da ficha",
        codigo_barras: "Código EAN",
        manual: "Manual",
    };

    const tbody = document.getElementById("diary-tbody");
    if (!summary.entries || summary.entries.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="threshold-note">Nenhuma refeição registrada hoje. Adicione abaixo ou leia uma ficha técnica por foto.</td></tr>`;
        return;
    }

    const rowsHtml = summary.entries
        .map((e) => {
            const srcLabel = sourceNames[e.source_type] || "Registro";
            return `
            <tr>
                <td><span class="meal-badge">${e.meal_type}</span></td>
                <td>
                    <strong>${e.product_name}</strong>
                    <span class="source-tag">${srcLabel}</span>
                </td>
                <td>${e.portion_g}g</td>
                <td><strong>${e.kcal} kcal</strong></td>
                <td>${e.carbohydrates_g}g</td>
                <td class="text-emerald"><strong>${e.proteins_g}g</strong></td>
                <td>${e.fat_g}g</td>
                <td><button class="btn-delete" aria-label="Remover ${e.product_name} da dieta" onclick="removeDiaryItem(${e.id})">Remover</button></td>
            </tr>`;
        })
        .join("");

    const totalRow = `
        <tr style="background: rgba(16, 185, 129, 0.08); font-weight: 700;">
            <td colspan="2">Total consumido hoje vs Limite Diário</td>
            <td>-</td>
            <td>${c.kcal} / ${Math.round(g.daily_kcal_limit)} kcal</td>
            <td>${c.carbohydrates_g} / ${Math.round(g.carbs_limit_g)}g</td>
            <td class="text-emerald">${c.proteins_g} / ${Math.round(g.proteins_limit_g)}g</td>
            <td>${c.fat_g} / ${Math.round(g.fat_limit_g)}g</td>
            <td>-</td>
        </tr>`;

    tbody.innerHTML = rowsHtml + totalRow;
}

let currentDietDate = new Date().toISOString().slice(0, 10);

async function loadDietToday(dateStr = currentDietDate) {
    currentDietDate = dateStr;
    updateDateDisplay(currentDietDate);
    try {
        const res = await fetch(`/api/v1/diet/today?date=${dateStr}`);
        if (res.ok) {
            const data = await res.json();
            renderDietToday(data);
            await loadWaterData(dateStr);
            await load7DayTrends();
            return;
        }
    } catch (_) {}
    const state = getLocalDietData();
    renderDietToday(buildOfflineSummary(state));
    await loadWaterData(dateStr);
    await load7DayTrends();
}

function updateDateDisplay(dateStr) {
    const todayStr = new Date().toISOString().slice(0, 10);
    const badge = document.getElementById("diet-date-badge");
    const text = document.getElementById("diet-date-text");
    if (!badge || !text) return;
    const parts = dateStr.split("-");
    const brDate = parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : dateStr;
    if (dateStr === todayStr) {
        badge.textContent = "HOJE";
        text.textContent = `Hoje (${brDate})`;
    } else {
        badge.textContent = dateStr < todayStr ? "ANTERIOR" : "FUTURO";
        text.textContent = brDate;
    }
}

async function loadWaterData(dateStr = currentDietDate) {
    try {
        const res = await fetch(`/api/v1/diet/water?date=${dateStr}`);
        if (res.ok) {
            const data = await res.json();
            renderWater(data);
            return;
        }
    } catch (_) {}
    renderWater({ amount_ml: 0, goal_ml: 2500, pct: 0 });
}

function renderWater(data) {
    if (typeof document === "undefined") return;
    const consumed = data.amount_ml || 0;
    const goal = data.goal_ml || 2500;
    const pct = Math.min(100, Math.round((consumed / goal) * 100));
    const elVal = document.getElementById("water-consumed-val");
    const elGoal = document.getElementById("water-goal-val");
    const elBadge = document.getElementById("water-pct-badge");
    const elFill = document.getElementById("water-progress-fill");
    if (elVal) elVal.textContent = `${consumed} ml`;
    if (elGoal) elGoal.textContent = `${goal} ml`;
    if (elBadge) elBadge.textContent = `${pct}%`;
    if (elFill) elFill.style.width = `${pct}%`;
}

async function addWaterAmount(amountMl) {
    if (typeof window.triggerHaptic === "function") window.triggerHaptic(40);
    try {
        await fetch("/api/v1/diet/water", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ amount_ml: amountMl, date_str: currentDietDate }),
        });
    } catch (_) {}
    await loadWaterData(currentDietDate);
    await load7DayTrends();
}

async function resetWaterAmount() {
    if (typeof window.triggerHaptic === "function") window.triggerHaptic(60);
    try {
        await fetch(`/api/v1/diet/water?date=${currentDietDate}`, { method: "DELETE" });
    } catch (_) {}
    await loadWaterData(currentDietDate);
    await load7DayTrends();
}

async function load7DayTrends() {
    try {
        const res = await fetch("/api/v1/diet/trends");
        if (res.ok) {
            const data = await res.json();
            renderTrends(data);
        }
    } catch (_) {}
}

function renderTrends(data) {
    const container = document.getElementById("trends-bars-container");
    if (!container || !data || !data.days) return;
    const badge = document.getElementById("trends-compliance-badge");
    if (badge) badge.textContent = `${Math.round(data.compliance_rate || 100)}% na meta`;

    const maxKcal = Math.max(...data.days.map((d) => Math.max(d.total_kcal, d.kcal_limit)), 2200);
    const todayStr = new Date().toISOString().slice(0, 10);

    container.innerHTML = data.days
        .map((d) => {
            const heightPct = Math.min(100, Math.max(8, Math.round((d.total_kcal / maxKcal) * 100)));
            const isToday = d.date_str === todayStr;
            const overGoal = d.total_kcal > d.kcal_limit;
            return `
            <div class="trend-col ${isToday ? "is-today" : ""}" title="${d.weekday_short} (${d.date_str}): ${d.total_kcal} kcal / ${d.kcal_limit} kcal">
                <div class="trend-bar-track">
                    <div class="trend-bar-fill ${overGoal ? "over-goal" : ""}" style="height: ${heightPct}%;"></div>
                </div>
                <span class="trend-day-label">${d.weekday_short}</span>
            </div>`;
        })
        .join("");
}

window.removeDiaryItem = async function (entryId) {
    try {
        const res = await fetch(`/api/v1/diet/diary/${entryId}`, { method: "DELETE" });
        if (res.ok) {
            await loadDietToday();
            return;
        }
    } catch (_) {}
    const state = getLocalDietData();
    state.entries = state.entries.filter((e) => e.id !== entryId);
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(state));
    renderDietToday(buildOfflineSummary(state));
};

async function addDiaryEntryToDiet(payload) {
    if (typeof window.triggerHaptic === "function") window.triggerHaptic(50);
    try {
        const res = await fetch("/api/v1/diet/diary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            await loadDietToday();
            return;
        }
    } catch (_) {}
    const state = getLocalDietData();
    const nextId = state.entries.length > 0 ? Math.max(...state.entries.map((e) => e.id)) + 1 : 1;
    state.entries.push({ id: nextId, ...payload });
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(state));
    renderDietToday(buildOfflineSummary(state));
}
window.addDiaryEntryToDiet = addDiaryEntryToDiet;
window.loadDietToday = loadDietToday;

async function saveDietGoals(autoCalculate = false) {
    const payload = {
        goal_type: document.getElementById("goal-type").value,
        activity_level: document.getElementById("goal-activity").value,
        weight_kg: parseFloat(document.getElementById("goal-weight").value) || 78,
        height_cm: parseFloat(document.getElementById("goal-height").value) || 176,
        age: parseInt(document.getElementById("goal-age").value, 10) || 29,
        auto_calculate: autoCalculate,
        daily_kcal_limit: parseFloat(document.getElementById("limit-kcal").value) || 2000,
        proteins_limit_g: parseFloat(document.getElementById("limit-prot").value) || 150,
        carbs_limit_g: parseFloat(document.getElementById("limit-carb").value) || 200,
        fat_limit_g: parseFloat(document.getElementById("limit-fat").value) || 65,
        sodium_limit_mg: parseFloat(document.getElementById("limit-sodium").value) || 2000,
    };

    try {
        const res = await fetch("/api/v1/diet/goals", {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (res.ok) {
            await loadDietToday();
            if (currentOcrResult) await runPhotoLabelScan(false);
            const fb = document.getElementById("goals-feedback");
            fb.textContent = autoCalculate
                ? "Meta calculada pelo peso/altura e aplicada à dieta de hoje."
                : "Limite diário atualizado.";
            setTimeout(() => (fb.textContent = ""), 3500);
            return;
        }
    } catch (_) {}

    const state = getLocalDietData();
    if (autoCalculate) {
        const bmr = 10 * payload.weight_kg + 6.25 * payload.height_cm - 5 * payload.age + 5;
        const mult = { sedentario: 1.2, leve: 1.375, moderado: 1.55, intenso: 1.725 }[payload.activity_level] || 1.55;
        const tdee = bmr * mult;
        const kcal =
            payload.goal_type === "cutting"
                ? Math.max(1200, Math.round((tdee - 450) / 10) * 10)
                : payload.goal_type === "bulking"
                ? Math.round((tdee + 350) / 10) * 10
                : Math.round(tdee / 10) * 10;
        const prot = Math.round(payload.weight_kg * 2.0);
        const fat = Math.round(payload.weight_kg * 0.85);
        const carbs = Math.max(50, Math.round((kcal - prot * 4 - fat * 9) / 4));
        payload.daily_kcal_limit = kcal;
        payload.proteins_limit_g = prot;
        payload.fat_limit_g = fat;
        payload.carbs_limit_g = carbs;
    }
    state.goals = payload;
    localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(state));
    renderDietToday(buildOfflineSummary(state));
}

/* PARSER CLIENT-SIDE DE FICHA TÉCNICA PARA MODO OFFLINE ANDROID */
function parseNutritionTextClientSide(rawText, portionConsumedG, productName) {
    const text = (rawText || "").trim();
    const findNum = (regexList, defVal = 0) => {
        for (const rgx of regexList) {
            const m = text.match(rgx);
            if (m && m[1]) {
                const v = parseFloat(m[1].replace(",", "."));
                if (!isNaN(v)) return v;
            }
        }
        return defVal;
    };

    const portionLabel = findNum([/Por[çc][ãa]o(?:\s+de)?\s*[:\-]?\s*(\d+[.,]?\d*)\s*(?:g|ml)/i], 100) || 100;
    let kcal = findNum([/Valor\s+energ[ée]tico\s*[:\-]?\s*(\d+[.,]?\d*)\s*kcal/i, /(\d+[.,]?\d*)\s*kcal/i], 0);
    const carbs = findNum([/Carboidratos(?:\s+totais)?\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const sugars = findNum([/A[çc][úu]cares\s+totais\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i, /A[çc][úu]cares\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const prot = findNum([/Prote[íi]nas?\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const fat = findNum([/Gorduras?\s+totais\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const satFat = findNum([/Gorduras?\s+saturadas?\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const fiber = findNum([/Fibras?\s+alimentar(?:es)?\s*[:\-]?\s*(\d+[.,]?\d*)\s*g/i], 0);
    const sodium = findNum([/S[óo]dio\s*[:\-]?\s*(\d+[.,]?\d*)\s*mg/i], 0);

    if (kcal <= 0 && (carbs > 0 || prot > 0 || fat > 0)) {
        kcal = Number((carbs * 4 + prot * 4 + fat * 9).toFixed(1));
    }

    const scale = (portionConsumedG || portionLabel) / portionLabel;
    const scale100 = 100 / portionLabel;
    const goals = currentDietSummary ? currentDietSummary.goals : getLocalDietData().goals;

    const consumed = {
        portion_g: Number((portionConsumedG || portionLabel).toFixed(1)),
        kcal: Number((kcal * scale).toFixed(1)),
        carbohydrates_g: Number((carbs * scale).toFixed(1)),
        sugars_g: Number((sugars * scale).toFixed(1)),
        proteins_g: Number((prot * scale).toFixed(1)),
        fat_g: Number((fat * scale).toFixed(1)),
        saturated_fat_g: Number((satFat * scale).toFixed(1)),
        fiber_g: Number((fiber * scale).toFixed(1)),
        sodium_mg: Number((sodium * scale).toFixed(1)),
    };

    const warnings = [];
    if (sugars * scale100 >= 15) warnings.push("ALTO EM AÇÚCAR");
    if (satFat * scale100 >= 6) warnings.push("ALTO EM GORDURA SATURADA");
    if (sodium * scale100 >= 600) warnings.push("ALTO EM SÓDIO");

    return {
        product_name: productName || "Alimento lido pela ficha técnica",
        portion_label_g: portionLabel,
        portion_consumed_g: consumed.portion_g,
        scale_factor: Number(scale.toFixed(2)),
        raw_ocr_text: text,
        per_label_portion: {
            kcal,
            carbohydrates_g: carbs,
            sugars_g: sugars,
            proteins_g: prot,
            fat_g: fat,
            saturated_fat_g: satFat,
            fiber_g: fiber,
            sodium_mg: sodium,
        },
        consumed_macros: consumed,
        daily_limit_impact_pct: {
            kcal_pct: Number(((consumed.kcal / (goals.daily_kcal_limit || 2000)) * 100).toFixed(1)),
            carbohydrates_pct: Number(((consumed.carbohydrates_g / (goals.carbs_limit_g || 200)) * 100).toFixed(1)),
            proteins_pct: Number(((consumed.proteins_g / (goals.proteins_limit_g || 150)) * 100).toFixed(1)),
            fat_pct: Number(((consumed.fat_g / (goals.fat_limit_g || 65)) * 100).toFixed(1)),
            sodium_pct: Number(((consumed.sodium_mg / (goals.sodium_limit_mg || 2000)) * 100).toFixed(1)),
        },
        anvisa: {
            warnings_count: warnings.length,
            warnings_list: warnings,
        },
        nutriscore_grade: warnings.length === 0 && prot * scale100 >= 8 ? "A" : warnings.length >= 2 ? "D" : "B",
    };
}

function renderOcrResult(res) {
    currentOcrResult = res;
    document.getElementById("ocr-prod-name").textContent = res.product_name;
    document.getElementById("ocr-portion-summary").textContent =
        `Tabela base: ${res.portion_label_g}g | Seu consumo: ${res.portion_consumed_g}g (${res.scale_factor}x)`;

    const nsBadge = document.getElementById("ocr-nutriscore-badge");
    const grade = (res.nutriscore_grade || "A").toUpperCase();
    nsBadge.textContent = `Nutri-Score ${grade}`;
    nsBadge.className = `ns-step ns-${grade.toLowerCase()} active`;

    const cm = res.consumed_macros;
    const imp = res.daily_limit_impact_pct;
    const pl = res.per_label_portion;

    document.getElementById("ocr-res-kcal").textContent = `${cm.kcal} kcal`;
    document.getElementById("ocr-pct-kcal").textContent = `+${imp.kcal_pct}% do limite diário`;

    document.getElementById("ocr-res-prot").textContent = `${cm.proteins_g} g`;
    document.getElementById("ocr-pct-prot").textContent = `+${imp.proteins_pct}% da meta`;

    document.getElementById("ocr-res-carb").textContent = `${cm.carbohydrates_g} g`;
    document.getElementById("ocr-pct-carb").textContent = `+${imp.carbohydrates_pct}% da meta`;

    document.getElementById("ocr-res-fat").textContent = `${cm.fat_g} g`;
    document.getElementById("ocr-pct-fat").textContent = `+${imp.fat_pct}% da meta`;

    document.getElementById("th-label-base").textContent = `No rótulo (${res.portion_label_g}g)`;
    document.getElementById("th-consumed-base").textContent = `Sua porção (${res.portion_consumed_g}g)`;

    const rows = [
        ["Valor energético", `${pl.kcal} kcal`, `${cm.kcal} kcal`, `${imp.kcal_pct}% da meta kcal`],
        ["Proteínas", `${pl.proteins_g} g`, `${cm.proteins_g} g`, `${imp.proteins_pct}% da meta prot`],
        ["Carboidratos", `${pl.carbohydrates_g} g`, `${cm.carbohydrates_g} g`, `${imp.carbohydrates_pct}% da meta carb`],
        ["Açúcares totais", `${pl.sugars_g} g`, `${cm.sugars_g} g`, "Incluso nos carboidratos"],
        ["Gorduras totais", `${pl.fat_g} g`, `${cm.fat_g} g`, `${imp.fat_pct}% da meta gord`],
        ["Gorduras saturadas", `${pl.saturated_fat_g} g`, `${cm.saturated_fat_g} g`, "Corte ANVISA: 6g/100g"],
        ["Fibras alimentares", `${pl.fiber_g} g`, `${cm.fiber_g} g`, "Recomendado >= 25g/dia"],
        ["Sódio", `${pl.sodium_mg} mg`, `${cm.sodium_mg} mg`, `${imp.sodium_pct}% do limite sódio`],
    ];

    document.getElementById("ocr-breakdown-tbody").innerHTML = rows
        .map(
            ([label, vBase, vCons, pctText]) => `
        <tr>
            <td>${label}</td>
            <td>${vBase}</td>
            <td><strong>${vCons}</strong></td>
            <td class="threshold-note">${pctText}</td>
        </tr>`
        )
        .join("");

    const sealsEl = document.getElementById("ocr-anvisa-seals");
    if (!res.anvisa.warnings_list || res.anvisa.warnings_list.length === 0) {
        sealsEl.innerHTML = `<div class="anvisa-clean">Sem alertas frontais de excesso (RDC 429/2020)</div>`;
    } else {
        sealsEl.innerHTML = res.anvisa.warnings_list
            .map(
                (w) => `
            <div class="anvisa-lupa">
                <span class="anvisa-lupa-icon">LUPA ANVISA</span>
                <span>${w}</span>
            </div>`
            )
            .join("");
    }
}

async function runPhotoLabelScan(useSampleText = false) {
    const portionG = parseFloat(document.getElementById("photo-portion-input").value) || 45;
    const textarea = document.getElementById("ocr-raw-textarea");

    if (useSampleText && OFFLINE_SAMPLES[currentSampleId]) {
        textarea.value = OFFLINE_SAMPLES[currentSampleId].raw_text;
    }

    try {
        const formData = new FormData();
        formData.append("portion_g", String(portionG));
        if (uploadedFileObj) {
            formData.append("file", uploadedFileObj);
        } else if (currentSampleId) {
            formData.append("sample_id", currentSampleId);
        }
        if (textarea.value.trim()) {
            formData.append("raw_text", textarea.value.trim());
        }

        const res = await fetch("/api/v1/scan-label-photo", {
            method: "POST",
            body: formData,
        });
        if (res.ok) {
            const data = await res.json();
            if (!textarea.value.trim() || uploadedFileObj) {
                textarea.value = data.raw_ocr_text;
            }
            renderOcrResult(data);
            return;
        }
    } catch (_) {}

    const sampleSpec = OFFLINE_SAMPLES[currentSampleId] || OFFLINE_SAMPLES.rotulo_whey;
    const rawText = textarea.value.trim() || sampleSpec.raw_text;
    textarea.value = rawText;
    const parsed = parseNutritionTextClientSide(rawText, portionG, sampleSpec.product_name);
    renderOcrResult(parsed);
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
    currentScannedProduct = prod;
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
            await loadHistory();
            return;
        }
    } catch (_) {}

    const found =
        OFFLINE_CATALOG.find((p) => p.barcode === clean || p.product_name.toLowerCase().includes(clean.toLowerCase())) ||
        OFFLINE_CATALOG[0];
    renderProduct(found);
}

async function loadHistory() {
    try {
        const res = await fetch("/api/v1/history");
        if (res.ok) {
            cachedHistory = await res.json();
            populateCompareSelectors();
            return;
        }
    } catch (_) {}
    cachedHistory = OFFLINE_CATALOG;
    populateCompareSelectors();
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
                <h3 style="font-size:15px;margin-top:4px;">${prod.product_name}</h3>
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
        return;
    } catch (_) {}

    const prodA = OFFLINE_CATALOG.find((p) => p.barcode === codeA) || OFFLINE_CATALOG[0];
    const prodB = OFFLINE_CATALOG.find((p) => p.barcode === codeB) || OFFLINE_CATALOG[1];
    renderCompareMiniCard("comp-card-a", prodA);
    renderCompareMiniCard("comp-card-b", prodB);
    document.getElementById("th-prod-a").textContent = prodA.product_name;
    document.getElementById("th-prod-b").textContent = prodB.product_name;
    const specs = [
        ["Valor energético", "kcal", prodA.nutrition.energy_kcal, prodB.nutrition.energy_kcal, true],
        ["Açúcares totais", "g", prodA.nutrition.sugars_g, prodB.nutrition.sugars_g, true],
        ["Gorduras saturadas", "g", prodA.nutrition.saturated_fat_g, prodB.nutrition.saturated_fat_g, true],
        ["Sódio", "mg", prodA.nutrition.sodium_mg, prodB.nutrition.sodium_mg, true],
        ["Proteínas", "g", prodA.nutrition.proteins_g, prodB.nutrition.proteins_g, false],
        ["Fibras alimentares", "g", prodA.nutrition.fiber_g, prodB.nutrition.fiber_g, false],
    ];
    document.getElementById("compare-deltas-tbody").innerHTML = specs
        .map(([label, unit, va, vb, lower]) => {
            const diff = Number((va - vb).toFixed(1));
            const sign = diff > 0 ? `+${diff}` : `${diff}`;
            const fav = lower ? (va < vb ? prodA.product_name : prodB.product_name) : va > vb ? prodA.product_name : prodB.product_name;
            return `<tr><td><strong>${label}</strong></td><td>${va} ${unit}</td><td>${vb} ${unit}</td><td><code>${sign} ${unit}</code></td><td><span class="text-emerald">${fav}</span></td></tr>`;
        })
        .join("");
}

function setupCameraBarcodeScanner() {
    const modal = document.getElementById("cam-scanner-modal");
    const video = document.getElementById("cam-scanner-video");
    const btnOpen = document.getElementById("btn-open-cam-scanner");
    const btnClose = document.getElementById("btn-cam-close");
    const btnCancel = document.getElementById("btn-cam-cancel");
    const btnTorch = document.getElementById("btn-cam-torch");
    const statusPill = document.getElementById("cam-scanner-status");

    if (!btnOpen || !modal) return;
    let torchOn = false;

    btnOpen.addEventListener("click", () => {
        if (typeof window.triggerHaptic === "function") window.triggerHaptic(50);
        modal.hidden = false;
        if (statusPill) statusPill.textContent = "Aponte para o código de barras";

        if (window.NutriScanCameraScanner) {
            window.NutriScanCameraScanner.startScanner(
                video,
                (barcode) => {
                    modal.hidden = true;
                    window.NutriScanCameraScanner.stopScanner();
                    const input = document.getElementById("barcode-input");
                    if (input) input.value = barcode;
                    scanProduct(barcode);
                },
                (err) => {
                    if (statusPill) statusPill.textContent = "Câmera indisponível ou permissão negada";
                }
            );
        }
    });

    const closeModal = () => {
        modal.hidden = true;
        if (window.NutriScanCameraScanner) {
            window.NutriScanCameraScanner.stopScanner();
        }
    };

    if (btnClose) btnClose.addEventListener("click", closeModal);
    if (btnCancel) btnCancel.addEventListener("click", closeModal);

    if (btnTorch) {
        btnTorch.addEventListener("click", async () => {
            torchOn = !torchOn;
            if (window.NutriScanCameraScanner) {
                await window.NutriScanCameraScanner.toggleTorch(torchOn);
            }
        });
    }
}

if (typeof document !== "undefined") {
    document.addEventListener("DOMContentLoaded", async () => {
        if (typeof navigator !== "undefined" && "serviceWorker" in navigator && typeof window !== "undefined" && window.location && window.location.protocol.startsWith("http")) {
            navigator.serviceWorker.register("/sw.js").catch(() => {});
        }

    document.querySelectorAll(".tab-btn, .mob-nav-btn").forEach((btn) => {
        btn.addEventListener("click", () => {
            switchTab(btn.dataset.tab);
            if (btn.dataset.tab === "comparar") runComparison();
        });
    });

    document.getElementById("btn-go-photo-scan").addEventListener("click", () => {
        switchTab("foto");
    });

    document.getElementById("btn-add-manual").addEventListener("click", async () => {
        const meal = document.getElementById("manual-meal").value;
        const name = document.getElementById("manual-name").value.trim() || "Alimento adicionado";
        const portion = parseFloat(document.getElementById("manual-portion").value) || 100;
        const kcal = parseFloat(document.getElementById("manual-kcal").value) || 0;
        const carb = parseFloat(document.getElementById("manual-carb").value) || 0;
        const prot = parseFloat(document.getElementById("manual-prot").value) || 0;
        const fat = parseFloat(document.getElementById("manual-fat").value) || 0;

        await addDiaryEntryToDiet({
            meal_type: meal,
            product_name: name,
            source_type: "manual",
            portion_g: portion,
            kcal,
            carbohydrates_g: carb,
            proteins_g: prot,
            fat_g: fat,
            fiber_g: 0,
            sodium_mg: 0,
        });
        document.getElementById("manual-name").value = "";
    });

    document.getElementById("btn-calc-mifflin").addEventListener("click", () => saveDietGoals(true));
    document.getElementById("btn-save-goals").addEventListener("click", () => saveDietGoals(false));

    // Controles da aba Foto da Ficha Técnica
    document.querySelectorAll(".sample-chip").forEach((chip) => {
        chip.addEventListener("click", async () => {
            document.querySelectorAll(".sample-chip").forEach((c) => c.classList.remove("active"));
            chip.classList.add("active");
            uploadedFileObj = null;
            currentSampleId = chip.dataset.sample;
            const defaultPortion = chip.dataset.portion || "45";
            document.getElementById("photo-portion-input").value = defaultPortion;

            const spec = OFFLINE_SAMPLES[currentSampleId];
            if (spec) {
                document.getElementById("label-preview-img").src = spec.image_url;
                document.getElementById("upload-filename").textContent = `Amostra: ${spec.product_name}`;
                document.getElementById("ocr-raw-textarea").value = spec.raw_text;
            }
            await runPhotoLabelScan(true);
        });
    });

    document.getElementById("label-photo-input").addEventListener("change", async (e) => {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        uploadedFileObj = file;
        document.getElementById("upload-filename").textContent = `Foto enviada: ${file.name}`;
        const reader = new FileReader();
        reader.onload = (ev) => {
            document.getElementById("label-preview-img").src = ev.target.result;
        };
        reader.readAsDataURL(file);
        document.getElementById("ocr-raw-textarea").value = "";
        await runPhotoLabelScan(false);
    });

    document.getElementById("btn-recalc-photo").addEventListener("click", () => runPhotoLabelScan(false));
    document.getElementById("photo-portion-input").addEventListener("change", () => runPhotoLabelScan(false));

    document.getElementById("btn-add-ocr-to-diet").addEventListener("click", async () => {
        if (!currentOcrResult) return;
        const meal = document.getElementById("photo-meal-select").value || "Lanche";
        const cm = currentOcrResult.consumed_macros;
        await addDiaryEntryToDiet({
            meal_type: meal,
            product_name: currentOcrResult.product_name,
            source_type: "foto_ficha",
            portion_g: cm.portion_g,
            kcal: cm.kcal,
            carbohydrates_g: cm.carbohydrates_g,
            proteins_g: cm.proteins_g,
            fat_g: cm.fat_g,
            fiber_g: cm.fiber_g,
            sodium_mg: cm.sodium_mg,
        });
        switchTab("dieta");
    });

    // Controles da aba Código de Barras
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

    document.getElementById("btn-add-barcode-diet").addEventListener("click", async () => {
        if (!currentScannedProduct) return;
        const portionG = parseFloat(document.getElementById("barcode-portion-g").value) || 30;
        const meal = document.getElementById("barcode-meal-type").value || "Lanche";
        const scale = portionG / 100.0;
        const n = currentScannedProduct.nutrition;
        await addDiaryEntryToDiet({
            meal_type: meal,
            product_name: currentScannedProduct.product_name,
            source_type: "codigo_barras",
            portion_g: portionG,
            kcal: Number((n.energy_kcal * scale).toFixed(1)),
            carbohydrates_g: Number((n.carbohydrates_g * scale).toFixed(1)),
            proteins_g: Number((n.proteins_g * scale).toFixed(1)),
            fat_g: Number((n.fat_g * scale).toFixed(1)),
            fiber_g: Number((n.fiber_g * scale).toFixed(1)),
            sodium_mg: Number((n.sodium_mg * scale).toFixed(1)),
        });
        switchTab("dieta");
    });

    document.getElementById("btn-run-compare").addEventListener("click", runComparison);

    // Navegador de data
    const btnDatePrev = document.getElementById("btn-date-prev");
    const btnDateNext = document.getElementById("btn-date-next");
    if (btnDatePrev) {
        btnDatePrev.addEventListener("click", () => {
            const d = new Date(currentDietDate + "T12:00:00");
            d.setDate(d.getDate() - 1);
            loadDietToday(d.toISOString().slice(0, 10));
        });
    }
    if (btnDateNext) {
        btnDateNext.addEventListener("click", () => {
            const d = new Date(currentDietDate + "T12:00:00");
            d.setDate(d.getDate() + 1);
            loadDietToday(d.toISOString().slice(0, 10));
        });
    }

    // Ações de hidratação (água)
    document.querySelectorAll(".btn-water-add").forEach((btn) => {
        btn.addEventListener("click", () => {
            addWaterAmount(parseInt(btn.dataset.amount, 10) || 200);
        });
    });
    const btnWaterReset = document.getElementById("btn-water-reset");
    if (btnWaterReset) {
        btnWaterReset.addEventListener("click", resetWaterAmount);
    }

    // Scanner por câmera ao vivo
    setupCameraBarcodeScanner();

    const params = new URLSearchParams(window.location.search);
    const initialTab = params.get("tab");
    if (initialTab && ["dieta", "foto", "scanner", "comparar", "compare", "prato"].includes(initialTab)) {
        switchTab(initialTab);
    } else {
        switchTab("dieta");
    }

    if (params.get("tab") === "scanner" && params.get("cam") === "1") {
        setTimeout(() => document.getElementById("btn-open-cam-scanner")?.click(), 300);
    }

    await loadDietToday();
    document.getElementById("ocr-raw-textarea").value = OFFLINE_SAMPLES.rotulo_whey.raw_text;
    await runPhotoLabelScan(false);
    await loadHistory();
    await scanProduct(document.getElementById("barcode-input").value || "3017620422003");
    await runComparison();

    // Iniciar Tour Interativo se clicado no botão ou se solicitado via URL (?tour=1)
    const btnStartTour = document.getElementById("btn-start-tour");
    if (btnStartTour) {
        btnStartTour.addEventListener("click", () => {
            if (window.NutriScanTour) {
                window.NutriScanTour.startTour(true);
            }
        });
    }

    if (params.get("tour") === "1") {
        setTimeout(() => {
            if (window.NutriScanTour) window.NutriScanTour.startTour(true);
        }, 400);
    }

    // Gerenciamento do Modal de Perfil & Onboarding (#modal-profile-onboarding)
    setupProfileOnboardingModal();
    });
}

function setupProfileOnboardingModal() {
    const modal = document.getElementById("modal-profile-onboarding");
    const btnOpenProfile = document.getElementById("btn-open-profile");
    const btnOpenTour = document.getElementById("btn-open-tour");
    const btnCloseModal = document.getElementById("btn-profile-close");
    const btnSkipProfile = document.getElementById("btn-profile-skip");
    const form = document.getElementById("profile-onboarding-form");

    // Profile inputs
    const inputName = document.getElementById("profile-name");
    const inputGender = document.getElementById("profile-gender");
    const inputAge = document.getElementById("profile-age");
    const inputWeight = document.getElementById("profile-weight");
    const inputHeight = document.getElementById("profile-height");
    const inputActivity = document.getElementById("profile-activity");
    const inputGoal = document.getElementById("profile-goal");

    // Preview elements
    const previewKcal = document.getElementById("profile-preview-kcal");
    const previewWater = document.getElementById("profile-preview-water");

    function updatePreview() {
        if (!previewKcal || !previewWater) return;
        const gender = inputGender?.value || "masculino";
        const weight = parseFloat(inputWeight?.value) || 75;
        const height = parseFloat(inputHeight?.value) || 175;
        const age = parseInt(inputAge?.value, 10) || 28;
        const activity = inputActivity?.value || "moderado";
        const goal = inputGoal?.value || "cutting";

        const res = calculateMifflinStJeor(gender, weight, height, age, activity, goal);
        previewKcal.textContent = `~${res.daily_kcal_limit} kcal`;
        previewWater.textContent = `~${res.water_goal_ml} ml`;
    }

    function openModal() {
        if (!modal) return;
        const profile = getUserProfile();
        if (profile) {
            if (inputName) inputName.value = profile.name || "";
            if (inputGender) inputGender.value = profile.gender || "masculino";
            if (inputAge) inputAge.value = profile.age || 29;
            if (inputWeight) inputWeight.value = profile.weight_kg || 78;
            if (inputHeight) inputHeight.value = profile.height_cm || 176;
            if (inputActivity) inputActivity.value = profile.activity_level || "moderado";
            if (inputGoal) inputGoal.value = profile.goal_type || "cutting";
        }
        updatePreview();
        modal.hidden = false;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        if (typeof window.triggerHaptic === "function") window.triggerHaptic(30);
    }

    function closeModal() {
        if (!modal) return;
        modal.hidden = true;
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
    }

    if (btnOpenProfile) {
        btnOpenProfile.addEventListener("click", openModal);
    }

    if (btnOpenTour) {
        btnOpenTour.addEventListener("click", () => {
            if (window.NutriScanTour) {
                window.NutriScanTour.startTour(true);
            }
        });
    }

    if (btnCloseModal) {
        btnCloseModal.addEventListener("click", closeModal);
    }

    if (btnSkipProfile) {
        btnSkipProfile.addEventListener("click", () => {
            closeModal();
            // Start tour if not completed
            if (window.NutriScanTour && !localStorage.getItem("nutriscan_tour_completed")) {
                window.NutriScanTour.startTour(false);
            }
        });
    }

    // Attach input listeners for live preview
    [inputGender, inputAge, inputWeight, inputHeight, inputActivity, inputGoal].forEach((el) => {
        if (el) {
            el.addEventListener("input", updatePreview);
            el.addEventListener("change", updatePreview);
        }
    });

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const profileData = {
                name: (inputName?.value || "").trim(),
                gender: inputGender?.value || "masculino",
                age: parseInt(inputAge?.value, 10) || 28,
                weight_kg: parseFloat(inputWeight?.value) || 75,
                height_cm: parseFloat(inputHeight?.value) || 175,
                activity_level: inputActivity?.value || "moderado",
                goal_type: inputGoal?.value || "cutting",
                updated_at: new Date().toISOString(),
            };

            await saveUserProfile(profileData);
            closeModal();
        });
    }

    // Initial greeting render
    updateUserGreeting();

    // Check if user has no profile yet -> automatically open onboarding modal
    const existingProfile = getUserProfile();
    if (!existingProfile) {
        setTimeout(openModal, 350);
    }
}

// CommonJS export for Node.js unit tests
if (typeof module !== "undefined" && module.exports) {
    module.exports = {
        getLocalDietData,
        calculateMifflinStJeor,
        getUserProfile,
        saveUserProfile,
        resetAllUserData,
        updateUserGreeting,
        NutriScanProfile,
    };
}

