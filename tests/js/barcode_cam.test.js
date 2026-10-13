// Unit & mock tests for NutriScanCameraScanner module
// Run with: node --test tests/js/barcode_cam.test.js
const test = require("node:test");
const assert = require("node:assert");

const scannerModule = require("../../app/static/js/barcode_cam.js");

const originalNavigatorDescriptor = Object.getOwnPropertyDescriptor(globalThis, "navigator");

function mockNavigator(mockObj) {
    Object.defineProperty(globalThis, "navigator", {
        value: mockObj,
        configurable: true,
        writable: true
    });
}

function restoreNavigator() {
    if (originalNavigatorDescriptor) {
        Object.defineProperty(globalThis, "navigator", originalNavigatorDescriptor);
    } else {
        delete globalThis.navigator;
    }
}

test("Module exports all required methods and constants", () => {
    assert.strictEqual(typeof scannerModule.isSupported, "function");
    assert.strictEqual(typeof scannerModule.startScanner, "function");
    assert.strictEqual(typeof scannerModule.stopScanner, "function");
    assert.strictEqual(typeof scannerModule.toggleTorch, "function");
    assert.strictEqual(typeof scannerModule.captureSnapshot, "function");
    assert.strictEqual(typeof scannerModule.handleDetection, "function");
    assert.strictEqual(typeof scannerModule.playBeepSound, "function");
    assert.strictEqual(typeof scannerModule.triggerHapticFeedback, "function");
    assert.strictEqual(typeof scannerModule.resetCooldown, "function");
    assert.strictEqual(scannerModule.DEBOUNCE_COOLDOWN_MS, 2500);
    assert.deepStrictEqual(scannerModule.SUPPORTED_FORMATS, ["ean_13", "ean_8", "upc_a", "upc_e"]);
});

test("isSupported handles absence and presence of APIs correctly", () => {
    // Plain Node.js (default navigator has no mediaDevices)
    const initialCheck = scannerModule.isSupported();
    assert.strictEqual(initialCheck.hasUserMedia, false);
    assert.strictEqual(initialCheck.isSupported, false);

    // Mock active navigator with mediaDevices & BarcodeDetector
    mockNavigator({
        mediaDevices: {
            getUserMedia: async () => ({})
        }
    });
    globalThis.BarcodeDetector = class MockDetector {};

    const mockedCheck = scannerModule.isSupported();
    assert.strictEqual(mockedCheck.hasUserMedia, true);
    assert.strictEqual(mockedCheck.hasBarcodeDetector, true);
    assert.strictEqual(mockedCheck.isSupported, true);

    // Clean up
    restoreNavigator();
    delete globalThis.BarcodeDetector;
});

test("Debouncing logic enforces 2.5s cooldown on consecutive identical detections", () => {
    scannerModule.resetCooldown();
    const calls = [];
    const callback = (code) => calls.push(code);

    const baseTime = 10000;

    // First scan: should execute
    const firstResult = scannerModule.handleDetection("7891000053508", callback, baseTime);
    assert.strictEqual(firstResult, true);
    assert.strictEqual(calls.length, 1);
    assert.strictEqual(calls[0], "7891000053508");

    // Second scan (same barcode, 1.0s later): should be ignored by debounce
    const tooSoonResult = scannerModule.handleDetection("7891000053508", callback, baseTime + 1000);
    assert.strictEqual(tooSoonResult, false);
    assert.strictEqual(calls.length, 1);

    // Third scan (different barcode, 1.2s later): should execute immediately
    const differentCodeResult = scannerModule.handleDetection("3017620422003", callback, baseTime + 1200);
    assert.strictEqual(differentCodeResult, true);
    assert.strictEqual(calls.length, 2);
    assert.strictEqual(calls[1], "3017620422003");

    // Fourth scan (same as third, after 2600ms): should execute
    const afterCooldownResult = scannerModule.handleDetection("3017620422003", callback, baseTime + 1200 + 2600);
    assert.strictEqual(afterCooldownResult, true);
    assert.strictEqual(calls.length, 3);
    assert.strictEqual(calls[2], "3017620422003");
});

test("Audio and haptic triggers execute cleanly without throwing errors", () => {
    let vibrateCalledWith = null;
    mockNavigator({
        vibrate: (ms) => {
            vibrateCalledWith = ms;
        }
    });

    let audioCreated = false;
    globalThis.AudioContext = class MockAudioContext {
        constructor() {
            audioCreated = true;
            this.currentTime = 0;
            this.state = "running";
        }
        createOscillator() {
            return {
                type: "sine",
                frequency: { setValueAtTime: () => {} },
                connect: () => {},
                start: () => {},
                stop: () => {}
            };
        }
        createGain() {
            return {
                gain: {
                    setValueAtTime: () => {},
                    exponentialRampToValueAtTime: () => {}
                },
                connect: () => {}
            };
        }
    };

    scannerModule.triggerHapticFeedback();
    assert.strictEqual(vibrateCalledWith, 80);

    // Test window.NutriScanNative priority
    let nativeVibrateCalled = null;
    globalThis.NutriScanNative = {
        vibrate: (ms) => {
            nativeVibrateCalled = ms;
        }
    };
    scannerModule.triggerHapticFeedback();
    assert.strictEqual(nativeVibrateCalled, 80);

    // Test audio
    scannerModule.playBeepSound();
    assert.strictEqual(audioCreated, true);

    // Clean up
    restoreNavigator();
    delete globalThis.AudioContext;
    delete globalThis.NutriScanNative;
});

test("startScanner and stopScanner manage stream lifecycle and cleanup", async () => {
    let stoppedTracks = 0;
    const mockTrack = {
        stop: () => {
            stoppedTracks++;
        },
        getCapabilities: () => ({ torch: true }),
        applyConstraints: async () => {}
    };

    const mockStream = {
        getTracks: () => [mockTrack],
        getVideoTracks: () => [mockTrack]
    };

    mockNavigator({
        mediaDevices: {
            getUserMedia: async () => mockStream
        }
    });

    let detectCalls = 0;
    globalThis.BarcodeDetector = class MockDetector {
        constructor(opts) {
            this.formats = opts?.formats;
        }
        async detect() {
            detectCalls++;
            return [{ rawValue: "7894900011517" }];
        }
    };

    const mockVideo = {
        srcObject: null,
        readyState: 4,
        setAttribute: () => {},
        play: async () => {}
    };

    scannerModule.resetCooldown();
    const detections = [];
    const startRes = await scannerModule.startScanner(mockVideo, (code) => {
        detections.push(code);
    });

    assert.strictEqual(startRes.mode, "detector");
    assert.strictEqual(mockVideo.srcObject, mockStream);
    assert.strictEqual(scannerModule.getState().isActive, true);

    // Test torch toggle
    let appliedTorch = false;
    mockTrack.applyConstraints = async (c) => {
        if (c.advanced?.[0]?.torch === true) appliedTorch = true;
    };
    const torchRes = await scannerModule.toggleTorch(true);
    assert.strictEqual(torchRes, true);
    assert.strictEqual(appliedTorch, true);

    // Stop scanner
    scannerModule.stopScanner();
    assert.strictEqual(stoppedTracks, 1);
    assert.strictEqual(mockVideo.srcObject, null);
    assert.strictEqual(scannerModule.getState().isActive, false);

    // Clean up
    restoreNavigator();
    delete globalThis.BarcodeDetector;
});

test("startScanner throws error when getUserMedia is missing", async () => {
    restoreNavigator(); // Node default without mediaDevices
    let errorFired = false;
    try {
        await scannerModule.startScanner(null, () => {}, (err) => {
            errorFired = true;
            assert.ok(err instanceof Error);
        });
        assert.fail("Should have thrown error");
    } catch (err) {
        assert.ok(err instanceof Error);
        assert.strictEqual(errorFired, true);
    }
});
