# Android Testing, Benchmarking & Integration Checklist

**Project Code**: SIH260042  
**Component**: Android Verification & Profiling Protocol

---

## 1. Golden Test Vectors Parity Test

To verify that the Kotlin DSP implementation matches the Python reference implementation down to numerical tolerances, use the pre-generated golden test vectors in `data/test_vectors/`:

1. **Audio Input**: `data/test_vectors/golden_audio_16k.wav`
   - Format: 16,000 Hz, 16-bit PCM, Mono, 1.00 second (16,000 samples).
2. **Expected Output Spectrogram**: `data/test_vectors/golden_spectrogram_101_64.npy`
   - Shape: `[101, 64]` Float32.
   - Numerical Tolerance: Max Absolute Error $< 1.0 \times 10^{-4}$.
3. **Mel Filterbank Matrix**: `data/test_vectors/golden_mel_filterbank_64_257.npy`
   - 64 filters over 257 FFT bins.
4. **Periodic Hann Window**: `data/test_vectors/golden_hann_window_400.json`
   - 400 floating-point coefficients.

### Android Unit Test Example (Robolectric / JUnit)
```kotlin
@Test
fun testAudioPreprocessorMatchesGoldenVector() {
    val context = ApplicationProvider.getApplicationContext<Context>()
    val preprocessor = AudioPreprocessor()
    
    // Read golden WAV from test assets
    val goldenPcm = readPcmFromAsset(context, "golden_audio_16k.wav")
    val spectrogram = preprocessor.extractLogMelSpectrogram(goldenPcm)
    
    val goldenExpected = readNpyFromAsset(context, "golden_spectrogram_101_64.npy")
    
    // Assert shape: 101 frames x 64 bins
    assertEquals(101, spectrogram.size)
    assertEquals(64, spectrogram[0].size)
    
    // Assert numerical parity
    for (t in 0 until 101) {
        for (m in 0 until 64) {
            assertEquals(goldenExpected[t][m], spectrogram[t][m], 1e-4f)
        }
    }
}
```

---

## 2. Physical Device Benchmarking Procedure

When deploying to a physical Android test device (e.g. MediaTek Helio G35 / Snapdragon 450, 2–3 GB RAM), follow this reproducible benchmarking protocol:

### Step 1: Memory Footprint (RAM)
Run via ADB while exercising continuous teacher speech input:
```bash
adb shell dumpsys meminfo org.sih260042.pedagogy
```
- **Target Peak PSS**: $< 75.0\text{ MB}$
- **Target Native Heap**: $< 25.0\text{ MB}$
- **Target Java Heap**: $< 35.0\text{ MB}$

### Step 2: Inference & End-to-End Latency
Measure with Android Simpleperf or code-level `SystemClock.elapsedRealtimeNanos()`:
```kotlin
val t0 = SystemClock.elapsedRealtimeNanos()
val result = coordinator.processTeacherSpeech(audioBuffer)
val elapsedMs = (SystemClock.elapsedRealtimeNanos() - t0) / 1_000_000.0f
Log.i("BENCHMARK", "End-to-End Latency: $elapsedMs ms")
```
- **Target Preprocessing Latency**: $< 15.0\text{ ms}$
- **Target Speech Inference Latency**: $< 65.0\text{ ms}$
- **Target Total End-to-End Latency**: $< 120.0\text{ ms}$

### Step 3: Battery & Thermal Profiling
1. Run continuous speech recognition for 30 minutes.
2. Monitor battery temperature via ADB:
   ```bash
   adb shell dumpsys battery
   ```
3. Ensure battery temperature remains below $42^\circ\text{C}$ and no CPU thermal throttling occurs.

---

## 3. Android Developer Integration Checklist

Before declaring Android integration complete, verify every item on this checklist:

- [ ] **1. Offline Guarantee**: App runs in Airplane Mode with WiFi and Cellular disabled.
- [ ] **2. Audio Format**: `AudioRecord` configured for 16,000 Hz, 16-bit PCM, Mono.
- [ ] **3. Preprocessing Parity**: Kotlin `AudioPreprocessor` produces `[1, 101, 64, 1]` matching golden tensor.
- [ ] **4. TFLite Execution**: `speech_model.tflite` loads without errors using standard LiteRT runtime.
- [ ] **5. Fallback Protection**: Silent audio ($< -45\text{ dBFS}$) safely triggers `SILENCE_DETECTED_FALLBACK`.
- [ ] **6. Ambiguity Protection**: Low confidence ($< 0.65$) prompts Pathway C (Direct Touch Card Mode).
- [ ] **7. Missing Audio Handling**: Missing audio assets do not throw exceptions; visual pedagogy renders gracefully.
- [ ] **8. Zero Hallucination**: Out-of-vocabulary Hindi input yields `OUT_OF_VOCABULARY_UNVERIFIED`.
- [ ] **9. Asset Integrity**: All 20 flashcard SVGs and 36 prototype audio WAVs exist in APK assets.
- [ ] **10. UI Thread Safety**: Audio capture, DSP, and model inference run strictly off the Main thread.
