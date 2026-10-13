// Unit tests for Food Plate Scanner & Micronutrients Dashboard (NutriScanPlateScanner)
// Run with: node --test tests/js/plate_scanner.test.js
const test = require("node:test");
const assert = require("node:assert");

const plateScanner = require("../../app/static/js/plate_scanner.js");

test("NutriScanPlateScanner exports required methods, catalogs and IDR constants", () => {
    assert.ok(plateScanner);
    assert.strictEqual(typeof plateScanner.calculatePlateTotals, "function");
    assert.strictEqual(typeof plateScanner.loadPreset, "function");
    assert.strictEqual(typeof plateScanner.updateItemGrams, "function");
    assert.strictEqual(typeof plateScanner.removeItem, "function");
    assert.strictEqual(typeof plateScanner.addItem, "function");
    assert.strictEqual(typeof plateScanner.addPlateToDiet, "function");
    assert.ok(plateScanner.ANVISA_IDR);
    assert.strictEqual(plateScanner.ANVISA_IDR.calcio_mg, 1000);
    assert.strictEqual(plateScanner.ANVISA_IDR.ferro_mg, 14);
    assert.strictEqual(plateScanner.ANVISA_IDR.potassio_mg, 3500);
    assert.strictEqual(plateScanner.ANVISA_IDR.magnesio_mg, 260);
    assert.strictEqual(plateScanner.ANVISA_IDR.vitamina_c_mg, 100);
    assert.strictEqual(plateScanner.ANVISA_IDR.sodio_mg, 2000);
    assert.ok(Array.isArray(plateScanner.TACO_DATABASE));
    assert.ok(plateScanner.TACO_DATABASE.length >= 10);
});

test("calculatePlateTotals accurately scales macros and calculates 6 key micronutrients", () => {
    // 100g de arroz branco + 100g de feijão carioca
    const items = [
        { taco_id: "arroz_branco", name: "Arroz Branco Cozido", grams: 100 },
        { taco_id: "feijao_carioca", name: "Feijão Carioca Cozido", grams: 100 },
    ];

    const result = plateScanner.calculatePlateTotals(items);
    assert.strictEqual(result.totals.total_grams, 200);
    assert.strictEqual(result.totals.kcal, 204); // 128 + 76
    assert.strictEqual(result.totals.carbs_g, 41.7); // 28.1 + 13.6
    assert.strictEqual(result.totals.prot_g, 7.3); // 2.5 + 4.8
    assert.strictEqual(result.totals.fat_g, 0.7); // 0.2 + 0.5

    // Micronutrientes
    assert.strictEqual(result.totals.micros.calcio_mg, 31); // 4 + 27
    assert.strictEqual(result.totals.micros.ferro_mg, 1.6); // 0.3 + 1.3
    assert.strictEqual(result.totals.micros.potassio_mg, 290); // 35 + 255
    assert.strictEqual(result.totals.micros.magnesio_mg, 48); // 6 + 42
    assert.strictEqual(result.totals.micros.sodio_mg, 3); // 1 + 2

    // Micronutrient dashboard format
    assert.strictEqual(result.micronutrients.length, 6);
    const calcio = result.micronutrients.find((m) => m.key === "calcio_mg");
    assert.ok(calcio);
    assert.strictEqual(calcio.unit, "mg");
    assert.strictEqual(calcio.pct, 3); // 31 / 1000 = 3%
});

test("Recalculation immediately scales when item grams change", () => {
    // Duplicar quantidade de salmão grelhado de 100g para 200g
    const items = [{ taco_id: "salmao_grelhado", name: "Salmão Grelhado", grams: 200 }];
    const result = plateScanner.calculatePlateTotals(items);

    assert.strictEqual(result.totals.total_grams, 200);
    assert.strictEqual(result.totals.kcal, 412); // 206 * 2
    assert.strictEqual(result.totals.prot_g, 44.2); // 22.1 * 2
    assert.strictEqual(result.totals.fat_g, 24.6); // 12.3 * 2
    assert.strictEqual(result.totals.micros.potassio_mg, 980); // 490 * 2
});

test("Plate presets contain predefined items and valid bounding boxes", () => {
    const presets = plateScanner.PLATE_PRESETS;
    assert.ok(presets.prato_feito);
    assert.ok(presets.omelete_fitness);
    assert.ok(presets.salmao_legumes);
    assert.ok(presets.acai_completo);

    assert.ok(presets.prato_feito.items.length >= 4);
    for (const item of presets.prato_feito.items) {
        assert.ok(item.box);
        assert.ok(typeof item.box.top === "number");
        assert.ok(typeof item.box.left === "number");
    }
});

test("updateItemGrams safely clamps extreme inputs (negative, zero, >2000g, NaN)", () => {
    plateScanner.loadPreset("prato_feito");
    // Test negative delta clamping to 0
    plateScanner.updateItemGrams(0, -9999, true);
    let state = plateScanner.getState();
    assert.strictEqual(state.items[0].grams, 0);

    // Test extreme value > 2000g clamping to 2000
    plateScanner.updateItemGrams(0, 9999, false);
    state = plateScanner.getState();
    assert.strictEqual(state.items[0].grams, 2000);

    // Test invalid NaN string clamping to 0
    plateScanner.updateItemGrams(0, "invalid_text", false);
    state = plateScanner.getState();
    assert.strictEqual(state.items[0].grams, 0);

    // Test normal addition
    plateScanner.updateItemGrams(0, 150, false);
    state = plateScanner.getState();
    assert.strictEqual(state.items[0].grams, 150);
});
