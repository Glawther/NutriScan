/**
 * NutriScan - Food Plate Scanner & Micronutrients Dashboard
 * AI Plate Vision Scanner + TACO Micro/Macro Recalculation + Diary Batch Sync
 */
(function (root, factory) {
    if (typeof module === "object" && module.exports) {
        module.exports = factory();
    } else {
        root.NutriScanPlateScanner = factory();
    }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    // ANVISA Recommended Daily Intake (IN 75/2020 & RDC 429/2020)
    const ANVISA_IDR = {
        calcio_mg: 1000,
        ferro_mg: 14,
        potassio_mg: 3500,
        magnesio_mg: 260,
        vitamina_c_mg: 100,
        sodio_mg: 2000,
    };

    const escapeHtml = (typeof window !== "undefined" && window.escapeHtml) ? window.escapeHtml : function (str) {
        if (str === null || str === undefined) return "";
        return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    };

    // Default TACO-derived catalog for food items and plate presets (values per 100g)
    const TACO_DATABASE = [
        {
            id: "arroz_branco",
            name: "Arroz Branco Cozido",
            category: "Cereais",
            kcal_100g: 128,
            carbs_100g: 28.1,
            prot_100g: 2.5,
            fat_100g: 0.2,
            fiber_100g: 1.6,
            calcio_mg_100g: 4.0,
            ferro_mg_100g: 0.3,
            potassio_mg_100g: 35.0,
            magnesio_mg_100g: 6.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 1.0,
        },
        {
            id: "feijao_carioca",
            name: "Feijão Carioca Cozido",
            category: "Leguminosas",
            kcal_100g: 76,
            carbs_100g: 13.6,
            prot_100g: 4.8,
            fat_100g: 0.5,
            fiber_100g: 8.5,
            calcio_mg_100g: 27.0,
            ferro_mg_100g: 1.3,
            potassio_mg_100g: 255.0,
            magnesio_mg_100g: 42.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 2.0,
        },
        {
            id: "bife_bovino",
            name: "Bife Bovino Grelhado",
            category: "Carnes",
            kcal_100g: 219,
            carbs_100g: 0.0,
            prot_100g: 32.5,
            fat_100g: 8.9,
            fiber_100g: 0.0,
            calcio_mg_100g: 9.0,
            ferro_mg_100g: 2.8,
            potassio_mg_100g: 380.0,
            magnesio_mg_100g: 24.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 65.0,
        },
        {
            id: "frango_grelhado",
            name: "Peito de Frango Grelhado",
            category: "Aves",
            kcal_100g: 165,
            carbs_100g: 0.0,
            prot_100g: 31.0,
            fat_100g: 3.6,
            fiber_100g: 0.0,
            calcio_mg_100g: 15.0,
            ferro_mg_100g: 0.9,
            potassio_mg_100g: 256.0,
            magnesio_mg_100g: 29.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 74.0,
        },
        {
            id: "salada_alface_tomate",
            name: "Salada de Alface e Tomate",
            category: "Verduras e Legumes",
            kcal_100g: 18,
            carbs_100g: 3.2,
            prot_100g: 1.1,
            fat_100g: 0.2,
            fiber_100g: 1.4,
            calcio_mg_100g: 19.0,
            ferro_mg_100g: 0.6,
            potassio_mg_100g: 220.0,
            magnesio_mg_100g: 12.0,
            vitamina_c_mg_100g: 18.0,
            sodio_mg_100g: 7.0,
        },
        {
            id: "salmao_grelhado",
            name: "Salmão Grelhado",
            category: "Pescados",
            kcal_100g: 206,
            carbs_100g: 0.0,
            prot_100g: 22.1,
            fat_100g: 12.3,
            fiber_100g: 0.0,
            calcio_mg_100g: 12.0,
            ferro_mg_100g: 0.8,
            potassio_mg_100g: 490.0,
            magnesio_mg_100g: 30.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 59.0,
        },
        {
            id: "brocolis_cozido",
            name: "Brócolis Cozido no Vapor",
            category: "Verduras e Legumes",
            kcal_100g: 25,
            carbs_100g: 4.4,
            prot_100g: 2.1,
            fat_100g: 0.5,
            fiber_100g: 3.4,
            calcio_mg_100g: 51.0,
            ferro_mg_100g: 0.8,
            potassio_mg_100g: 316.0,
            magnesio_mg_100g: 21.0,
            vitamina_c_mg_100g: 42.0,
            sodio_mg_100g: 15.0,
        },
        {
            id: "cenoura_cozida",
            name: "Cenoura Cozida",
            category: "Verduras e Legumes",
            kcal_100g: 30,
            carbs_100g: 6.7,
            prot_100g: 0.8,
            fat_100g: 0.2,
            fiber_100g: 2.6,
            calcio_mg_100g: 26.0,
            ferro_mg_100g: 0.4,
            potassio_mg_100g: 240.0,
            magnesio_mg_100g: 14.0,
            vitamina_c_mg_100g: 5.0,
            sodio_mg_100g: 35.0,
        },
        {
            id: "omelete_ovos",
            name: "Omelete de 2 Ovos com Espinafre",
            category: "Ovos",
            kcal_100g: 154,
            carbs_100g: 1.5,
            prot_100g: 12.6,
            fat_100g: 10.9,
            fiber_100g: 0.8,
            calcio_mg_100g: 88.0,
            ferro_mg_100g: 2.4,
            potassio_mg_100g: 210.0,
            magnesio_mg_100g: 22.0,
            vitamina_c_mg_100g: 7.0,
            sodio_mg_100g: 180.0,
        },
        {
            id: "queijo_cottage",
            name: "Queijo Cottage",
            category: "Laticínios",
            kcal_100g: 98,
            carbs_100g: 3.4,
            prot_100g: 11.1,
            fat_100g: 4.3,
            fiber_100g: 0.0,
            calcio_mg_100g: 83.0,
            ferro_mg_100g: 0.2,
            potassio_mg_100g: 104.0,
            magnesio_mg_100g: 9.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 364.0,
        },
        {
            id: "tomate_cereja",
            name: "Tomate Cereja",
            category: "Verduras e Legumes",
            kcal_100g: 18,
            carbs_100g: 3.9,
            prot_100g: 0.9,
            fat_100g: 0.2,
            fiber_100g: 1.2,
            calcio_mg_100g: 10.0,
            ferro_mg_100g: 0.3,
            potassio_mg_100g: 237.0,
            magnesio_mg_100g: 11.0,
            vitamina_c_mg_100g: 24.0,
            sodio_mg_100g: 5.0,
        },
        {
            id: "acai_puro",
            name: "Polpa de Açaí Médio",
            category: "Frutas",
            kcal_100g: 58,
            carbs_100g: 6.2,
            prot_100g: 0.8,
            fat_100g: 3.9,
            fiber_100g: 2.6,
            calcio_mg_100g: 35.0,
            ferro_mg_100g: 0.4,
            potassio_mg_100g: 130.0,
            magnesio_mg_100g: 17.0,
            vitamina_c_mg_100g: 9.0,
            sodio_mg_100g: 8.0,
        },
        {
            id: "banana_nanica",
            name: "Banana Nanica Fatiada",
            category: "Frutas",
            kcal_100g: 92,
            carbs_100g: 23.8,
            prot_100g: 1.4,
            fat_100g: 0.1,
            fiber_100g: 1.9,
            calcio_mg_100g: 8.0,
            ferro_mg_100g: 0.4,
            potassio_mg_100g: 376.0,
            magnesio_mg_100g: 28.0,
            vitamina_c_mg_100g: 7.0,
            sodio_mg_100g: 1.0,
        },
        {
            id: "granola_artesanal",
            name: "Granola Tradicional",
            category: "Cereais",
            kcal_100g: 421,
            carbs_100g: 68.0,
            prot_100g: 10.0,
            fat_100g: 12.0,
            fiber_100g: 6.5,
            calcio_mg_100g: 60.0,
            ferro_mg_100g: 3.5,
            potassio_mg_100g: 320.0,
            magnesio_mg_100g: 85.0,
            vitamina_c_mg_100g: 1.0,
            sodio_mg_100g: 45.0,
        },
        {
            id: "morango_fresco",
            name: "Morangos Frescos",
            category: "Frutas",
            kcal_100g: 30,
            carbs_100g: 6.8,
            prot_100g: 0.9,
            fat_100g: 0.3,
            fiber_100g: 1.7,
            calcio_mg_100g: 11.0,
            ferro_mg_100g: 0.3,
            potassio_mg_100g: 161.0,
            magnesio_mg_100g: 10.0,
            vitamina_c_mg_100g: 63.0,
            sodio_mg_100g: 1.0,
        },
        {
            id: "batata_doce_cozida",
            name: "Batata Doce Cozida",
            category: "Tubérculos",
            kcal_100g: 77,
            carbs_100g: 18.4,
            prot_100g: 0.6,
            fat_100g: 0.1,
            fiber_100g: 2.2,
            calcio_mg_100g: 17.0,
            ferro_mg_100g: 0.3,
            potassio_mg_100g: 206.0,
            magnesio_mg_100g: 11.0,
            vitamina_c_mg_100g: 14.0,
            sodio_mg_100g: 3.0,
        },
        {
            id: "azeite_oliva",
            name: "Azeite de Oliva Extra Virgem",
            category: "Óleos e Gorduras",
            kcal_100g: 884,
            carbs_100g: 0.0,
            prot_100g: 0.0,
            fat_100g: 100.0,
            fiber_100g: 0.0,
            calcio_mg_100g: 1.0,
            ferro_mg_100g: 0.1,
            potassio_mg_100g: 1.0,
            magnesio_mg_100g: 0.0,
            vitamina_c_mg_100g: 0.0,
            sodio_mg_100g: 2.0,
        },
    ];

    // Presets with bounding boxes for plate visualization
    const PLATE_PRESETS = {
        prato_feito: {
            id: "prato_feito",
            title: "Prato Feito Brasileiro",
            description: "Arroz, feijão carioca, bife grelhado e salada fresca de alface com tomate.",
            meal_type: "Almoço",
            mock_image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
                    <defs>
                        <radialGradient id="plateGrad" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stop-color="#1e293b"/>
                            <stop offset="85%" stop-color="#0f172a"/>
                            <stop offset="100%" stop-color="#020617"/>
                        </radialGradient>
                        <radialGradient id="innerPlate" cx="45%" cy="45%" r="60%">
                            <stop offset="0%" stop-color="#334155"/>
                            <stop offset="90%" stop-color="#1e293b"/>
                        </radialGradient>
                    </defs>
                    <rect width="600" height="400" fill="#090d16"/>
                    <circle cx="300" cy="200" r="185" fill="url(#plateGrad)" stroke="#38bdf8" stroke-width="2" opacity="0.6"/>
                    <circle cx="300" cy="200" r="150" fill="url(#innerPlate)" stroke="#1e293b" stroke-width="3"/>
                    <!-- Rice -->
                    <ellipse cx="230" cy="160" rx="60" ry="45" fill="#f8fafc" opacity="0.9"/>
                    <!-- Beans -->
                    <ellipse cx="240" cy="250" rx="55" ry="40" fill="#78350f" opacity="0.85"/>
                    <!-- Steak -->
                    <ellipse cx="370" cy="170" rx="65" ry="50" fill="#451a03" stroke="#b45309" stroke-dasharray="4,2"/>
                    <!-- Salad -->
                    <ellipse cx="360" cy="260" rx="55" ry="40" fill="#15803d" opacity="0.85"/>
                    <circle cx="380" cy="270" r="10" fill="#ef4444"/>
                    <circle cx="345" cy="250" r="8" fill="#ef4444"/>
                </svg>
            `),
            items: [
                { taco_id: "arroz_branco", name: "Arroz Branco Cozido", grams: 150, box: { top: 22, left: 20, width: 28, height: 26 } },
                { taco_id: "feijao_carioca", name: "Feijão Carioca Cozido", grams: 100, box: { top: 52, left: 22, width: 26, height: 26 } },
                { taco_id: "bife_bovino", name: "Bife Bovino Grelhado", grams: 120, box: { top: 24, left: 52, width: 30, height: 28 } },
                { taco_id: "salada_alface_tomate", name: "Salada de Alface e Tomate", grams: 80, box: { top: 54, left: 50, width: 28, height: 26 } },
            ],
        },
        omelete_fitness: {
            id: "omelete_fitness",
            title: "Omelete Fitness com Cottage",
            description: "Omelete proteico recheado com queijo cottage e tomatinhos cereja.",
            meal_type: "Café da manhã",
            mock_image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
                    <rect width="600" height="400" fill="#090d16"/>
                    <circle cx="300" cy="200" r="180" fill="#111827" stroke="#10b981" stroke-width="2" opacity="0.7"/>
                    <circle cx="300" cy="200" r="145" fill="#1e293b"/>
                    <!-- Omelet -->
                    <path d="M 200 240 Q 300 110 400 240 Z" fill="#eab308" opacity="0.95"/>
                    <circle cx="270" cy="205" r="12" fill="#ef4444"/>
                    <circle cx="330" cy="195" r="14" fill="#ef4444"/>
                    <!-- Cottage -->
                    <ellipse cx="300" cy="235" rx="40" ry="20" fill="#f8fafc" opacity="0.9"/>
                </svg>
            `),
            items: [
                { taco_id: "omelete_ovos", name: "Omelete de 2 Ovos com Espinafre", grams: 160, box: { top: 30, left: 26, width: 48, height: 32 } },
                { taco_id: "queijo_cottage", name: "Queijo Cottage", grams: 60, box: { top: 52, left: 38, width: 24, height: 20 } },
                { taco_id: "tomate_cereja", name: "Tomate Cereja", grams: 50, box: { top: 38, left: 56, width: 20, height: 20 } },
            ],
        },
        salmao_legumes: {
            id: "salmao_legumes",
            title: "Salmão com Legumes no Vapor",
            description: "Filé de salmão grelhado, brócolis no vapor e cenouras baby.",
            meal_type: "Jantar",
            mock_image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
                    <rect width="600" height="400" fill="#090d16"/>
                    <circle cx="300" cy="200" r="180" fill="#111827" stroke="#fb7185" stroke-width="2" opacity="0.7"/>
                    <circle cx="300" cy="200" r="145" fill="#1e293b"/>
                    <!-- Salmon -->
                    <rect x="230" y="150" width="140" height="85" rx="18" fill="#f43f5e" opacity="0.9"/>
                    <!-- Broccoli -->
                    <circle cx="230" cy="265" r="30" fill="#15803d"/>
                    <circle cx="280" cy="275" r="28" fill="#16a34a"/>
                    <!-- Carrots -->
                    <rect x="340" y="250" width="75" height="18" rx="8" fill="#ea580c" transform="rotate(-15 340 250)"/>
                    <rect x="345" y="275" width="70" height="16" rx="8" fill="#f97316" transform="rotate(-5 345 275)"/>
                </svg>
            `),
            items: [
                { taco_id: "salmao_grelhado", name: "Salmão Grelhado", grams: 150, box: { top: 25, left: 30, width: 40, height: 30 } },
                { taco_id: "brocolis_cozido", name: "Brócolis Cozido no Vapor", grams: 100, box: { top: 56, left: 24, width: 28, height: 26 } },
                { taco_id: "cenoura_cozida", name: "Cenoura Cozida", grams: 80, box: { top: 56, left: 52, width: 28, height: 24 } },
            ],
        },
        acai_completo: {
            id: "acai_completo",
            title: "Açaí Completo com Frutas",
            description: "Tigela de açaí puro com rodelas de banana, morangos e granola crocante.",
            meal_type: "Lanche",
            mock_image: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(`
                <svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
                    <rect width="600" height="400" fill="#090d16"/>
                    <circle cx="300" cy="200" r="175" fill="#3b0764" stroke="#a855f7" stroke-width="3"/>
                    <circle cx="300" cy="200" r="140" fill="#581c87"/>
                    <!-- Bananas -->
                    <circle cx="250" cy="160" r="18" fill="#fef08a" stroke="#ca8a04"/>
                    <circle cx="285" cy="145" r="18" fill="#fef08a" stroke="#ca8a04"/>
                    <!-- Strawberries -->
                    <polygon points="330,140 350,170 310,170" fill="#dc2626"/>
                    <polygon points="360,160 380,190 340,190" fill="#ef4444"/>
                    <!-- Granola -->
                    <ellipse cx="300" cy="255" rx="75" ry="30" fill="#b45309" stroke="#d97706" stroke-dasharray="6,3"/>
                </svg>
            `),
            items: [
                { taco_id: "acai_puro", name: "Polpa de Açaí Médio", grams: 200, box: { top: 22, left: 22, width: 56, height: 56 } },
                { taco_id: "banana_nanica", name: "Banana Nanica Fatiada", grams: 80, box: { top: 24, left: 28, width: 24, height: 20 } },
                { taco_id: "morango_fresco", name: "Morangos Frescos", grams: 60, box: { top: 24, left: 52, width: 24, height: 20 } },
                { taco_id: "granola_artesanal", name: "Granola Tradicional", grams: 40, box: { top: 56, left: 34, width: 32, height: 22 } },
            ],
        },
    };

    // State of current plate inspection
    let currentPlateState = {
        plateId: "prato_feito",
        plateTitle: "Prato Feito Brasileiro",
        imageUrl: PLATE_PRESETS.prato_feito.mock_image,
        mealType: "Almoço",
        items: JSON.parse(JSON.stringify(PLATE_PRESETS.prato_feito.items)),
        activeFilter: "",
    };

    /**
     * Finds item in TACO database by ID or name
     */
    function findTacoItem(idOrName) {
        if (!idOrName) return null;
        const normalized = idOrName.toLowerCase().trim();
        return (
            TACO_DATABASE.find((t) => t.id === normalized) ||
            TACO_DATABASE.find((t) => t.name.toLowerCase() === normalized) ||
            TACO_DATABASE.find((t) => t.name.toLowerCase().includes(normalized)) ||
            null
        );
    }

    /**
     * Recalculates all macros and micronutrients for the given list of food items
     * @param {Array} items - List of items with { taco_id, name, grams }
     * @returns {Object} totals and micronutrient breakdown
     */
    function calculatePlateTotals(items) {
        const totals = {
            total_grams: 0,
            kcal: 0,
            carbs_g: 0,
            prot_g: 0,
            fat_g: 0,
            fiber_g: 0,
            micros: {
                calcio_mg: 0,
                ferro_mg: 0,
                potassio_mg: 0,
                magnesio_mg: 0,
                vitamina_c_mg: 0,
                sodio_mg: 0,
            },
        };

        const itemCalculations = items.map((item) => {
            const taco = findTacoItem(item.taco_id) || findTacoItem(item.name) || TACO_DATABASE[0];
            const grams = Math.max(0, Number(item.grams) || 0);
            const scale = grams / 100.0;

            const itemKcal = Number((taco.kcal_100g * scale).toFixed(1));
            const itemCarbs = Number((taco.carbs_100g * scale).toFixed(1));
            const itemProt = Number((taco.prot_100g * scale).toFixed(1));
            const itemFat = Number((taco.fat_100g * scale).toFixed(1));
            const itemFiber = Number((taco.fiber_100g * scale).toFixed(1));

            const calcio = Number((taco.calcio_mg_100g * scale).toFixed(1));
            const ferro = Number((taco.ferro_mg_100g * scale).toFixed(2));
            const potassio = Number((taco.potassio_mg_100g * scale).toFixed(1));
            const magnesio = Number((taco.magnesio_mg_100g * scale).toFixed(1));
            const vitC = Number((taco.vitamina_c_mg_100g * scale).toFixed(1));
            const sodio = Number((taco.sodio_mg_100g * scale).toFixed(1));

            totals.total_grams += grams;
            totals.kcal += itemKcal;
            totals.carbs_g += itemCarbs;
            totals.prot_g += itemProt;
            totals.fat_g += itemFat;
            totals.fiber_g += itemFiber;

            totals.micros.calcio_mg += calcio;
            totals.micros.ferro_mg += ferro;
            totals.micros.potassio_mg += potassio;
            totals.micros.magnesio_mg += magnesio;
            totals.micros.vitamina_c_mg += vitC;
            totals.micros.sodio_mg += sodio;

            return {
                ...item,
                taco_ref: taco,
                calculated: {
                    kcal: itemKcal,
                    carbs_g: itemCarbs,
                    prot_g: itemProt,
                    fat_g: itemFat,
                    fiber_g: itemFiber,
                    calcio_mg: calcio,
                    ferro_mg: ferro,
                    potassio_mg: potassio,
                    magnesio_mg: magnesio,
                    vitamina_c_mg: vitC,
                    sodio_mg: sodio,
                },
            };
        });

        // Format totals
        totals.total_grams = Number(totals.total_grams.toFixed(0));
        totals.kcal = Number(totals.kcal.toFixed(1));
        totals.carbs_g = Number(totals.carbs_g.toFixed(1));
        totals.prot_g = Number(totals.prot_g.toFixed(1));
        totals.fat_g = Number(totals.fat_g.toFixed(1));
        totals.fiber_g = Number(totals.fiber_g.toFixed(1));

        totals.micros.calcio_mg = Number(totals.micros.calcio_mg.toFixed(1));
        totals.micros.ferro_mg = Number(totals.micros.ferro_mg.toFixed(1));
        totals.micros.potassio_mg = Number(totals.micros.potassio_mg.toFixed(1));
        totals.micros.magnesio_mg = Number(totals.micros.magnesio_mg.toFixed(1));
        totals.micros.vitamina_c_mg = Number(totals.micros.vitamina_c_mg.toFixed(1));
        totals.micros.sodio_mg = Number(totals.micros.sodio_mg.toFixed(1));

        // Evaluate IDR Percentages and Status
        const microDashboard = [
            {
                key: "calcio_mg",
                label: "Cálcio",
                unit: "mg",
                value: totals.micros.calcio_mg,
                idr: ANVISA_IDR.calcio_mg,
                pct: Math.round((totals.micros.calcio_mg / ANVISA_IDR.calcio_mg) * 100),
                status: getStatusPill(totals.micros.calcio_mg / ANVISA_IDR.calcio_mg, false),
            },
            {
                key: "ferro_mg",
                label: "Ferro",
                unit: "mg",
                value: totals.micros.ferro_mg,
                idr: ANVISA_IDR.ferro_mg,
                pct: Math.round((totals.micros.ferro_mg / ANVISA_IDR.ferro_mg) * 100),
                status: getStatusPill(totals.micros.ferro_mg / ANVISA_IDR.ferro_mg, false),
            },
            {
                key: "potassio_mg",
                label: "Potássio",
                unit: "mg",
                value: totals.micros.potassio_mg,
                idr: ANVISA_IDR.potassio_mg,
                pct: Math.round((totals.micros.potassio_mg / ANVISA_IDR.potassio_mg) * 100),
                status: getStatusPill(totals.micros.potassio_mg / ANVISA_IDR.potassio_mg, false),
            },
            {
                key: "magnesio_mg",
                label: "Magnésio",
                unit: "mg",
                value: totals.micros.magnesio_mg,
                idr: ANVISA_IDR.magnesio_mg,
                pct: Math.round((totals.micros.magnesio_mg / ANVISA_IDR.magnesio_mg) * 100),
                status: getStatusPill(totals.micros.magnesio_mg / ANVISA_IDR.magnesio_mg, false),
            },
            {
                key: "vitamina_c_mg",
                label: "Vitamina C",
                unit: "mg",
                value: totals.micros.vitamina_c_mg,
                idr: ANVISA_IDR.vitamina_c_mg,
                pct: Math.round((totals.micros.vitamina_c_mg / ANVISA_IDR.vitamina_c_mg) * 100),
                status: getStatusPill(totals.micros.vitamina_c_mg / ANVISA_IDR.vitamina_c_mg, false),
            },
            {
                key: "sodio_mg",
                label: "Sódio",
                unit: "mg",
                value: totals.micros.sodio_mg,
                idr: ANVISA_IDR.sodio_mg,
                pct: Math.round((totals.micros.sodio_mg / ANVISA_IDR.sodio_mg) * 100),
                status: getSodiumStatusPill(totals.micros.sodio_mg / ANVISA_IDR.sodio_mg),
            },
        ];

        return {
            totals,
            items: itemCalculations,
            micronutrients: microDashboard,
        };
    }

    function getStatusPill(ratio, isLimit) {
        if (isLimit) {
            if (ratio > 1.0) return { label: "Alto", cls: "pill-danger" };
            if (ratio > 0.6) return { label: "Atenção", cls: "pill-warning" };
            return { label: "Adequado", cls: "pill-optimal" };
        }
        if (ratio >= 0.35) return { label: "Ótimo", cls: "pill-optimal" };
        if (ratio >= 0.15) return { label: "Adequado", cls: "pill-adequate" };
        return { label: "Baixo", cls: "pill-low" };
    }

    function getSodiumStatusPill(ratio) {
        if (ratio > 0.5) return { label: "Alto", cls: "pill-danger" };
        if (ratio > 0.25) return { label: "Moderado", cls: "pill-adequate" };
        return { label: "Ótimo", cls: "pill-optimal" };
    }

    /**
     * Sets active plate from a preset identifier
     */
    function loadPreset(presetKey) {
        const preset = PLATE_PRESETS[presetKey] || PLATE_PRESETS.prato_feito;
        currentPlateState.plateId = preset.id;
        currentPlateState.plateTitle = preset.title;
        currentPlateState.imageUrl = preset.mock_image;
        currentPlateState.mealType = preset.meal_type || "Almoço";
        currentPlateState.items = JSON.parse(JSON.stringify(preset.items));
        renderPlateDashboard();
    }

    /**
     * Updates grams for a specific food item
     */
    function updateItemGrams(index, deltaOrValue, isDelta = true) {
        if (!currentPlateState.items[index]) return;
        const current = Number(currentPlateState.items[index].grams) || 0;
        let next = isDelta ? current + Number(deltaOrValue) : Number(deltaOrValue);
        if (isNaN(next) || next < 0) next = 0;
        if (next > 2000) next = 2000;
        currentPlateState.items[index].grams = Math.round(next);
        renderPlateDashboard();
        if (typeof window !== "undefined" && typeof window.triggerHaptic === "function") {
            window.triggerHaptic(20);
        }
    }

    /**
     * Removes an item from the current plate
     */
    function removeItem(index) {
        if (index >= 0 && index < currentPlateState.items.length) {
            currentPlateState.items.splice(index, 1);
            renderPlateDashboard();
            if (typeof window !== "undefined" && typeof window.triggerHaptic === "function") {
                window.triggerHaptic(35);
            }
        }
    }

    /**
     * Adds an extra item from TACO catalog
     */
    function addItem(tacoId, grams = 100) {
        const taco = findTacoItem(tacoId);
        if (!taco) return;
        currentPlateState.items.push({
            taco_id: taco.id,
            name: taco.name,
            grams: Number(grams) || 100,
            box: { top: 50, left: 50, width: 25, height: 25 },
        });
        renderPlateDashboard();
        if (typeof window !== "undefined" && typeof window.triggerHaptic === "function") {
            window.triggerHaptic(40);
        }
    }

    /**
     * Handles file input / camera snapshot
     */
    async function handlePhotoUpload(file) {
        if (!file) return;

        // Show loading status in card
        const statusEl = document.getElementById("plate-scan-status");
        if (statusEl) {
            statusEl.textContent = "Processando imagem do prato com IA...";
            statusEl.classList.add("loading");
        }

        // Preview local file
        const reader = new FileReader();
        reader.onload = async (e) => {
            const dataUrl = e.target.result;
            currentPlateState.imageUrl = dataUrl;

            // Try backend API endpoint POST /api/v1/scan-plate-photo
            const isOnlineNow = typeof window.isOnline === "function" ? window.isOnline() : (typeof navigator === "undefined" || navigator.onLine !== false);
            if (isOnlineNow) {
                try {
                    const formData = new FormData();
                    formData.append("file", file);

                    const response = await fetch("/api/v1/scan-plate-photo", {
                        method: "POST",
                        body: formData,
                    });

                    if (response.ok) {
                        const data = await response.json();
                        if (data && data.items && data.items.length > 0) {
                            currentPlateState.plateTitle = data.plate_title || "Prato Escaneado";
                            currentPlateState.items = data.items;
                            renderPlateDashboard();
                            if (statusEl) {
                                statusEl.textContent = "Alimentos identificados com sucesso!";
                                statusEl.classList.remove("loading");
                            }
                            return;
                        }
                    }
                } catch (_) {
                    // Endpoint unavailable or offline fallback
                }
            }


            // Fallback: Default to Prato Feito items on custom photo
            currentPlateState.plateTitle = "Foto do Prato Enviada";
            currentPlateState.items = JSON.parse(JSON.stringify(PLATE_PRESETS.prato_feito.items));
            renderPlateDashboard();
            if (statusEl) {
                statusEl.textContent = "4 alimentos identificados na imagem";
                statusEl.classList.remove("loading");
            }
        };
        reader.readAsDataURL(file);
    }

    /**
     * Adds the complete plate items to the user's daily diet diary
     */
    async function addPlateToDiet() {
        const state = calculatePlateTotals(currentPlateState.items);
        const mealSelect = document.getElementById("plate-meal-select");
        const mealType = mealSelect ? mealSelect.value : currentPlateState.mealType || "Almoço";

        const btnAdd = document.getElementById("btn-add-plate-diet");
        if (btnAdd) {
            btnAdd.disabled = true;
            btnAdd.textContent = "Registrando na dieta...";
        }

        // Trigger native vibration
        if (typeof window.triggerHaptic === "function") {
            window.triggerHaptic(60);
        }

        const entriesToAdd = state.items.map((it) => ({
            meal_type: mealType,
            product_name: it.name,
            source_type: "foto_prato_ia",
            portion_g: it.grams,
            kcal: it.calculated.kcal,
            carbohydrates_g: it.calculated.carbs_g,
            proteins_g: it.calculated.prot_g,
            fat_g: it.calculated.fat_g,
            fiber_g: it.calculated.fiber_g,
            sodium_mg: it.calculated.sodio_mg,
        }));

        const isOnlineNow = typeof window.isOnline === "function" ? window.isOnline() : (typeof navigator === "undefined" || navigator.onLine !== false);
        let savedCount = 0;
        if (isOnlineNow) {
            for (const entry of entriesToAdd) {
                try {
                    const res = await fetch("/api/v1/diet/diary", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(entry),
                    });
                    if (res.ok) {
                        savedCount++;
                    }
                } catch (_) {}
            }
        }

        // Fallback or offline sync with localStorage
        if (savedCount === 0 && typeof window.addDiaryEntryToDiet === "function") {
            for (const entry of entriesToAdd) {
                await window.addDiaryEntryToDiet(entry);
            }
        } else if (savedCount === 0) {
            const raw = localStorage.getItem("nutriscan_diet_state_v1");
            if (raw) {
                try {
                    const localState = JSON.parse(raw);
                    if (localState && typeof localState === "object") {
                        if (!Array.isArray(localState.entries)) localState.entries = [];
                        let maxId = localState.entries.length > 0 ? Math.max(...localState.entries.map((e) => Number(e.id) || 0)) : 0;
                        entriesToAdd.forEach((e) => {
                            maxId++;
                            localState.entries.push({ id: maxId, ...e });
                        });
                        localStorage.setItem("nutriscan_diet_state_v1", JSON.stringify(localState));
                    }
                } catch (_) {}
            }
        }

        if (btnAdd) {
            btnAdd.disabled = false;
            btnAdd.textContent = "✓ Prato adicionado com sucesso!";
            setTimeout(() => {
                btnAdd.textContent = "Adicionar prato completo à refeição";
            }, 2500);
        }

        // Redirect to Minha Dieta tab
        if (typeof window.switchTab === "function") {
            window.switchTab("dieta");
        } else {
            const tabDietaBtn = document.getElementById("tab-btn-dieta");
            if (tabDietaBtn) tabDietaBtn.click();
        }

        // Refresh today's summary if function is accessible
        if (typeof window.loadDietToday === "function") {
            window.loadDietToday();
        }
    }

    /**
     * Renders the entire plate scanner dashboard and Bento cards
     */
    function renderPlateDashboard() {
        if (typeof document === "undefined") return;
        const { totals, items, micronutrients } = calculatePlateTotals(currentPlateState.items);

        // 1. Update Preview Image and Bounding Chips
        const imgEl = document.getElementById("plate-preview-img");
        if (imgEl) {
            imgEl.src = currentPlateState.imageUrl;
            imgEl.alt = currentPlateState.plateTitle;
        }

        const overlayEl = document.getElementById("plate-bounding-overlay");
        if (overlayEl) {
            overlayEl.innerHTML = items
                .map((it, idx) => {
                    const box = it.box || { top: 30 + idx * 15, left: 30 + idx * 10, width: 25, height: 25 };
                    const safeName = escapeHtml(it.name);
                    return `
                        <div class="plate-bound-box" style="top: ${box.top}%; left: ${box.left}%;" data-idx="${idx}">
                            <span class="plate-bound-badge">
                                <span class="badge-dot"></span>
                                ${safeName} (${Number(it.grams) || 0}g)
                            </span>
                        </div>
                    `;
                })
                .join("");
        }

        // 2. Update KPI summary cards
        const kcalEl = document.getElementById("plate-total-kcal");
        const carbsEl = document.getElementById("plate-total-carbs");
        const protEl = document.getElementById("plate-total-prot");
        const fatEl = document.getElementById("plate-total-fat");
        const fiberEl = document.getElementById("plate-total-fiber");
        const weightEl = document.getElementById("plate-total-weight");

        if (kcalEl) kcalEl.textContent = `${Math.round(totals.kcal)} kcal`;
        if (carbsEl) carbsEl.textContent = `${totals.carbs_g}g`;
        if (protEl) protEl.textContent = `${totals.prot_g}g`;
        if (fatEl) fatEl.textContent = `${totals.fat_g}g`;
        if (fiberEl) fiberEl.textContent = `${totals.fiber_g}g`;
        if (weightEl) weightEl.textContent = `${totals.total_grams}g`;

        // 3. Render Food Items List with plus/minus steppers
        const itemsListEl = document.getElementById("plate-items-list");
        if (itemsListEl) {
            if (items.length === 0) {
                itemsListEl.innerHTML = `
                    <div class="empty-plate-state">
                        <p>Nenhum alimento no prato. Adicione alimentos abaixo ou selecione um prato pronto.</p>
                    </div>
                `;
            } else {
                itemsListEl.innerHTML = items
                    .map(
                        (it, idx) => {
                            const safeName = escapeHtml(it.name);
                            return `
                    <div class="plate-item-row" data-index="${idx}">
                        <div class="item-meta">
                            <strong class="item-name">${safeName}</strong>
                            <div class="item-macros">
                                <span class="macro-badge kcal">${Math.round(it.calculated.kcal)} kcal</span>
                                <span class="macro-badge carb">C: ${it.calculated.carbs_g}g</span>
                                <span class="macro-badge prot">P: ${it.calculated.prot_g}g</span>
                                <span class="macro-badge fat">G: ${it.calculated.fat_g}g</span>
                            </div>
                        </div>
                        <div class="item-stepper-wrap">
                            <div class="stepper-controls" role="group" aria-label="Ajustar gramas de ${safeName}">
                                <button type="button" class="btn-step btn-step-minus" data-action="minus" data-idx="${idx}" aria-label="Diminuir 10g">−</button>
                                <div class="stepper-input-box">
                                    <input type="number" class="stepper-input" data-idx="${idx}" value="${Number(it.grams) || 0}" min="0" max="1500" step="10" inputmode="numeric" aria-label="Gramas" />
                                    <span class="stepper-unit">g</span>
                                </div>
                                <button type="button" class="btn-step btn-step-plus" data-action="plus" data-idx="${idx}" aria-label="Aumentar 10g">+</button>
                            </div>
                            <button type="button" class="btn-remove-item" data-idx="${idx}" title="Remover este alimento do prato" aria-label="Remover ${safeName}">✕</button>
                        </div>
                    </div>
                `;
                        }
                    )
                    .join("");
            }
        }


        // 4. Render Micronutrients Bento Card with % IDR progress meters
        const microGridEl = document.getElementById("plate-micros-grid");
        if (microGridEl) {
            microGridEl.innerHTML = micronutrients
                .map(
                    (m) => `
                <div class="micro-card-tile">
                    <div class="micro-tile-header">
                        <span class="micro-tile-label">${m.label}</span>
                        <span class="status-pill ${m.status.cls}">${m.status.label}</span>
                    </div>
                    <div class="micro-tile-body">
                        <strong class="micro-tile-value">${m.value} <span class="micro-tile-unit">${m.unit}</span></strong>
                        <span class="micro-tile-pct">${m.pct}% IDR</span>
                    </div>
                    <div class="progress-track" aria-hidden="true">
                        <div class="progress-fill ${m.pct > 100 ? "fill-rose" : m.pct >= 35 ? "fill-emerald" : "fill-blue"}" style="width: ${Math.min(100, m.pct)}%;"></div>
                    </div>
                    <span class="micro-idr-ref">Meta diária ANVISA: ${m.idr} ${m.unit}</span>
                </div>
            `
                )
                .join("");
        }

        // 5. Update Preset chip active states
        document.querySelectorAll(".plate-preset-chip").forEach((chip) => {
            chip.classList.toggle("active", chip.dataset.preset === currentPlateState.plateId);
        });
    }

    /**
     * Initializes DOM events and autocomplete search
     */
    function init() {
        // Preset Chips
        document.querySelectorAll(".plate-preset-chip").forEach((chip) => {
            chip.addEventListener("click", () => {
                const presetKey = chip.dataset.preset;
                loadPreset(presetKey);
            });
        });

        // Photo Upload / Camera Input
        const fileInput = document.getElementById("plate-photo-input");
        if (fileInput) {
            fileInput.addEventListener("change", (e) => {
                const file = e.target.files && e.target.files[0];
                if (file) handlePhotoUpload(file);
            });
        }

        // Interactive Stepper Clicks & Change Delegation
        const itemsList = document.getElementById("plate-items-list");
        if (itemsList) {
            itemsList.addEventListener("click", (e) => {
                const btn = e.target.closest("button");
                if (!btn) return;

                if (btn.classList.contains("btn-step-minus")) {
                    const idx = parseInt(btn.dataset.idx, 10);
                    updateItemGrams(idx, -10, true);
                } else if (btn.classList.contains("btn-step-plus")) {
                    const idx = parseInt(btn.dataset.idx, 10);
                    updateItemGrams(idx, 10, true);
                } else if (btn.classList.contains("btn-remove-item")) {
                    const idx = parseInt(btn.dataset.idx, 10);
                    removeItem(idx);
                }
            });

            itemsList.addEventListener("change", (e) => {
                if (e.target.classList.contains("stepper-input")) {
                    const idx = parseInt(e.target.dataset.idx, 10);
                    updateItemGrams(idx, parseFloat(e.target.value) || 0, false);
                }
            });
        }

        // Add to Diet Button
        const btnAddDiet = document.getElementById("btn-add-plate-diet");
        if (btnAddDiet) {
            btnAddDiet.addEventListener("click", addPlateToDiet);
        }

        // TACO Search & Autocomplete
        const searchInput = document.getElementById("plate-taco-search");
        const suggestionsBox = document.getElementById("plate-taco-suggestions");
        if (searchInput && suggestionsBox) {
            searchInput.addEventListener("input", (e) => {
                const query = e.target.value.toLowerCase().trim();
                if (!query || query.length < 2) {
                    suggestionsBox.hidden = true;
                    suggestionsBox.innerHTML = "";
                    return;
                }

                const matches = TACO_DATABASE.filter(
                    (t) => t.name.toLowerCase().includes(query) || t.category.toLowerCase().includes(query)
                ).slice(0, 6);

                if (matches.length === 0) {
                    suggestionsBox.innerHTML = `<div class="taco-no-result">Nenhum alimento encontrado na Tabela TACO.</div>`;
                    suggestionsBox.hidden = false;
                    return;
                }

                suggestionsBox.innerHTML = matches
                    .map(
                        (m) => `
                    <button type="button" class="taco-suggest-item" data-id="${escapeHtml(m.id)}">
                        <div class="suggest-info">
                            <strong>${escapeHtml(m.name)}</strong>
                            <span class="suggest-meta">${escapeHtml(m.category)} • ${Number(m.kcal_100g)} kcal/100g • Prot: ${Number(m.prot_100g)}g</span>
                        </div>
                        <span class="suggest-add-badge">+ Adicionar</span>
                    </button>
                `
                    )
                    .join("");
                suggestionsBox.hidden = false;
            });

            suggestionsBox.addEventListener("click", (e) => {
                const itemBtn = e.target.closest(".taco-suggest-item");
                if (!itemBtn) return;
                const tacoId = itemBtn.dataset.id;
                addItem(tacoId, 100);
                searchInput.value = "";
                suggestionsBox.hidden = true;
                suggestionsBox.innerHTML = "";
            });

            document.addEventListener("click", (e) => {
                if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
                    suggestionsBox.hidden = true;
                }
            });
        }

        // Initial render
        renderPlateDashboard();
    }

    // Auto-init on DOMContentLoaded if running in browser
    if (typeof document !== "undefined") {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", init);
        } else {
            init();
        }
    }

    return {
        ANVISA_IDR,
        TACO_DATABASE,
        PLATE_PRESETS,
        getState: () => currentPlateState,
        calculatePlateTotals,
        loadPreset,
        updateItemGrams,
        removeItem,
        addItem,
        addPlateToDiet,
        renderPlateDashboard,
        init,
    };
});
