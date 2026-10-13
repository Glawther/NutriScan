// Unit tests for NutriScan Profile Management (Mifflin-St Jeor & Zero-State Initialization)
// Run with: node --test tests/js/profile.test.js
const test = require("node:test");
const assert = require("node:assert");

// Mock localStorage and window before loading app.js
const storageMock = new Map();
globalThis.localStorage = {
    getItem: (key) => (storageMock.has(key) ? storageMock.get(key) : null),
    setItem: (key, val) => storageMock.set(key, String(val)),
    removeItem: (key) => storageMock.delete(key),
    clear: () => storageMock.clear(),
};

globalThis.window = globalThis;
globalThis.window.dispatchEvent = () => true;
globalThis.CustomEvent = class CustomEvent {
    constructor(event, params) {
        this.type = event;
        this.detail = params?.detail;
    }
};

const appModule = require("../../app/static/js/app.js");
const {
    calculateMifflinStJeor,
    getUserProfile,
    saveUserProfile,
    resetAllUserData,
    getLocalDietData,
} = appModule;

test("Mifflin-St Jeor: TMB Masculino calculation", () => {
    // Exemplo Masculino: peso 80 kg, altura 180 cm, idade 30 anos
    // TMB = 10 * 80 + 6.25 * 180 - 5 * 30 + 5
    //     = 800 + 1125 - 150 + 5 = 1780 kcal
    const maleRes = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "manutencao");
    assert.strictEqual(maleRes.tmb, 1780);
});

test("Mifflin-St Jeor: TMB Feminino calculation", () => {
    // Exemplo Feminino: peso 60 kg, altura 165 cm, idade 25 anos
    // TMB = 10 * 60 + 6.25 * 165 - 5 * 25 - 161
    //     = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345 kcal
    const femaleRes = calculateMifflinStJeor("feminino", 60, 165, 25, "sedentario", "manutencao");
    assert.strictEqual(femaleRes.tmb, 1345);
});

test("Activity Level multipliers (sedentario, leve, moderado, intenso)", () => {
    // Homem: 80kg, 180cm, 30 anos -> TMB 1780
    // Sedentario (1.2): 1780 * 1.2 = 2136
    const rSed = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "manutencao");
    assert.strictEqual(rSed.tdee, 2136);

    // Leve (1.375): 1780 * 1.375 = 2447.5 -> 2448
    const rLeve = calculateMifflinStJeor("masculino", 80, 180, 30, "leve", "manutencao");
    assert.strictEqual(rLeve.tdee, 2448);

    // Moderado (1.55): 1780 * 1.55 = 2759
    const rMod = calculateMifflinStJeor("masculino", 80, 180, 30, "moderado", "manutencao");
    assert.strictEqual(rMod.tdee, 2759);

    // Intenso (1.725): 1780 * 1.725 = 3070.5 -> 3071
    const rInt = calculateMifflinStJeor("masculino", 80, 180, 30, "intenso", "manutencao");
    assert.strictEqual(rInt.tdee, 3071);
});

test("Goal adjustments: cutting (-400 kcal), manutencao (0 kcal), bulking (+350 kcal)", () => {
    // TDEE = 2136 (Sedentario, 80kg, 180cm, 30 anos)
    // Cutting: 2136 - 400 = 1736 kcal
    const rCut = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "cutting");
    assert.strictEqual(rCut.daily_kcal_limit, 1736);

    // Manutencao: 2136 kcal
    const rMan = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "manutencao");
    assert.strictEqual(rMan.daily_kcal_limit, 2136);

    // Bulking: 2136 + 350 = 2486 kcal
    const rBulk = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "bulking");
    assert.strictEqual(rBulk.daily_kcal_limit, 2486);
});

test("Macro distribution and water calculation for cutting", () => {
    // Cutting: 80 kg, 180 cm, 30 anos, sedentario (-400 kcal)
    // Limite kcal: 1736 kcal
    // Proteína: 2.0 g/kg * 80 kg = 160 g (160 * 4 = 640 kcal)
    // Gordura: 0.8 g/kg * 80 kg = 64 g (64 * 9 = 576 kcal)
    // Carboidratos restantes: (1736 - 640 - 576) / 4 = 520 / 4 = 130 g
    // Água: round(80 * 35) = 2800 ml
    const rCut = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "cutting");
    assert.strictEqual(rCut.proteins_limit_g, 160);
    assert.strictEqual(rCut.fat_limit_g, 64);
    assert.strictEqual(rCut.carbs_limit_g, 130);
    assert.strictEqual(rCut.water_goal_ml, 2800);
});

test("Macro distribution for manutencao (1.6 g/kg de proteína)", () => {
    // Manutencao: 80 kg, 180 cm, 30 anos, sedentario
    // Limite kcal: 2136 kcal
    // Proteína: 1.6 g/kg * 80 = 128 g (128 * 4 = 512 kcal)
    // Gordura: 0.8 g/kg * 80 = 64 g (64 * 9 = 576 kcal)
    // Carboidratos restantes: (2136 - 512 - 576) / 4 = 1048 / 4 = 262 g
    const rMan = calculateMifflinStJeor("masculino", 80, 180, 30, "sedentario", "manutencao");
    assert.strictEqual(rMan.proteins_limit_g, 128);
    assert.strictEqual(rMan.fat_limit_g, 64);
    assert.strictEqual(rMan.carbs_limit_g, 262);
});

test("Zero-State Initialization: getLocalDietData starts with 0 meals and clean initial state", () => {
    storageMock.clear();
    const data = getLocalDietData();
    assert.ok(Array.isArray(data.entries), "entries deve ser um array");
    assert.strictEqual(data.entries.length, 0, "entries deve iniciar 100% zerado ([])");
    assert.strictEqual(data.goals.water_goal_ml, 2730);
});

test("Profile persistence: saveUserProfile and getUserProfile", async () => {
    storageMock.clear();
    assert.strictEqual(getUserProfile(), null, "perfil inicial deve ser null");

    let eventDispatched = false;
    let eventDetail = null;
    globalThis.window.dispatchEvent = (evt) => {
        if (evt.type === "nutriscan:profile-saved") {
            eventDispatched = true;
            eventDetail = evt.detail;
        }
        return true;
    };

    let tourStarted = false;
    globalThis.window.NutriScanTour = {
        startTour: (force) => {
            tourStarted = true;
        },
    };

    const newProfile = {
        name: "Carlos",
        gender: "masculino",
        age: 28,
        weight_kg: 75,
        height_cm: 175,
        activity_level: "moderado",
        goal_type: "cutting",
    };

    await saveUserProfile(newProfile);

    // Verificação do storage
    const saved = getUserProfile();
    assert.ok(saved);
    assert.strictEqual(saved.name, "Carlos");
    assert.strictEqual(saved.weight_kg, 75);

    // Evento e Tour disparados
    assert.strictEqual(eventDispatched, true, "evento nutriscan:profile-saved deve ser emitido");
    assert.strictEqual(eventDetail.name, "Carlos");
    assert.strictEqual(tourStarted, true, "NutriScanTour.startTour deve ser invocado");

    // Dieta deve estar zerada
    const dietState = getLocalDietData();
    assert.strictEqual(dietState.entries.length, 0, "refeições devem estar zeradas após salvar perfil");
    assert.strictEqual(dietState.goals.weight_kg, 75);
    assert.strictEqual(dietState.goals.water_goal_ml, Math.round(75 * 35));
});

test("resetAllUserData clears today meals and water", async () => {
    storageMock.clear();
    // Injeta refeição de teste
    const state = getLocalDietData();
    state.entries.push({ id: 99, meal_type: "Café", product_name: "Ovo", kcal: 150 });
    storageMock.set("nutriscan_diet_state_v1", JSON.stringify(state));
    assert.strictEqual(getLocalDietData().entries.length, 1);

    await resetAllUserData();

    const resetState = getLocalDietData();
    assert.strictEqual(resetState.entries.length, 0, "entries deve ser resetado para []");
});
