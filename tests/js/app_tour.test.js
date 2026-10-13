// Unit & Integration tests for NutriScanTour module
// Run with: node --test tests/js/app_tour.test.js
const test = require("node:test");
const assert = require("node:assert");

// Load Tour Module
const tourModule = require("../../app/static/js/app_tour.js");

// Mock LocalStorage
function createMockLocalStorage() {
    let store = {};
    return {
        getItem: (key) => store[key] ?? null,
        setItem: (key, val) => {
            store[key] = String(val);
        },
        removeItem: (key) => {
            delete store[key];
        },
        clear: () => {
            store = {};
        }
    };
}

// Minimal DOM Mock for Tour UI
function createMockDOM() {
    const elements = {};

    function createElement(id, tagName = "div") {
        const el = {
            id,
            tagName: tagName.toUpperCase(),
            style: {},
            hidden: false,
            classList: {
                _classes: new Set(),
                add(c) { this._classes.add(c); },
                remove(c) { this._classes.delete(c); },
                contains(c) { return this._classes.has(c); },
                toggle(c, force) {
                    if (force !== undefined) {
                        if (force) this.add(c); else this.remove(c);
                    } else if (this.contains(c)) {
                        this.remove(c);
                    } else {
                        this.add(c);
                    }
                }
            },
            attributes: {},
            setAttribute(k, v) { this.attributes[k] = String(v); },
            getAttribute(k) { return this.attributes[k]; },
            textContent: "",
            innerHTML: "",
            children: [],
            appendChild(child) { this.children.push(child); },
            focus() { el._focused = true; },
            getBoundingClientRect() {
                return { top: 100, left: 50, width: 400, height: 250, bottom: 350, right: 450 };
            },
            scrollIntoView() { el._scrolledIntoView = true; },
            _listeners: {},
            addEventListener(type, fn) {
                if (!this._listeners[type]) this._listeners[type] = [];
                this._listeners[type].push(fn);
            },
            trigger(type, evt = {}) {
                if (this._listeners[type]) {
                    this._listeners[type].forEach((fn) => fn(evt));
                }
            }
        };
        elements[id] = el;
        return el;
    }

    // Modal and tour sub-elements
    const modal = createElement("modal-app-tour");
    const backdropOverlay = createElement("tour-backdrop-overlay");
    const spotlight = createElement("tour-spotlight-cutout");
    const progressBar = createElement("tour-progress-bar");
    const progressFill = createElement("tour-progress-fill");
    const stepBadge = createElement("tour-step-badge");
    const stepIcon = createElement("tour-step-icon");
    const stepTitle = createElement("tour-step-title");
    const stepDesc = createElement("tour-step-desc");
    const dotsContainer = createElement("tour-dots-container");
    const btnSkip = createElement("btn-skip-tour");
    const btnPrev = createElement("btn-prev-tour");
    const btnNext = createElement("btn-next-tour");
    const btnClose = createElement("btn-close-tour-modal");

    // Target elements
    const dietStrip = createElement("diet-kpi-strip");
    const panelPrato = createElement("panel-prato");
    const panelFoto = createElement("panel-foto");
    const panelScanner = createElement("panel-scanner");
    const shareGroup = createElement("share-btn-group");

    return {
        elements,
        getElementById(id) {
            return elements[id] || null;
        },
        querySelector(selector) {
            if (selector.startsWith("#")) {
                const id = selector.slice(1);
                return elements[id] || null;
            }
            if (selector === ".share-btn-group") {
                return elements["share-btn-group"] || null;
            }
            return null;
        },
        querySelectorAll(selector) {
            if (selector === ".tab-panel") {
                return [
                    elements["panel-dieta"] || createElement("panel-dieta"),
                    elements["panel-foto"] || createElement("panel-foto"),
                    elements["panel-scanner"] || createElement("panel-scanner"),
                    elements["panel-prato"] || createElement("panel-prato")
                ];
            }
            return [];
        },
        createElement(tag) {
            return createElement(`mock-${Date.now()}-${Math.random()}`, tag);
        }
    };
}

test("NutriScanTour exports required methods and defines exact 5 walkthrough steps", () => {
    assert.ok(tourModule);
    assert.strictEqual(typeof tourModule.startTour, "function");
    assert.strictEqual(typeof tourModule.nextStep, "function");
    assert.strictEqual(typeof tourModule.prevStep, "function");
    assert.strictEqual(typeof tourModule.endTour, "function");
    assert.strictEqual(typeof tourModule.isCompleted, "function");

    assert.ok(Array.isArray(tourModule.TOUR_STEPS));
    assert.strictEqual(tourModule.TOUR_STEPS.length, 5);

    // Passo 1: Minha Dieta
    const step1 = tourModule.TOUR_STEPS[0];
    assert.strictEqual(step1.stepNumber, 1);
    assert.strictEqual(step1.tab, "dieta");
    assert.strictEqual(step1.title, "1. Seu Painel Diário da Dieta");
    assert.ok(step1.description.includes("calorias e macros"));
    assert.strictEqual(step1.targetSelector, "#diet-kpi-strip");

    // Passo 2: Foto do Prato
    const step2 = tourModule.TOUR_STEPS[1];
    assert.strictEqual(step2.stepNumber, 2);
    assert.strictEqual(step2.tab, "prato");
    assert.strictEqual(step2.title, "2. Estimativa de Prato por Foto");
    assert.ok(step2.description.includes("Tabela TACO"));
    assert.strictEqual(step2.targetSelector, "#panel-prato");

    // Passo 3: Foto da Ficha Técnica
    const step3 = tourModule.TOUR_STEPS[2];
    assert.strictEqual(step3.stepNumber, 3);
    assert.strictEqual(step3.tab, "foto");
    assert.strictEqual(step3.title, "3. Leitor de Ficha Técnica por Foto");
    assert.ok(step3.description.includes("tabela nutricional"));
    assert.strictEqual(step3.targetSelector, "#panel-foto");

    // Passo 4: Código de Barras
    const step4 = tourModule.TOUR_STEPS[3];
    assert.strictEqual(step4.stepNumber, 4);
    assert.strictEqual(step4.tab, "scanner");
    assert.strictEqual(step4.title, "4. Scanner de Código de Barras por Câmera");
    assert.ok(step4.description.includes("ANVISA"));
    assert.strictEqual(step4.targetSelector, "#panel-scanner");

    // Passo 5: Compartilhar com Nutricionista
    const step5 = tourModule.TOUR_STEPS[4];
    assert.strictEqual(step5.stepNumber, 5);
    assert.strictEqual(step5.tab, "dieta");
    assert.strictEqual(step5.title, "5. Exportação para WhatsApp");
    assert.ok(step5.description.includes("WhatsApp"));
    assert.strictEqual(step5.targetSelector, ".share-btn-group");
});

test("LocalStorage persistence (isCompleted, markCompleted, resetCompleted)", () => {
    const mockStorage = createMockLocalStorage();
    globalThis.localStorage = mockStorage;

    assert.strictEqual(tourModule.isCompleted(), false);
    tourModule.markCompleted();
    assert.strictEqual(tourModule.isCompleted(), true);
    assert.strictEqual(mockStorage.getItem(tourModule.STORAGE_KEY), "true");

    tourModule.resetCompleted();
    assert.strictEqual(tourModule.isCompleted(), false);
    assert.strictEqual(mockStorage.getItem(tourModule.STORAGE_KEY), null);
});

test("Full interactive tour walkthrough: tab switching, haptics, UI updates, step navigation and completion", () => {
    const mockStorage = createMockLocalStorage();
    globalThis.localStorage = mockStorage;

    const mockDom = createMockDOM();
    globalThis.document = mockDom;
    globalThis.window = {
        addEventListener: () => {},
        innerHeight: 800,
        innerWidth: 1200
    };

    // Track tab switching and haptic calls
    const switchedTabs = [];
    globalThis.switchTab = (tab) => {
        switchedTabs.push(tab);
    };

    const hapticCalls = [];
    globalThis.triggerHaptic = (ms) => {
        hapticCalls.push(ms);
    };

    // Start Tour
    tourModule.startTour(true);
    assert.strictEqual(tourModule.getIsActive(), true);
    assert.strictEqual(tourModule.getCurrentStepIndex(), 0);

    // Passo 1 checks
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "dieta");
    assert.strictEqual(hapticCalls[hapticCalls.length - 1], 30);
    assert.strictEqual(mockDom.elements["modal-app-tour"].hidden, false);
    assert.strictEqual(mockDom.elements["tour-step-badge"].textContent, "Passo 1 de 5");
    assert.strictEqual(mockDom.elements["tour-step-title"].textContent, "1. Seu Painel Diário da Dieta");
    assert.strictEqual(mockDom.elements["btn-prev-tour"].style.display, "none");
    assert.strictEqual(mockDom.elements["btn-next-tour"].textContent, "Próximo ▶");
    assert.strictEqual(mockDom.elements["tour-progress-fill"].style.width, "20%");

    // Advance to Passo 2
    tourModule.nextStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 1);
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "prato");
    assert.strictEqual(mockDom.elements["tour-step-badge"].textContent, "Passo 2 de 5");
    assert.strictEqual(mockDom.elements["tour-step-title"].textContent, "2. Estimativa de Prato por Foto");
    assert.strictEqual(mockDom.elements["btn-prev-tour"].style.display, "inline-flex");
    assert.strictEqual(mockDom.elements["tour-progress-fill"].style.width, "40%");

    // Advance to Passo 3
    tourModule.nextStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 2);
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "foto");
    assert.strictEqual(mockDom.elements["tour-step-badge"].textContent, "Passo 3 de 5");
    assert.strictEqual(mockDom.elements["tour-progress-fill"].style.width, "60%");

    // Advance to Passo 4
    tourModule.nextStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 3);
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "scanner");
    assert.strictEqual(mockDom.elements["tour-step-badge"].textContent, "Passo 4 de 5");
    assert.strictEqual(mockDom.elements["tour-progress-fill"].style.width, "80%");

    // Advance to Passo 5 (Last step)
    tourModule.nextStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 4);
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "dieta");
    assert.strictEqual(mockDom.elements["tour-step-badge"].textContent, "Passo 5 de 5");
    assert.strictEqual(mockDom.elements["tour-step-title"].textContent, "5. Exportação para WhatsApp");
    assert.strictEqual(mockDom.elements["btn-next-tour"].textContent, "Concluir Tour ✓");
    assert.strictEqual(mockDom.elements["tour-progress-fill"].style.width, "100%");

    // Step back to Passo 4 with prevStep()
    tourModule.prevStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 3);
    assert.strictEqual(switchedTabs[switchedTabs.length - 1], "scanner");
    assert.strictEqual(mockDom.elements["btn-next-tour"].textContent, "Próximo ▶");

    // Advance back to Passo 5 and complete
    tourModule.nextStep();
    assert.strictEqual(tourModule.getCurrentStepIndex(), 4);
    assert.strictEqual(tourModule.isCompleted(), false);

    // Clicking next on last step finishes tour
    tourModule.nextStep();
    assert.strictEqual(tourModule.getIsActive(), false);
    assert.strictEqual(mockDom.elements["modal-app-tour"].hidden, true);
    assert.strictEqual(tourModule.isCompleted(), true);
    assert.strictEqual(mockStorage.getItem(tourModule.STORAGE_KEY), "true");

    // Clean up
    delete globalThis.switchTab;
    delete globalThis.triggerHaptic;
    delete globalThis.document;
    delete globalThis.window;
    delete globalThis.localStorage;
});

test("startTour(force = false) respects already completed state", () => {
    const mockStorage = createMockLocalStorage();
    mockStorage.setItem(tourModule.STORAGE_KEY, "true");
    globalThis.localStorage = mockStorage;

    const started = tourModule.startTour(false);
    assert.strictEqual(started, false);
    assert.strictEqual(tourModule.getIsActive(), false);

    // With force = true, it should start
    const forced = tourModule.startTour(true);
    assert.strictEqual(forced, true);
    assert.strictEqual(tourModule.getIsActive(), true);

    tourModule.endTour(true);
    delete globalThis.localStorage;
});

test("endTour closes modal and can save completion state", () => {
    const mockStorage = createMockLocalStorage();
    globalThis.localStorage = mockStorage;
    const mockDom = createMockDOM();
    globalThis.document = mockDom;

    tourModule.startTour(true);
    assert.strictEqual(tourModule.getIsActive(), true);

    tourModule.endTour(true);
    assert.strictEqual(tourModule.getIsActive(), false);
    assert.strictEqual(mockDom.elements["modal-app-tour"].hidden, true);
    assert.strictEqual(tourModule.isCompleted(), true);

    delete globalThis.document;
    delete globalThis.localStorage;
});
