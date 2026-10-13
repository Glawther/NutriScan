/**
 * NutriScanTour - Interactive 5-step guided walkthrough
 *
 * Requirements:
 * - 5 steps covering Diet Dashboard, Plate Scanner (AI Taco),
 *   Photo Label Reader, Barcode Camera & Nutritionist WhatsApp Export.
 * - Auto-switches application tabs smoothly.
 * - Spotlight target positioning & backdrop cutout.
 * - Haptic feedback integration (window.triggerHaptic(30)).
 * - LocalStorage persistence ("nutriscan_tour_completed").
 * - Exported as window.NutriScanTour and CommonJS module.
 */
(function (root, factory) {
    if (typeof module === "object" && typeof module.exports === "object") {
        module.exports = factory();
    } else {
        root.NutriScanTour = factory();
    }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    "use strict";

    const STORAGE_KEY = "nutriscan_tour_completed";

    const TOUR_STEPS = [
        {
            stepNumber: 1,
            badge: "Passo 1 de 5",
            icon: "🥗",
            title: "1. Seu Painel Diário da Dieta",
            description: "Acompanhe seu consumo de calorias e macros calculado especialmente para o seu peso e objetivo. Registre água e veja o saldo restante de cada refeição.",
            tab: "dieta",
            targetSelector: "#diet-kpi-strip"
        },
        {
            stepNumber: 2,
            badge: "Passo 2 de 5",
            icon: "🍽️",
            title: "2. Reconhecimento de Prato 100% Offline",
            description: "Tire foto do seu almoço ou jantar! A inteligência artificial identifica alimentos, estima porções e calcula macros e micronutrientes da Tabela TACO sem gastar internet.",
            tab: "prato",
            targetSelector: "#panel-prato"
        },
        {
            stepNumber: 3,
            badge: "Passo 3 de 5",
            icon: "📷",
            title: "3. Leitor de Ficha Técnica por Foto",
            description: "Fotografe a tabela nutricional na embalagem de suplementos ou alimentos (whey, iogurte, pão). O leitor calcula a porção consumida proporcionalmente.",
            tab: "foto",
            targetSelector: "#panel-foto"
        },
        {
            stepNumber: 4,
            badge: "Passo 4 de 5",
            icon: "🔍",
            title: "4. Scanner de Código de Barras por Câmera",
            description: "Aponte a câmera para produtos de supermercado e veja imediatamente os selos de advertência da ANVISA (Alto em Açúcar, Sódio ou Gordura) e o Nutri-Score.",
            tab: "scanner",
            targetSelector: "#panel-scanner"
        },
        {
            stepNumber: 5,
            badge: "Passo 5 de 5",
            icon: "📲",
            title: "5. Exportação para WhatsApp",
            description: "Envie o resumo completo da sua alimentação diária com 1 clique direto no WhatsApp do seu nutricionista ou médico.",
            tab: "dieta",
            targetSelector: ".share-btn-group"
        }
    ];

    let currentStepIndex = 0;
    let isActive = false;
    let resizeListenerAttached = false;
    let keydownListenerAttached = false;

    /**
     * Check if the tour was previously completed in localStorage.
     * @returns {boolean}
     */
    function isCompleted() {
        try {
            if (typeof localStorage !== "undefined" && localStorage !== null) {
                return localStorage.getItem(STORAGE_KEY) === "true";
            }
        } catch (_) {}
        return false;
    }

    /**
     * Save completed state in localStorage.
     */
    function markCompleted() {
        try {
            if (typeof localStorage !== "undefined" && localStorage !== null) {
                localStorage.setItem(STORAGE_KEY, "true");
            }
        } catch (_) {}
    }

    /**
     * Clear completion state (useful for tests or restart).
     */
    function resetCompleted() {
        try {
            if (typeof localStorage !== "undefined" && localStorage !== null) {
                localStorage.removeItem(STORAGE_KEY);
            }
        } catch (_) {}
    }

    /**
     * Trigger subtle haptic vibration if supported.
     * @param {number} durationMs
     */
    function triggerHaptic(durationMs = 30) {
        try {
            const root = typeof globalThis !== "undefined" ? globalThis : window;
            if (root && typeof root.triggerHaptic === "function") {
                root.triggerHaptic(durationMs);
            } else if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
                navigator.vibrate(durationMs);
            }
        } catch (_) {}
    }

    /**
     * Switch tab using application global or fallback.
     * @param {string} tabName
     */
    function performTabSwitch(tabName) {
        try {
            const root = typeof globalThis !== "undefined" ? globalThis : window;
            if (root && typeof root.switchTab === "function") {
                root.switchTab(tabName);
                return;
            }
            if (typeof document !== "undefined") {
                const targetBtn = document.querySelector(`.tab-btn[data-tab="${tabName}"]`);
                if (targetBtn && typeof targetBtn.click === "function") {
                    targetBtn.click();
                    return;
                }
                // Fallback manual class toggle
                document.querySelectorAll(".tab-panel").forEach((panel) => {
                    const match = panel.id === `panel-${tabName}`;
                    panel.classList.toggle("active", match);
                    panel.hidden = !match;
                });
            }
        } catch (_) {}
    }

    /**
     * Update spotlight cutout position based on active target element.
     * @param {HTMLElement|null} targetEl
     * @param {HTMLElement|null} spotlightEl
     */
    function updateSpotlightPosition(targetEl, spotlightEl) {
        if (!spotlightEl) return;
        if (!targetEl || typeof targetEl.getBoundingClientRect !== "function") {
            spotlightEl.style.display = "none";
            return;
        }

        const rect = targetEl.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) {
            spotlightEl.style.display = "none";
            return;
        }

        const padding = 8;
        const top = Math.max(0, rect.top - padding);
        const left = Math.max(0, rect.left - padding);
        const width = rect.width + padding * 2;
        const height = rect.height + padding * 2;

        spotlightEl.style.display = "block";
        spotlightEl.style.top = `${top}px`;
        spotlightEl.style.left = `${left}px`;
        spotlightEl.style.width = `${width}px`;
        spotlightEl.style.height = `${height}px`;

        // Smooth scroll into view if target element is outside viewport
        try {
            if (typeof targetEl.scrollIntoView === "function") {
                const isInViewport =
                    rect.top >= 0 &&
                    rect.left >= 0 &&
                    rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                    rect.right <= (window.innerWidth || document.documentElement.clientWidth);

                if (!isInViewport) {
                    targetEl.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
                }
            }
        } catch (_) {}
    }

    /**
     * Render the current step into the DOM modal card.
     */
    function renderStep() {
        if (typeof document === "undefined") return;

        const modal = document.getElementById("modal-app-tour");
        if (!modal) return;

        const step = TOUR_STEPS[currentStepIndex];
        if (!step) return;

        // Auto-switch application tab smoothly
        performTabSwitch(step.tab);

        // Haptic feedback on each step
        triggerHaptic(30);

        // Ensure modal is visible and accessible
        modal.hidden = false;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");

        // Progress bar percentage
        const progressFill = document.getElementById("tour-progress-fill");
        if (progressFill) {
            const pct = Math.round(((currentStepIndex + 1) / TOUR_STEPS.length) * 100);
            progressFill.style.width = `${pct}%`;
            progressFill.setAttribute("aria-valuenow", String(pct));
        }

        // Step counter badge
        const badgeEl = document.getElementById("tour-step-badge");
        if (badgeEl) {
            badgeEl.textContent = `Passo ${step.stepNumber} de ${TOUR_STEPS.length}`;
        }

        // Step icon
        const iconEl = document.getElementById("tour-step-icon");
        if (iconEl) {
            iconEl.textContent = step.icon;
        }

        // Title
        const titleEl = document.getElementById("tour-step-title");
        if (titleEl) {
            titleEl.textContent = step.title;
        }

        // Description
        const descEl = document.getElementById("tour-step-desc");
        if (descEl) {
            descEl.textContent = step.description;
        }

        // Progress dots
        const dotsContainer = document.getElementById("tour-dots-container");
        if (dotsContainer) {
            dotsContainer.innerHTML = "";
            TOUR_STEPS.forEach((s, idx) => {
                const dot = document.createElement("span");
                dot.className = `tour-dot${idx === currentStepIndex ? " active" : ""}${idx < currentStepIndex ? " completed" : ""}`;
                dot.setAttribute("aria-label", `Passo ${idx + 1}`);
                dotsContainer.appendChild(dot);
            });
        }

        // Previous button visibility
        const prevBtn = document.getElementById("btn-prev-tour");
        if (prevBtn) {
            prevBtn.style.display = currentStepIndex === 0 ? "none" : "inline-flex";
            prevBtn.hidden = currentStepIndex === 0;
        }

        // Next button label
        const nextBtn = document.getElementById("btn-next-tour");
        if (nextBtn) {
            const isLast = currentStepIndex === TOUR_STEPS.length - 1;
            nextBtn.textContent = isLast ? "Concluir Tour ✓" : "Próximo ▶";
            nextBtn.setAttribute("aria-label", isLast ? "Concluir tour" : "Ir para o próximo passo");
            // Focus next button for seamless keyboard navigation
            try {
                nextBtn.focus();
            } catch (_) {}
        }

        // Spotlight positioning
        const spotlightEl = document.getElementById("tour-spotlight-cutout");
        const targetEl = document.querySelector(step.targetSelector);
        updateSpotlightPosition(targetEl, spotlightEl);
    }

    /**
     * Start tour walkthrough.
     * @param {boolean} force If true, starts even if previously completed.
     * @returns {boolean} True if started, false if skipped because already completed.
     */
    function startTour(force = true) {
        if (!force && isCompleted()) {
            return false;
        }

        currentStepIndex = 0;
        isActive = true;

        if (typeof window !== "undefined") {
            if (!resizeListenerAttached) {
                window.addEventListener("resize", onWindowResize);
                resizeListenerAttached = true;
            }
            if (!keydownListenerAttached) {
                window.addEventListener("keydown", onKeyDown);
                keydownListenerAttached = true;
            }
        }

        renderStep();
        return true;
    }

    /**
     * Advance to the next step, or finish tour if on last step.
     */
    function nextStep() {
        if (!isActive) return;

        if (currentStepIndex < TOUR_STEPS.length - 1) {
            currentStepIndex++;
            renderStep();
        } else {
            endTour(true);
        }
    }

    /**
     * Return to previous step.
     */
    function prevStep() {
        if (!isActive) return;

        if (currentStepIndex > 0) {
            currentStepIndex--;
            renderStep();
        }
    }

    /**
     * End tour walkthrough and close modal.
     * @param {boolean} markAsDone Whether to mark tour as completed in localStorage.
     */
    function endTour(markAsDone = true) {
        isActive = false;

        if (markAsDone) {
            markCompleted();
        }

        if (typeof document !== "undefined") {
            const modal = document.getElementById("modal-app-tour");
            if (modal) {
                modal.hidden = true;
                modal.classList.remove("is-open");
                modal.setAttribute("aria-hidden", "true");
            }

            const spotlightEl = document.getElementById("tour-spotlight-cutout");
            if (spotlightEl) {
                spotlightEl.style.display = "none";
            }
        }

        triggerHaptic(20);
    }

    function onWindowResize() {
        if (!isActive || typeof document === "undefined") return;
        const step = TOUR_STEPS[currentStepIndex];
        if (step) {
            const spotlightEl = document.getElementById("tour-spotlight-cutout");
            const targetEl = document.querySelector(step.targetSelector);
            updateSpotlightPosition(targetEl, spotlightEl);
        }
    }

    function onKeyDown(evt) {
        if (!isActive) return;
        if (evt.key === "Escape") {
            evt.preventDefault();
            endTour(true);
        } else if (evt.key === "ArrowRight") {
            evt.preventDefault();
            nextStep();
        } else if (evt.key === "ArrowLeft") {
            evt.preventDefault();
            prevStep();
        }
    }

    /**
     * Wire button events in DOM.
     */
    function initEvents() {
        if (typeof document === "undefined") return;

        const skipBtn = document.getElementById("btn-skip-tour");
        if (skipBtn) {
            skipBtn.addEventListener("click", () => endTour(true));
        }

        const prevBtn = document.getElementById("btn-prev-tour");
        if (prevBtn) {
            prevBtn.addEventListener("click", () => prevStep());
        }

        const nextBtn = document.getElementById("btn-next-tour");
        if (nextBtn) {
            nextBtn.addEventListener("click", () => nextStep());
        }

        const closeBtn = document.getElementById("btn-close-tour-modal");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => endTour(true));
        }

        const backdrop = document.getElementById("tour-backdrop-overlay");
        if (backdrop) {
            backdrop.addEventListener("click", (e) => {
                if (e.target === backdrop) {
                    endTour(true);
                }
            });
        }
    }

    // Auto-bind on DOMContentLoaded if running in browser
    if (typeof document !== "undefined") {
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", initEvents);
        } else {
            initEvents();
        }
    }

    return {
        TOUR_STEPS,
        STORAGE_KEY,
        startTour,
        nextStep,
        prevStep,
        endTour,
        isCompleted,
        markCompleted,
        resetCompleted,
        getCurrentStepIndex: () => currentStepIndex,
        setCurrentStepIndex: (idx) => { currentStepIndex = idx; },
        getIsActive: () => isActive,
        triggerHaptic,
        performTabSwitch,
        initEvents
    };
});
