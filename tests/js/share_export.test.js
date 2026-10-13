// Unit tests for NutriScanShare module and offline sharing
// Run with: node --test tests/js/share_export.test.js
const test = require("node:test");
const assert = require("node:assert");

const shareModule = require("../../app/static/js/share_export.js");

test("NutriScanShare exports required methods", () => {
    assert.strictEqual(typeof shareModule.generateDailySummaryText, "function");
    assert.strictEqual(typeof shareModule.shareToWhatsApp, "function");
    assert.strictEqual(typeof shareModule.copyToClipboard, "function");
    assert.strictEqual(typeof shareModule.printDailyReport, "function");
});

test("generateDailySummaryText creates clean formatted WhatsApp text", () => {
    const summary = {
        goals: {
            daily_kcal_limit: 2200,
            proteins_limit_g: 160,
            carbs_limit_g: 220,
            fat_limit_g: 65,
            sodium_limit_mg: 2000,
        },
        consumed: {
            kcal: 1450,
            proteins_g: 120,
            carbohydrates_g: 150,
            fat_g: 40,
            sodium_mg: 1100,
        },
        entries: [
            { meal_type: "Almoço", product_name: "Frango com Arroz", portion_g: 350, kcal: 620, proteins_g: 50, carbohydrates_g: 60, fat_g: 12 },
            { meal_type: "Lanche", product_name: "Whey Protein", portion_g: 45, kcal: 165, proteins_g: 36, carbohydrates_g: 4, fat_g: 2 },
        ]
    };
    const waterData = { amount_ml: 1800, goal_ml: 2625 };

    const text = shareModule.generateDailySummaryText(summary, waterData, "2026-10-13");
    assert.ok(text.includes("NutriScan - Resumo da Dieta (13/10/2026)"));
    assert.ok(text.includes("1450 / 2200 kcal"));
    assert.ok(text.includes("750 kcal restantes"));
    assert.ok(text.includes("1800 ml / 2625 ml"));
    assert.ok(text.includes("Almoço:"));
    assert.ok(text.includes("Frango com Arroz"));
    assert.ok(text.includes("Whey Protein"));
});

test("generateDailySummaryText handles zero entries gracefully", () => {
    const summary = {
        goals: { daily_kcal_limit: 2000 },
        consumed: { kcal: 0, proteins_g: 0, carbohydrates_g: 0, fat_g: 0, sodium_mg: 0 },
        entries: []
    };
    const waterData = { amount_ml: 0, goal_ml: 2500 };

    const text = shareModule.generateDailySummaryText(summary, waterData, "2026-10-13");
    assert.ok(text.includes("0 / 2000 kcal"));
    assert.ok(text.includes("Nenhuma refeição registrada"));
    assert.ok(text.includes("0 ml / 2500 ml"));
});
