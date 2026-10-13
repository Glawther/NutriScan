// Testes do leitor de tabela nutricional em JavaScript.
// Rodar com: node --test tests/js
const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const fs = require("node:fs");

const { parseLabel, forPortion } = require("../../app/static/js/label_parser.js");

const fixtures = JSON.parse(
    fs.readFileSync(path.join(__dirname, "..", "fixtures", "labels.json"), "utf8")
);

for (const fx of fixtures) {
    test(fx.name, () => {
        const parsed = parseLabel(fx.text);
        const e = fx.expect;
        assert.strictEqual(parsed.portion_g, e.portion_g, "porção");
        assert.strictEqual(parsed.unit, e.unit, "unidade");
        assert.strictEqual(parsed.has_100g_column, e.has_100g_column, "coluna 100 g");
        for (const [k, v] of Object.entries(e.per_portion)) {
            assert.ok(Math.abs(parsed.per_portion[k] - v) < 0.051, `porção.${k}: ${parsed.per_portion[k]} != ${v}`);
        }
        for (const [k, v] of Object.entries(e.per_100g)) {
            assert.ok(Math.abs(parsed.per_100g[k] - v) < 0.051, `100g.${k}: ${parsed.per_100g[k]} != ${v}`);
        }
        const res = forPortion(parsed, parsed.portion_g, {});
        assert.deepStrictEqual(res.anvisa_warnings, e.warnings);
    });
}

test("escala para a quantidade consumida", () => {
    const parsed = parseLabel(fixtures[0].text);
    const res = forPortion(parsed, 45, { daily_kcal_limit: 2000, proteins_limit_g: 150 });
    assert.strictEqual(res.consumed.kcal, 180);
    assert.strictEqual(res.consumed.proteins_g, 36);
    assert.strictEqual(res.daily_limit_impact_pct.kcal_pct, 9);
    assert.strictEqual(res.daily_limit_impact_pct.proteins_pct, 24);
    assert.strictEqual(res.scale_factor, 1.5);
});
