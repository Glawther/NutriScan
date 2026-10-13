/**
 * NutriScan - Módulo de Compartilhamento e Exportação de Dieta
 * Suporte a Web Share API nativo (Android), NativeBridge (Kotlin), fallback WhatsApp Web,
 * cópia para Área de Transferência com Toast, e Impressão / PDF limpo.
 */
(function (root) {
    "use strict";

    function showToast(message, duration = 3000) {
        if (typeof document === "undefined") return;
        let toast = document.getElementById("nutriscan-toast");
        if (!toast) {
            toast = document.createElement("div");
            toast.id = "nutriscan-toast";
            toast.className = "ns-toast";
            toast.setAttribute("role", "status");
            toast.setAttribute("aria-live", "polite");
            document.body.appendChild(toast);
        }

        toast.textContent = message;
        toast.classList.add("show");

        if (toast._timeout) {
            clearTimeout(toast._timeout);
        }

        toast._timeout = setTimeout(() => {
            toast.classList.remove("show");
        }, duration);
    }

    /**
     * Gera o texto formatado para WhatsApp diretamente no cliente (100% offline).
     */
    function generateDailySummaryText(summary, waterData, dateStr) {
        let dateFmt = dateStr;
        if (dateStr && dateStr.includes("-")) {
            dateFmt = dateStr.split("-").reverse().join("/");
        } else if (!dateFmt) {
            dateFmt = new Date().toLocaleDateString("pt-BR");
        }

        const c = summary?.consumed || { kcal: 0, proteins_g: 0, carbohydrates_g: 0, fat_g: 0, sodium_mg: 0 };
        const g = summary?.goals || { daily_kcal_limit: 2000, proteins_limit_g: 150, carbs_limit_g: 200, fat_limit_g: 65, sodium_limit_mg: 2000 };
        const waterConsumed = waterData?.amount_ml ?? 0;
        const waterGoal = waterData?.goal_ml ?? 2500;
        const diff = Math.round((g.daily_kcal_limit || 2000) - (c.kcal || 0));
        const diffText = diff >= 0 ? `${diff} kcal restantes` : `${Math.abs(diff)} kcal acima da meta`;

        let text = `🥗 *NutriScan - Resumo da Dieta (${dateFmt})*\n\n`;
        text += `🔥 *Calorias:* ${Math.round(c.kcal || 0)} / ${Math.round(g.daily_kcal_limit || 2000)} kcal (${diffText})\n`;
        text += `💪 *Proteína:* ${c.proteins_g || 0}g | 🌾 *Carbs:* ${c.carbohydrates_g || 0}g | 🥑 *Gordura:* ${c.fat_g || 0}g | 🧂 *Sódio:* ${Math.round(c.sodium_mg || 0)}mg\n`;
        text += `💧 *Água:* ${waterConsumed} ml / ${waterGoal} ml\n\n`;

        const entries = summary?.entries || [];
        if (entries.length === 0) {
            text += `_Nenhuma refeição registrada neste dia._\n`;
        } else {
            text += `*Refeições Registradas:*\n`;
            const meals = {};
            entries.forEach((e) => {
                const m = e.meal_type || "Lanche";
                if (!meals[m]) meals[m] = [];
                meals[m].push(e);
            });
            for (const [mName, items] of Object.entries(meals)) {
                text += `\n*${mName}:*\n`;
                items.forEach((it) => {
                    text += `• ${it.product_name} (${it.portion_g}g) - ${Math.round(it.kcal)} kcal (P: ${it.proteins_g}g, C: ${it.carbohydrates_g}g, G: ${it.fat_g}g)\n`;
                });
            }
        }
        text += `\n_Gerado pelo NutriScan_`;
        return text;
    }

    async function shareToWhatsApp(summaryText) {
        if (!summaryText) {
            showToast("Nenhum resumo disponível para compartilhar.");
            return;
        }

        if (typeof root.triggerHaptic === "function") root.triggerHaptic(40);

        // 1. Tenta ponte nativa Android (Kotlin NativeBridge)
        if (root.NutriScanNative && typeof root.NutriScanNative.shareText === "function") {
            try {
                root.NutriScanNative.shareText("NutriScan Dieta", summaryText);
                return;
            } catch (_) {}
        }

        // 2. Tenta Web Share API nativo (navegadores móveis)
        if (typeof navigator !== "undefined" && navigator.share) {
            try {
                await navigator.share({
                    title: "NutriScan Dieta",
                    text: summaryText,
                });
                return;
            } catch (err) {
                if (err && err.name === "AbortError") {
                    return;
                }
            }
        }

        // 3. Fallback: abre direto no WhatsApp Web / App
        const url = `https://api.whatsapp.com/send?text=${encodeURIComponent(summaryText)}`;
        if (typeof window !== "undefined") {
            window.open(url, "_blank", "noopener,noreferrer");
        }
    }

    async function copyToClipboard(summaryText) {
        if (!summaryText) {
            showToast("Nenhum resumo para copiar.");
            return;
        }

        if (typeof root.triggerHaptic === "function") root.triggerHaptic(30);

        try {
            if (typeof navigator !== "undefined" && navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(summaryText);
            } else if (typeof document !== "undefined") {
                const ta = document.createElement("textarea");
                ta.value = summaryText;
                ta.style.position = "fixed";
                ta.style.left = "-9999px";
                document.body.appendChild(ta);
                ta.focus();
                ta.select();
                document.execCommand("copy");
                document.body.removeChild(ta);
            }
            showToast("✓ Resumo copiado para a área de transferência!");
        } catch (err) {
            showToast("Erro ao copiar texto.");
        }
    }

    function printDailyReport() {
        if (typeof window !== "undefined") {
            window.print();
        }
    }

    async function fetchExport(dateStr, format = "whatsapp") {
        const params = new URLSearchParams();
        if (dateStr) params.set("date_str", dateStr);
        if (format) params.set("format", format);

        const res = await fetch(`/api/v1/diet/export?${params.toString()}`);
        if (!res.ok) {
            throw new Error(`Falha ao exportar dieta: ${res.status}`);
        }
        return await res.json();
    }

    const NutriScanShare = {
        generateDailySummaryText,
        shareToWhatsApp,
        copyToClipboard,
        printDailyReport,
        fetchExport,
        showToast,
    };

    root.NutriScanShare = NutriScanShare;

    if (typeof module !== "undefined" && module.exports) {
        module.exports = NutriScanShare;
    }
})(typeof globalThis !== "undefined" ? globalThis : this);
