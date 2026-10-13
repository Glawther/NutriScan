/*
 * Leitor de tabela nutricional brasileira (RDC 429/2020 e modelo antigo).
 *
 * Recebe o texto devolvido pelo OCR (Tesseract.js no navegador, ML Kit no Android)
 * e devolve os valores por porção e por 100 g. A mesma lógica existe em Python em
 * app/engine/label_ocr.py; os dois lados usam os casos de teste de tests/fixtures/labels.
 *
 * Funciona como módulo CommonJS (testes com node) e como script de navegador
 * (expõe window.NutriLabel).
 */
(function (root) {
    "use strict";

    const NUMBER_RE = /(\d+(?:[.,]\d+)?)/g;

    // Ordem importa: linhas de gordura saturada/trans precisam ser testadas antes de "gorduras totais".
    const FIELDS = [
        { key: "kcal", test: (l) => /valor\s*energ|energia|calorias/.test(l) },
        { key: "added_sugars_g", test: (l) => /a[çc][úu]?u?cares?\s*adicionad/.test(l) },
        { key: "sugars_g", test: (l) => /a[çc][úu]?u?cares?/.test(l) },
        { key: "carbohydrates_g", test: (l) => /carboidrato/.test(l) },
        { key: "proteins_g", test: (l) => /prote[íi]na/.test(l) },
        { key: "saturated_fat_g", test: (l) => /(?<!in)saturad/.test(l) },
        { key: "trans_fat_g", test: (l) => /gordura.*trans|\btrans\b/.test(l) },
        { key: "fat_g", test: (l) => /gordura|lip[íi]dio/.test(l) && !/mono|poli|insaturad/.test(l) },
        { key: "fiber_g", test: (l) => /fibra/.test(l) },
        { key: "sodium_mg", test: (l) => /s[óo]dio/.test(l) },
    ];

    const ALL_KEYS = FIELDS.map((f) => f.key);

    function toNumber(raw) {
        return parseFloat(String(raw).replace(",", "."));
    }

    function round1(v) {
        return Math.round(v * 10) / 10;
    }

    function fieldForLine(lower) {
        for (const f of FIELDS) {
            if (f.test(lower)) return f.key;
        }
        return null;
    }

    function valuesFromLine(lower, key) {
        let s = lower
            .replace(/\((?:k?cal|kj|g|mg|ml)\)/g, " ")
            .replace(/\d+(?:[.,]\d+)?\s*kj/g, " ")
            .replace(/\d+(?:[.,]\d+)?\s*%/g, " ");

        if (key === "kcal") {
            const kcal = [...s.matchAll(/(\d+(?:[.,]\d+)?)\s*kcal/g)].map((m) => toNumber(m[1]));
            if (kcal.length) return kcal;
        }
        // Ignora números colados em letras (ex.: "ômega3", "b12").
        s = s.replace(/[a-zà-ú]\d+/g, " ");
        return [...s.matchAll(NUMBER_RE)].map((m) => toNumber(m[1]));
    }

    function detectPortion(text) {
        const m = text.match(/por[çc][ãa]o\s*(?:de|:)?\s*:?\s*(\d+(?:[.,]\d+)?)\s*(g|ml)\b/i);
        if (!m) return { grams: null, unit: "g" };
        return { grams: toNumber(m[1]), unit: m[2].toLowerCase() };
    }

    function mentions100Column(lines) {
        return lines.some((line) => {
            const l = line.toLowerCase();
            if (/por[çc][ãa]o/.test(l)) return false;
            return /\b100\s*(g|ml)\b/.test(l);
        });
    }

    function median(values) {
        const sorted = [...values].sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
    }

    /**
     * Interpreta o texto de uma tabela nutricional.
     * @param {string} rawText texto do OCR
     * @returns {{portion_g:number, portion_detected:boolean, unit:string, has_100g_column:boolean,
     *            per_portion:Object, per_100g:Object, fields_found:string[], fields_missing:string[]}}
     */
    function parseLabel(rawText) {
        const text = String(rawText || "");
        const lines = text
            .split(/\r?\n/)
            .map((l) => l.trim())
            .filter(Boolean);

        const portion = detectPortion(text);
        const rows = {};
        for (const line of lines) {
            const lower = line.toLowerCase();
            if (/por[çc][ãa]o/.test(lower) && !/valor|prote|carbo|gordura|s[óo]dio|fibra/.test(lower)) continue;
            const key = fieldForLine(lower);
            if (!key || rows[key]) continue;
            const values = valuesFromLine(lower, key);
            if (values.length) rows[key] = values;
        }

        const portionG = portion.grams && portion.grams > 0 ? portion.grams : 100;

        // Coluna de 100 g: cabeçalho explícito ou proporção entre as duas primeiras colunas
        // batendo com o tamanho da porção.
        let has100 = mentions100Column(lines);
        if (!has100 && portion.grams && portion.grams !== 100) {
            const expected = portion.grams / 100;
            const ratios = Object.values(rows)
                .filter((v) => v.length >= 2 && v[0] > 0)
                .map((v) => v[1] / v[0]);
            if (ratios.length >= 2 && Math.abs(median(ratios) - expected) <= expected * 0.15) {
                has100 = true;
            }
        }

        const perPortion = {};
        const per100 = {};
        for (const key of ALL_KEYS) {
            const v = rows[key];
            if (!v) {
                perPortion[key] = 0;
                per100[key] = 0;
                continue;
            }
            if (has100) {
                per100[key] = v[0];
                perPortion[key] = v.length >= 2 ? v[1] : (v[0] * portionG) / 100;
            } else {
                perPortion[key] = v[0];
                per100[key] = (v[0] * 100) / portionG;
            }
        }

        if (!rows.kcal && (rows.carbohydrates_g || rows.proteins_g || rows.fat_g)) {
            perPortion.kcal = perPortion.carbohydrates_g * 4 + perPortion.proteins_g * 4 + perPortion.fat_g * 9;
            per100.kcal = per100.carbohydrates_g * 4 + per100.proteins_g * 4 + per100.fat_g * 9;
        }

        for (const key of ALL_KEYS) {
            perPortion[key] = round1(perPortion[key]);
            per100[key] = round1(per100[key]);
        }

        const found = ALL_KEYS.filter((k) => rows[k]);
        return {
            portion_g: round1(portionG),
            portion_detected: Boolean(portion.grams),
            unit: portion.unit,
            has_100g_column: has100,
            per_portion: perPortion,
            per_100g: per100,
            fields_found: found,
            fields_missing: ["kcal", "carbohydrates_g", "proteins_g", "fat_g"].filter((k) => !rows[k]),
        };
    }

    /** Alertas frontais da ANVISA (RDC 429/2020), calculados por 100 g ou 100 ml. */
    function anvisaWarnings(per100, isBeverage, hasAddedSugarRow) {
        const lim = isBeverage
            ? { sugar: 7.5, sat: 3, sodium: 300 }
            : { sugar: 15, sat: 6, sodium: 600 };
        const list = [];
        if (hasAddedSugarRow) {
            if ((per100.added_sugars_g || 0) >= lim.sugar) list.push("ALTO EM AÇÚCAR ADICIONADO");
        } else if ((per100.sugars_g || 0) >= lim.sugar) {
            list.push("ALTO EM AÇÚCAR (TOTAL)");
        }
        if ((per100.saturated_fat_g || 0) >= lim.sat) list.push("ALTO EM GORDURA SATURADA");
        if ((per100.sodium_mg || 0) >= lim.sodium) list.push("ALTO EM SÓDIO");
        return list;
    }

    /**
     * Escala a tabela para a quantidade consumida e calcula o peso na meta diária.
     * @param {ReturnType<typeof parseLabel>} parsed
     * @param {number} consumedG gramas ou ml consumidos
     * @param {Object} goals metas diárias (daily_kcal_limit, carbs_limit_g, ...)
     */
    function forPortion(parsed, consumedG, goals) {
        const grams = consumedG > 0 ? consumedG : parsed.portion_g;
        const factor = grams / 100;
        const p = parsed.per_100g;
        const consumed = {
            portion_g: round1(grams),
            kcal: round1(p.kcal * factor),
            carbohydrates_g: round1(p.carbohydrates_g * factor),
            sugars_g: round1(p.sugars_g * factor),
            proteins_g: round1(p.proteins_g * factor),
            fat_g: round1(p.fat_g * factor),
            saturated_fat_g: round1(p.saturated_fat_g * factor),
            fiber_g: round1(p.fiber_g * factor),
            sodium_mg: round1(p.sodium_mg * factor),
        };
        const g = goals || {};
        const pct = (v, lim) => (lim > 0 ? round1((v / lim) * 100) : 0);
        return {
            consumed,
            scale_factor: Math.round((grams / parsed.portion_g) * 100) / 100,
            daily_limit_impact_pct: {
                kcal_pct: pct(consumed.kcal, g.daily_kcal_limit || 2000),
                carbohydrates_pct: pct(consumed.carbohydrates_g, g.carbs_limit_g || 200),
                proteins_pct: pct(consumed.proteins_g, g.proteins_limit_g || 150),
                fat_pct: pct(consumed.fat_g, g.fat_limit_g || 65),
                sodium_pct: pct(consumed.sodium_mg, g.sodium_limit_mg || 2000),
            },
            anvisa_warnings: anvisaWarnings(p, parsed.unit === "ml", parsed.fields_found.includes("added_sugars_g")),
        };
    }

    const api = { parseLabel, forPortion, anvisaWarnings };
    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    } else {
        root.NutriLabel = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
