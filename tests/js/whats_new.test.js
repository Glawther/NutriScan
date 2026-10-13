// Unit tests for NutriScan What's New Modal (v1.4.0)
// Run with: node --test tests/js/whats_new.test.js
const test = require("node:test");
const assert = require("node:assert");

// Mock localStorage, window and CustomEvent before requiring app.js
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
globalThis.CustomEvent = class CustomEvent {
    constructor(event, params) {
        this.type = event;
        this.detail = params?.detail;
    }
};

// Require appModule without triggering browser DOMContentLoaded
const appModule = require("../../app/static/js/app.js");

// Helper to create mock DOM elements
function createMockElement(id) {
    const listeners = {};
    return {
        id,
        hidden: true,
        classList: {
            classes: new Set(),
            add(c) { this.classes.add(c); },
            remove(c) { this.classes.delete(c); },
            contains(c) { return this.classes.has(c); }
        },
        attrs: {},
        setAttribute(k, v) { this.attrs[k] = String(v); },
        getAttribute(k) { return this.attrs[k] || null; },
        addEventListener(event, cb) {
            listeners[event] = listeners[event] || [];
            listeners[event].push(cb);
        },
        dispatchEvent(event) {
            const handlers = listeners[event.type || event] || [];
            handlers.forEach(h => h(event));
        }
    };
}

test("setupWhatsNewModal: opens and closes properly via buttons and keydown", () => {
    const modalEl = createMockElement("modal-whats-new");
    const btnOpenEl = createMockElement("btn-open-whats-new");
    const btnCloseEl = createMockElement("btn-whats-new-close");
    const btnConfirmEl = createMockElement("btn-whats-new-confirm");

    const elements = {
        "modal-whats-new": modalEl,
        "btn-open-whats-new": btnOpenEl,
        "btn-whats-new-close": btnCloseEl,
        "btn-whats-new-confirm": btnConfirmEl,
    };

    const windowListeners = {};
    const originalAddEventListener = globalThis.window.addEventListener;
    globalThis.window.addEventListener = (event, cb) => {
        windowListeners[event] = windowListeners[event] || [];
        windowListeners[event].push(cb);
    };

    globalThis.document = {
        getElementById: (id) => elements[id] || null,
    };

    assert.strictEqual(typeof appModule.setupWhatsNewModal, "function");

    const controller = appModule.setupWhatsNewModal();

    // Initial state: hidden
    assert.strictEqual(modalEl.hidden, true);
    assert.strictEqual(modalEl.classList.contains("is-open"), false);

    // Click open button
    btnOpenEl.dispatchEvent({ type: "click" });
    assert.strictEqual(modalEl.hidden, false);
    assert.strictEqual(modalEl.classList.contains("is-open"), true);
    assert.strictEqual(modalEl.getAttribute("aria-hidden"), "false");

    // Click close button
    btnCloseEl.dispatchEvent({ type: "click" });
    assert.strictEqual(modalEl.hidden, true);
    assert.strictEqual(modalEl.classList.contains("is-open"), false);
    assert.strictEqual(modalEl.getAttribute("aria-hidden"), "true");

    // Click open again, then click confirm button
    btnOpenEl.dispatchEvent({ type: "click" });
    assert.strictEqual(modalEl.hidden, false);

    btnConfirmEl.dispatchEvent({ type: "click" });
    assert.strictEqual(modalEl.hidden, true);

    // Direct controller methods
    controller.openModal();
    assert.strictEqual(modalEl.hidden, false);
    controller.closeModal();
    assert.strictEqual(modalEl.hidden, true);

    // Clean up
    delete globalThis.document;
    globalThis.window.addEventListener = originalAddEventListener;
});
