/**
 * NutriScanCameraScanner - Ultra-fast live camera barcode scanner
 * Supporting BarcodeDetector API with snapshot / manual fallback,
 * debouncing (2.5s), acoustic feedback (Web Audio synth 880Hz),
 * and haptic feedback (vibrate API).
 *
 * Compatible with Browser and CommonJS/Node environments.
 */
(function (root) {
    "use strict";

    const SUPPORTED_FORMATS = ["ean_13", "ean_8", "upc_a", "upc_e"];
    const DEBOUNCE_COOLDOWN_MS = 2500;
    const SCAN_INTERVAL_MS = 100;

    let activeStream = null;
    let activeVideoElement = null;
    let scanIntervalTimer = null;
    let detectorInstance = null;
    let isDetecting = false;
    let lastDetectedCode = null;
    let lastDetectedTimestamp = 0;
    let audioContext = null;

    /**
     * Checks whether camera mediaDevices and BarcodeDetector are supported.
     * @returns {{ hasUserMedia: boolean, hasBarcodeDetector: boolean, isSupported: boolean }}
     */
    function isSupported() {
        const hasUserMedia = Boolean(
            typeof navigator !== "undefined" &&
            navigator.mediaDevices &&
            typeof navigator.mediaDevices.getUserMedia === "function"
        );
        const hasBarcodeDetector = Boolean(
            typeof root !== "undefined" &&
            typeof root.BarcodeDetector === "function"
        );
        return {
            hasUserMedia: hasUserMedia,
            hasBarcodeDetector: hasBarcodeDetector,
            isSupported: hasUserMedia
        };
    }

    /**
     * Synthesizes a pleasant subtle 880Hz sine wave beep for 70ms.
     */
    function playBeepSound() {
        try {
            const AudioCtx = root.AudioContext || root.webkitAudioContext;
            if (!AudioCtx) return;
            if (!audioContext || audioContext.state === "closed") {
                audioContext = new AudioCtx();
            }
            if (audioContext.state === "suspended") {
                audioContext.resume().catch(() => {});
            }

            const osc = audioContext.createOscillator();
            const gain = audioContext.createGain();

            osc.type = "sine";
            osc.frequency.setValueAtTime(880, audioContext.currentTime);

            // Envelope to avoid clicks
            gain.gain.setValueAtTime(0.001, audioContext.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.2, audioContext.currentTime + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.001, audioContext.currentTime + 0.07);

            osc.connect(gain);
            gain.connect(audioContext.destination);

            osc.start(audioContext.currentTime);
            osc.stop(audioContext.currentTime + 0.07);
        } catch (_) {
            // Audio error non-blocking
        }
    }

    /**
     * Triggers native or web vibration for 80ms.
     */
    function triggerHapticFeedback() {
        try {
            if (root.NutriScanNative && typeof root.NutriScanNative.vibrate === "function") {
                root.NutriScanNative.vibrate(80);
            } else if (typeof navigator !== "undefined" && typeof navigator.vibrate === "function") {
                navigator.vibrate(80);
            }
        } catch (_) {
            // Haptic error non-blocking
        }
    }

    /**
     * Checks debounce constraint and executes detection callback.
     * @param {string} rawValue
     * @param {Function} onDetectedCallback
     * @param {number} [currentTime] Optional timestamp for deterministic testing
     * @returns {boolean} Whether the code was processed or ignored due to cooldown
     */
    function handleDetection(rawValue, onDetectedCallback, currentTime) {
        if (!rawValue) return false;
        const barcode = String(rawValue).trim();
        if (!barcode) return false;

        const now = typeof currentTime === "number" ? currentTime : Date.now();
        if (lastDetectedCode === barcode && now - lastDetectedTimestamp < DEBOUNCE_COOLDOWN_MS) {
            return false;
        }

        lastDetectedCode = barcode;
        lastDetectedTimestamp = now;

        triggerHapticFeedback();
        playBeepSound();

        if (typeof onDetectedCallback === "function") {
            try {
                onDetectedCallback(barcode);
            } catch (err) {
                console.error("Error in onDetectedCallback:", err);
            }
        }
        return true;
    }

    /**
     * Captures a single image frame as Blob / DataURL from the active video stream for fallback processing.
     * @param {HTMLVideoElement} videoElement
     * @returns {string|null} DataURL of the captured snapshot
     */
    function captureSnapshot(videoElement) {
        const vid = videoElement || activeVideoElement;
        if (!vid || !vid.videoWidth || !vid.videoHeight) return null;
        try {
            const canvas = document.createElement("canvas");
            canvas.width = vid.videoWidth;
            canvas.height = vid.videoHeight;
            const ctx = canvas.getContext("2d");
            ctx.drawImage(vid, 0, 0, canvas.width, canvas.height);
            return canvas.toDataURL("image/jpeg", 0.85);
        } catch (_) {
            return null;
        }
    }

    /**
     * Starts live camera scanning on the provided video element.
     * @param {HTMLVideoElement} videoElement
     * @param {Function} onDetectedCallback
     * @param {Function} [onErrorCallback]
     * @returns {Promise<{ mode: "detector" | "fallback", stream: MediaStream }>}
     */
    async function startScanner(videoElement, onDetectedCallback, onErrorCallback) {
        stopScanner();

        const support = isSupported();
        if (!support.hasUserMedia) {
            const err = new Error("Camera not accessible (MediaDevices getUserMedia unsupported).");
            if (typeof onErrorCallback === "function") onErrorCallback(err);
            throw err;
        }

        activeVideoElement = videoElement;

        const constraints = {
            audio: false,
            video: {
                facingMode: { ideal: "environment" },
                width: { ideal: 1920, min: 1280 },
                height: { ideal: 1080, min: 720 },
                focusMode: { ideal: "continuous" }
            }
        };

        try {
            let stream;
            try {
                stream = await navigator.mediaDevices.getUserMedia(constraints);
            } catch (strictErr) {
                // Fallback to simpler video constraints if high resolution fails on some devices
                stream = await navigator.mediaDevices.getUserMedia({
                    audio: false,
                    video: { facingMode: { ideal: "environment" } }
                });
            }

            activeStream = stream;

            if (videoElement) {
                videoElement.srcObject = stream;
                videoElement.setAttribute("playsinline", "true"); // Required for iOS Safari
                videoElement.muted = true;
                await videoElement.play().catch(() => {});
            }

            if (support.hasBarcodeDetector) {
                try {
                    detectorInstance = new root.BarcodeDetector({ formats: SUPPORTED_FORMATS });
                } catch (_) {
                    detectorInstance = new root.BarcodeDetector();
                }

                isDetecting = true;
                scanIntervalTimer = setInterval(async () => {
                    if (!isDetecting || !activeVideoElement || activeVideoElement.readyState < 2) {
                        return;
                    }
                    try {
                        const barcodes = await detectorInstance.detect(activeVideoElement);
                        if (barcodes && barcodes.length > 0) {
                            for (const item of barcodes) {
                                if (item.rawValue) {
                                    handleDetection(item.rawValue, onDetectedCallback);
                                    break;
                                }
                            }
                        }
                    } catch (_) {
                        // Keep loop running on transient decode frames
                    }
                }, SCAN_INTERVAL_MS);

                return { mode: "detector", stream: stream };
            }

            // Fallback mode: BarcodeDetector not natively available in browser
            return { mode: "fallback", stream: stream };
        } catch (err) {
            stopScanner();
            if (typeof onErrorCallback === "function") {
                onErrorCallback(err);
            }
            throw err;
        }
    }

    /**
     * Cleanly stops camera stream and releases hardware tracks.
     */
    function stopScanner() {
        isDetecting = false;
        if (scanIntervalTimer) {
            clearInterval(scanIntervalTimer);
            scanIntervalTimer = null;
        }
        detectorInstance = null;

        if (activeStream) {
            try {
                const tracks = activeStream.getTracks();
                tracks.forEach((track) => {
                    try {
                        track.stop();
                    } catch (_) {}
                });
            } catch (_) {}
            activeStream = null;
        }

        if (activeVideoElement) {
            try {
                activeVideoElement.srcObject = null;
            } catch (_) {}
            activeVideoElement = null;
        }
    }

    /**
     * Toggles flashlight / torch if supported by the camera track.
     * @param {boolean} enable
     * @returns {Promise<boolean>} Whether torch toggle succeeded
     */
    async function toggleTorch(enable) {
        if (!activeStream) return false;
        const videoTrack = activeStream.getVideoTracks()[0];
        if (!videoTrack) return false;

        const capabilities = typeof videoTrack.getCapabilities === "function" ? videoTrack.getCapabilities() : {};
        if (!capabilities.torch) {
            return false;
        }

        try {
            await videoTrack.applyConstraints({
                advanced: [{ torch: Boolean(enable) }]
            });
            return true;
        } catch (_) {
            return false;
        }
    }

    /**
     * Resets debounce state (useful for testing or switching modes).
     */
    function resetCooldown() {
        lastDetectedCode = null;
        lastDetectedTimestamp = 0;
    }

    /**
     * Returns internal state snapshot.
     */
    function getState() {
        return {
            isActive: Boolean(activeStream),
            hasVideoElement: Boolean(activeVideoElement),
            lastDetectedCode: lastDetectedCode,
            lastDetectedTimestamp: lastDetectedTimestamp
        };
    }

    const api = {
        SUPPORTED_FORMATS: SUPPORTED_FORMATS,
        DEBOUNCE_COOLDOWN_MS: DEBOUNCE_COOLDOWN_MS,
        isSupported: isSupported,
        startScanner: startScanner,
        stopScanner: stopScanner,
        toggleTorch: toggleTorch,
        captureSnapshot: captureSnapshot,
        handleDetection: handleDetection,
        playBeepSound: playBeepSound,
        triggerHapticFeedback: triggerHapticFeedback,
        resetCooldown: resetCooldown,
        getState: getState
    };

    if (typeof module !== "undefined" && module.exports) {
        module.exports = api;
    } else {
        root.NutriScanCameraScanner = api;
    }
})(typeof window !== "undefined" ? window : globalThis);
