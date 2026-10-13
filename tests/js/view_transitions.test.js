// Unit tests for NutriScan View Transitions & Fluid Animations
// Run with: node --test tests/js/view_transitions.test.js
const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

// Mock environment setup
const storageMock = new Map();
globalThis.localStorage = {
    getItem: (key) => (storageMock.has(key) ? storageMock.get(key) : null),
    setItem: (key, val) => storageMock.set(key, String(val)),
    removeItem: (key) => storageMock.delete(key),
    clear: () => storageMock.clear(),
};

globalThis.window = globalThis;
globalThis.window.dispatchEvent = () => true;
globalThis.window.triggerHaptic = () => true;
globalThis.window.addEventListener = () => true;
globalThis.window.removeEventListener = () => true;

const appModule = require("../../app/static/js/app.js");

function createMockElement(id, classes = []) {
    const classSet = new Set(classes);
    const attrs = {};
    const listeners = {};
    return {
        id,
        hidden: false,
        dataset: {},
        classList: {
            add: (c) => classSet.add(c),
            remove: (c) => classSet.delete(c),
            toggle: (c, force) => {
                if (force !== undefined) {
                    if (force) classSet.add(c); else classSet.delete(c);
                } else if (classSet.has(c)) {
                    classSet.delete(c);
                } else {
                    classSet.add(c);
                }
            },
            contains: (c) => classSet.has(c),
        },
        setAttribute: (k, v) => { attrs[k] = String(v); },
        getAttribute: (k) => attrs[k] || null,
        addEventListener: (evt, fn) => {
            listeners[evt] = listeners[evt] || [];
            listeners[evt].push(fn);
        },
        dispatchEvent: (evt) => {
            const handlers = listeners[evt.type || evt] || [];
            handlers.forEach((h) => h(evt));
        },
    };
}

test("switchTab: uses document.startViewTransition when available", () => {
    let transitionCalled = false;
    let transitionCallbackExecuted = false;

    const btnDieta = createMockElement("tab-btn-dieta", ["active"]);
    btnDieta.dataset.tab = "dieta";
    const btnFoto = createMockElement("tab-btn-foto");
    btnFoto.dataset.tab = "foto";

    const mobDieta = createMockElement("mob-btn-dieta", ["active"]);
    mobDieta.dataset.tab = "dieta";
    const mobFoto = createMockElement("mob-btn-foto");
    mobFoto.dataset.tab = "foto";

    const panelDieta = createMockElement("panel-dieta", ["active"]);
    const panelFoto = createMockElement("panel-foto");
    panelFoto.hidden = true;

    globalThis.document = {
        querySelectorAll: (selector) => {
            if (selector === ".tab-btn") return [btnDieta, btnFoto];
            if (selector === ".mob-nav-btn") return [mobDieta, mobFoto];
            if (selector === ".tab-panel") return [panelDieta, panelFoto];
            return [];
        },
        startViewTransition: (cb) => {
            transitionCalled = true;
            cb();
            transitionCallbackExecuted = true;
            return { finished: Promise.resolve() };
        },
    };

    appModule.switchTab("foto");

    assert.strictEqual(transitionCalled, true, "startViewTransition should be called");
    assert.strictEqual(transitionCallbackExecuted, true, "callback inside startViewTransition must execute");
    assert.strictEqual(btnFoto.classList.contains("active"), true);
    assert.strictEqual(btnDieta.classList.contains("active"), false);
    assert.strictEqual(panelFoto.classList.contains("active"), true);
    assert.strictEqual(panelFoto.hidden, false);
    assert.strictEqual(panelDieta.classList.contains("active"), false);
    assert.strictEqual(panelDieta.hidden, true);
});

test("switchTab: falls back gracefully when document.startViewTransition is undefined", () => {
    const btnDieta = createMockElement("tab-btn-dieta", ["active"]);
    btnDieta.dataset.tab = "dieta";
    const btnScanner = createMockElement("tab-btn-scanner");
    btnScanner.dataset.tab = "scanner";

    const panelDieta = createMockElement("panel-dieta", ["active"]);
    const panelScanner = createMockElement("panel-scanner");
    panelScanner.hidden = true;

    globalThis.document = {
        querySelectorAll: (selector) => {
            if (selector === ".tab-btn") return [btnDieta, btnScanner];
            if (selector === ".mob-nav-btn") return [];
            if (selector === ".tab-panel") return [panelDieta, panelScanner];
            return [];
        },
        startViewTransition: undefined,
    };

    appModule.switchTab("scanner");

    assert.strictEqual(btnScanner.classList.contains("active"), true);
    assert.strictEqual(btnDieta.classList.contains("active"), false);
    assert.strictEqual(panelScanner.classList.contains("active"), true);
    assert.strictEqual(panelScanner.hidden, false);
    assert.strictEqual(panelDieta.hidden, true);
});

test("modals: setupProfileOnboardingModal uses startViewTransition when opening and closing", () => {
    let transitionCount = 0;
    const modalEl = createMockElement("modal-profile-onboarding");
    modalEl.hidden = true;
    const btnOpenEl = createMockElement("btn-open-profile");
    const btnCloseEl = createMockElement("btn-profile-close");

    const elements = {
        "modal-profile-onboarding": modalEl,
        "btn-open-profile": btnOpenEl,
        "btn-profile-close": btnCloseEl,
    };

    globalThis.document = {
        getElementById: (id) => elements[id] || null,
        startViewTransition: (cb) => {
            transitionCount++;
            cb();
            return { finished: Promise.resolve() };
        },
    };

    appModule.setupProfileOnboardingModal();

    // Trigger open
    btnOpenEl.dispatchEvent({ type: "click" });
    assert.strictEqual(transitionCount, 1, "startViewTransition should be called on open");
    assert.strictEqual(modalEl.hidden, false);
    assert.strictEqual(modalEl.classList.contains("is-open"), true);

    // Trigger close
    btnCloseEl.dispatchEvent({ type: "click" });
    assert.strictEqual(transitionCount, 2, "startViewTransition should be called on close");
    assert.strictEqual(modalEl.hidden, true);
    assert.strictEqual(modalEl.classList.contains("is-open"), false);
});

test("modals: setupWhatsNewModal uses startViewTransition when available", () => {
    let transitionCount = 0;
    const modalEl = createMockElement("modal-whats-new");
    modalEl.hidden = true;
    const btnOpenEl = createMockElement("btn-open-whats-new");
    const btnCloseEl = createMockElement("btn-whats-new-close");

    const elements = {
        "modal-whats-new": modalEl,
        "btn-open-whats-new": btnOpenEl,
        "btn-whats-new-close": btnCloseEl,
    };

    globalThis.document = {
        getElementById: (id) => elements[id] || null,
        startViewTransition: (cb) => {
            transitionCount++;
            cb();
            return { finished: Promise.resolve() };
        },
    };

    appModule.setupWhatsNewModal();

    btnOpenEl.dispatchEvent({ type: "click" });
    assert.strictEqual(transitionCount, 1);
    assert.strictEqual(modalEl.classList.contains("is-open"), true);

    btnCloseEl.dispatchEvent({ type: "click" });
    assert.strictEqual(transitionCount, 2);
    assert.strictEqual(modalEl.classList.contains("is-open"), false);
});

test("style.css: View Transitions API rules, selectors, and reduced motion are properly declared", () => {
    const cssPath = path.resolve(__dirname, "../../app/static/css/style.css");
    const cssContent = fs.readFileSync(cssPath, "utf-8");

    assert.ok(cssContent.includes("::view-transition-old(root)"), "Must define ::view-transition-old(root)");
    assert.ok(cssContent.includes("::view-transition-new(root)"), "Must define ::view-transition-new(root)");
    assert.ok(cssContent.includes("view-transition-name: tab-panel"), "Must define tab-panel transition name");
    assert.ok(cssContent.includes("view-transition-name: diet-kpi-strip"), "Must define diet-kpi-strip transition name");
    assert.ok(cssContent.includes("view-transition-name: meal-list"), "Must define meal-list transition name");
    assert.ok(cssContent.includes("view-transition-name: modal-profile"), "Must define modal-profile transition name");
    assert.ok(cssContent.includes("view-transition-name: modal-whats-new"), "Must define modal-whats-new transition name");
    assert.ok(cssContent.includes("view-transition-name: modal-tour"), "Must define modal-tour transition name");
    assert.ok(cssContent.includes("prefers-reduced-motion: reduce"), "Must respect prefers-reduced-motion");
    assert.ok(cssContent.includes("animation: none !important"), "Must disable view-transition animations on reduced motion");
});
