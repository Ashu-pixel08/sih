# Audio Preprocessing Specification & Cross-Platform Contract

This specification establishes the mathematical DSP parameters for speech recognition feature extraction in our offline FLN pedagogy assistant. It is strictly shared between the Python training/evaluation pipeline and the Android Kotlin edge runtime.

---

## 1. Specification Matrix

| Parameter | Value | DSP Definition / Rationale | Kotlin Parity Equivalent |
| :--- | :--- | :--- | :--- |
| **Input Audio Source** | Microphone / File | Classroom audio recording | Android `AudioRecord` |
| **Audio Sample Rate** | **16,000 Hz (16 kHz)** | Standard speech bandwidth (up to 8 kHz Nyquist) | `AudioFormat.SAMPLE_RATE_16000` |
| **Channel Count** | **1 (Mono)** | Single-channel speech signal | `AudioFormat.CHANNEL_IN_MONO` |
| **Sample Encoding** | **16-bit Linear PCM** | Scaled to Float32 range `[-1.0, 1.0]` (`val / 32768.0f`) | `AudioFormat.ENCODING_PCM_16BIT` |
| **Fixed Time Window** | **1.00 second** | Optimized for isolated monosyllabic/disyllabic words | 16,000 samples buffer |
| **Window Type** | **Hann Window** | $w[n] = 0.5 \times (1 - \cos(\frac{2\pi n}{N - 1}))$ | Symmetric Hann array |
| **Window Length ($N$)** | **400 samples** | $400 / 16000 = 25.0\text{ ms}$ frame width | Array of 400 floats |
| **Hop Length ($H$)** | **160 samples** | $160 / 16000 = 10.0\text{ ms}$ step size | Step loop by 160 |
| **FFT Size ($N_{\text{fft}}$)** | **512 points** | Power-of-2 zero-padded from 400 | Real-to-Complex FFT 512 |
| **Frequency Bins** | **257 bins** | $N_{\text{fft}} / 2 + 1 = 257$ bins ($0\text{ Hz}$ to $8000\text{ Hz}$) | Half-spectrum magnitude |
| **Mel Filterbank Bins** | **64 bins** | Logarithmic perceptual frequency resolution | 64 triangular filter rows |
| **Min Frequency ($f_{\min}$)** | **20.0 Hz** | High-pass cutoff below vocal fundamental | Filterbank lower bound |
| **Max Frequency ($f_{\max}$)** | **8,000.0 Hz** | Nyquist frequency at 16 kHz sample rate | Filterbank upper bound |
| **STFT Centering** | **Reflect / Symmetric** | Left pad 200, right pad 200 samples ($16,400$ total) | Pad 200 samples before STFT |
| **Number of Time Frames** | **101 frames** | $\lfloor (16400 - 400) / 160 \rfloor + 1 = 101$ | Exactly 101 outer loop steps |
| **Log Compression** | $\log(E + 10^{-6})$ | Natural log of Mel power with stabilizer | `ln(melEnergy + 1e-6f)` |
| **Verified Spectrogram Shape** | **`[101, 64]`** | `[TimeFrames, MelBins]` | 2D FloatArray `101 x 64` |
| **Model Input Tensor** | **`[1, 101, 64, 1]`** | `[Batch, TimeFrames, MelBins, Channels]` | 4D ByteBuffer for TFLite |
| **Tensor Dtype** | **`FLOAT32`** | Standard 32-bit single precision IEEE 754 | `FloatBuffer` |

---

## 2. Mathematical Derivation of Tensor Dimensions

1. **Signal Duration**:
   $$\text{Duration} = 1.0\text{ s} \implies L = 16,000\text{ samples at } 16\text{ kHz}$$

2. **Centered STFT Padding**:
   $$\text{pad} = \frac{\text{win\_length}}{2} = \frac{400}{2} = 200\text{ samples}$$
   $$L_{\text{padded}} = 16000 + 2 \times 200 = 16,400\text{ samples}$$

3. **Time Frame Count**:
   $$N_{\text{frames}} = \left\lfloor \frac{L_{\text{padded}} - \text{win\_length}}{\text{hop\_length}} \right\rfloor + 1 = \frac{16400 - 400}{160} + 1 = \frac{16000}{160} + 1 = 100 + 1 = \mathbf{101}\text{ frames}$$

4. **FFT Frequency Bins**:
   $$K = \frac{N_{\text{fft}}}{2} + 1 = \frac{512}{2} + 1 = \mathbf{257}\text{ bins}$$

5. **Mel Projection**:
   $$\text{Mel Spectrogram} = \text{Power STFT} [101, 257] \times (\text{Mel Matrix} [64, 257])^T = [101, 64]$$

6. **Model Input Tensor Reshaping**:
   $$\text{Tensor} = \text{Reshape}([101, 64]) \implies \mathbf{[1, 101, 64, 1]}$$

---

## 3. Kotlin Android Implementation Guide

To ensure mathematical parity between Android and Python:

```kotlin
class AudioPreprocessor(
    val sampleRate: Int = 16000,
    val windowLength: Int = 400,
    val hopLength: Int = 160,
    val nFft: Int = 512,
    val nMels: Int = 64
) {
    // Mel filterbank matrix: 64 rows, 257 columns (precomputed from assets/mel_filterbank.bin)
    private val melFilterbank = loadMelFilterbank()
    
    // Hann window: 400 floats: 0.5 * (1 - cos(2 * pi * i / 399))
    private val hannWindow = FloatArray(400) { i ->
        (0.5 * (1.0 - Math.cos(2.0 * Math.PI * i / 399.0))).toFloat()
    }

    fun preprocessAudio(rawPcm16: ShortArray): Array<Array<FloatArray>> {
        // 1. Normalize PCM ShortArray to FloatArray [-1.0f, 1.0f]
        val audio = FloatArray(16000) { i ->
            if (i < rawPcm16.size) rawPcm16[i] / 32768.0f else 0.0f
        }

        // 2. Symmetric pad 200 samples left & right
        val padded = FloatArray(16400)
        // reflect left pad
        for (i in 0 until 200) padded[i] = audio[200 - i]
        System.arraycopy(audio, 0, padded, 200, 16000)
        // reflect right pad
        for (i in 0 until 200) padded[16200 + i] = audio[15999 - i]

        // 3. Frame-by-frame STFT & Mel projection (101 frames)
        val spectrogram = Array(101) { FloatArray(64) }
        val fftBuffer = FloatArray(512)

        for (frame in 0 until 101) {
            val start = frame * hopLength
            // Apply Hann window and zero pad to 512
            fftBuffer.fill(0.0f)
            for (i in 0 until 400) {
                fftBuffer[i] = padded[start + i] * hannWindow[i]
            }

            // Real FFT 512 -> power spectrum (257 bins)
            val powerSpectrum = computeRealFftPower(fftBuffer)

            // Dot product with 64 Mel filterbank rows
            for (m in 0 until 64) {
                var melEnergy = 0.0f
                for (k in 0 until 257) {
                    melEnergy += powerSpectrum[k] * melFilterbank[m][k]
                }
                spectrogram[frame][m] = Math.log((melEnergy + 1e-6f).toDouble()).toFloat()
            }
        }

        // Output shaped as [1, 101, 64, 1] for TFLite Interpreter
        return formatAs4DTensor(spectrogram)
    }
}
```
