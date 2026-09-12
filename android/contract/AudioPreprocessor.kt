package org.sih260042.pedagogy.dsp

import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.*

/**
 * Standard Audio Preprocessing Configuration matching Python AudioPreprocessingConfig.
 */
data class PreprocessingConfig(
    val targetSampleRate: Int = 16000,
    val targetChannels: Int = 1,
    val targetDurationSec: Float = 1.0f,
    val targetSamples: Int = 16000,
    val winLength: Int = 400,        // 25 ms Hann window
    val hopLength: Int = 160,        // 10 ms hop
    val nFft: Int = 512,             // 512-point FFT
    val nMels: Int = 64,             // 64 Mel filterbank bins
    val fMin: Float = 20.0f,
    val fMax: Float = 8000.0f,
    val centerPadding: Boolean = true,
    val logOffset: Float = 1e-6f
) {
    val numFrames: Int get() = 101
    val numFftBins: Int get() = nFft / 2 + 1 // 257 bins
    val totalElements: Int get() = numFrames * nMels // 6464 elements
}

/**
 * Native Kotlin implementation of the STFT and Log-Mel Spectrogram extraction pipeline.
 * Numerically identical to Python scipy/numpy implementation for TFLite / LiteRT input.
 */
class AudioPreprocessor(
    val config: PreprocessingConfig = PreprocessingConfig()
) {
    private val hannWindow: FloatArray = buildHannWindow()
    private val melFilterbank: Array<FloatArray> = buildMelFilterbank()

    /**
     * Builds periodic Hann window matching standard DSP:
     * w[n] = 0.5 * (1.0 - cos(2.0 * PI * n / (winLength - 1)))
     */
    private fun buildHannWindow(): FloatArray {
        val n = config.winLength
        val window = FloatArray(n)
        val factor = 2.0 * Math.PI / (n - 1)
        for (i in 0 until n) {
            window[i] = (0.5 * (1.0 - cos(factor * i))).toFloat()
        }
        return window
    }

    private fun hzToMel(hz: Float): Float {
        return (2595.0 * log10(1.0 + hz / 700.0)).toFloat()
    }

    private fun melToHz(mel: Float): Float {
        return (700.0 * (10.0.pow(mel / 2595.0) - 1.0)).toFloat()
    }

    /**
     * Builds triangular Mel filterbank matrix of shape [nMels, nFft / 2 + 1].
     */
    private fun buildMelFilterbank(): Array<FloatArray> {
        val numFftBins = config.numFftBins
        val melMin = hzToMel(config.fMin)
        val melMax = hzToMel(config.fMax)

        val melPoints = FloatArray(config.nMels + 2)
        val step = (melMax - melMin) / (config.nMels + 1)
        for (i in melPoints.indices) {
            melPoints[i] = melMin + i * step
        }

        val binPoints = IntArray(config.nMels + 2)
        for (i in binPoints.indices) {
            val hz = melToHz(melPoints[i])
            binPoints[i] = floor((config.nFft + 1) * hz / config.targetSampleRate).toInt().coerceIn(0, numFftBins - 1)
        }

        val filterbank = Array(config.nMels) { FloatArray(numFftBins) }
        for (m in 1..config.nMels) {
            val left = binPoints[m - 1]
            val center = binPoints[m]
            val right = binPoints[m + 1]

            if (center > left) {
                for (k in left until center) {
                    filterbank[m - 1][k] = (k - left).toFloat() / (center - left).toFloat()
                }
            }
            if (right > center) {
                for (k in center until right) {
                    filterbank[m - 1][k] = (right - k).toFloat() / (right - center).toFloat()
                }
            }
        }
        return filterbank
    }

    /**
     * Preprocesses input audio buffer into a flat Log-Mel float array [101, 64].
     */
    fun extractLogMelSpectrogram(rawAudio: FloatArray): Array<FloatArray> {
        // Step 1: Normalize and fix length to targetSamples (16,000)
        val fixedAudio = FloatArray(config.targetSamples)
        val copyLen = min(rawAudio.size, config.targetSamples)
        System.arraycopy(rawAudio, 0, fixedAudio, 0, copyLen)

        // Step 2: Center padding (symmetric 200 samples on both sides)
        val pad = config.winLength / 2 // 200 samples
        val paddedAudio = FloatArray(config.targetSamples + 2 * pad)
        // Symmetric reflection padding
        for (i in 0 until pad) {
            paddedAudio[i] = fixedAudio[pad - i]
            paddedAudio[paddedAudio.size - 1 - i] = fixedAudio[config.targetSamples - 1 - (pad - i)]
        }
        System.arraycopy(fixedAudio, 0, paddedAudio, pad, config.targetSamples)

        // Step 3: Compute STFT and Mel filterbank across 101 frames
        val numFrames = config.numFrames
        val spectrogram = Array(numFrames) { FloatArray(config.nMels) }
        val fftReal = DoubleArray(config.nFft)
        val fftImag = DoubleArray(config.nFft)

        for (frameIdx in 0 until numFrames) {
            val startSample = frameIdx * config.hopLength

            // Apply Hann window and zero-pad to nFft (512)
            fftReal.fill(0.0)
            fftImag.fill(0.0)
            for (i in 0 until config.winLength) {
                fftReal[i] = (paddedAudio[startSample + i] * hannWindow[i]).toDouble()
            }

            // In-place Radix-2 Cooley-Tukey FFT (512 points)
            computeFft512(fftReal, fftImag)

            // Compute power spectrum: |X[k]|^2 for k in 0..256
            val powerSpectrum = FloatArray(config.numFftBins)
            for (k in 0 until config.numFftBins) {
                val magSq = (fftReal[k] * fftReal[k] + fftImag[k] * fftImag[k]).toFloat()
                powerSpectrum[k] = magSq
            }

            // Multiply with 64 Mel filterbank bins and apply natural log compression
            for (m in 0 until config.nMels) {
                var melEnergy = 0.0f
                val filter = melFilterbank[m]
                for (k in 0 until config.numFftBins) {
                    melEnergy += powerSpectrum[k] * filter[k]
                }
                spectrogram[frameIdx][m] = ln(melEnergy + config.logOffset)
            }
        }

        return spectrogram
    }

    /**
     * Converts the [101, 64] spectrogram into a direct ByteBuffer formatted for TFLite [1, 101, 64, 1].
     */
    fun toTFLiteInputBuffer(spectrogram: Array<FloatArray>): ByteBuffer {
        val buffer = ByteBuffer.allocateDirect(4 * config.numFrames * config.nMels)
        buffer.order(ByteOrder.nativeOrder())
        buffer.rewind()

        for (t in 0 until config.numFrames) {
            for (m in 0 until config.nMels) {
                buffer.putFloat(spectrogram[t][m])
            }
        }
        buffer.rewind()
        return buffer
    }

    /**
     * In-place Radix-2 Cooley-Tukey FFT for N = 512.
     */
    private fun computeFft512(real: DoubleArray, imag: DoubleArray) {
        val n = 512
        // Bit-reversal permutation
        var j = 0
        for (i in 0 until n - 1) {
            if (i < j) {
                val tempR = real[i]; real[i] = real[j]; real[j] = tempR
                val tempI = imag[i]; imag[i] = imag[j]; imag[j] = tempI
            }
            var k = n shr 1
            while (k <= j) {
                j -= k
                k = k shr 1
            }
            j += k
        }

        // Cooley-Tukey butterflies
        var len = 2
        while (len <= n) {
            val halfLen = len shr 1
            val angle = -2.0 * Math.PI / len
            val wStepR = cos(angle)
            val wStepI = sin(angle)

            var i = 0
            while (i < n) {
                var wR = 1.0
                var wI = 0.0
                for (k in 0 until halfLen) {
                    val uR = real[i + k]
                    val uI = imag[i + k]
                    val vR = real[i + k + halfLen] * wR - imag[i + k + halfLen] * wI
                    val vI = real[i + k + halfLen] * wI + imag[i + k + halfLen] * wR

                    real[i + k] = uR + vR
                    imag[i + k] = uI + vI
                    real[i + k + halfLen] = uR - vR
                    imag[i + k + halfLen] = uI - vI

                    val nextWR = wR * wStepR - wI * wStepI
                    val nextWI = wR * wStepI + wI * wStepR
                    wR = nextWR
                    wI = nextWI
                }
                i += len
            }
            len = len shl 1
        }
    }
}
