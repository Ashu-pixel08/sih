package org.sih260042.pedagogy.model

/**
 * Speech capture input specification for AudioRecord.
 */
data class AudioInputConfig(
    val sampleRate: Int = 16000,
    val channelCount: Int = 1,
    val bitDepth: Int = 16,
    val bufferSizeBytes: Int = 1280, // 40 ms chunk at 16 kHz
    val targetDurationSec: Float = 1.0f,
    val targetSamples: Int = 16000
)

/**
 * Standardized raw audio buffer captured from Android AudioRecord.
 */
data class AudioBuffer(
    val pcmData: ShortArray,
    val sampleRate: Int = 16000,
    val channelCount: Int = 1,
    val durationSec: Float = pcmData.size.toFloat() / sampleRate.toFloat(),
    val timestampMs: Long = System.currentTimeMillis()
) {
    /**
     * Converts 16-bit PCM to Float32 in range [-1.0, 1.0].
     */
    fun toFloatArray(): FloatArray {
        val floatData = FloatArray(pcmData.size)
        for (i in pcmData.indices) {
            floatData[i] = pcmData[i] / 32768.0f
        }
        return floatData
    }

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as AudioBuffer
        return pcmData.contentEquals(other.pcmData) &&
               sampleRate == other.sampleRate &&
               channelCount == other.channelCount
    }

    override fun hashCode(): Int {
        var result = pcmData.contentHashCode()
        result = 31 * result + sampleRate
        result = 31 * result + channelCount
        return result
    }
}

/**
 * Classification and recognition result from on-device speech inference.
 */
data class SpeechRecognitionResult(
    val recognizedText: String?,
    val classIndex: Int?, // 0 to 20 for numerals (0 = background/unknown)
    val confidence: Float, // 0.0 to 1.0
    val margin: Float,     // Margin over second-highest class
    val status: String,    // "RECOGNIZED", "SILENCE", "LOW_CONFIDENCE", "HIGH_NOISE", "AUDIO_DEFECT"
    val isConfident: Boolean,
    val durationSec: Float,
    val latencyMs: Float,
    val engineName: String,
    val fallbackRecommended: Boolean,
    val fallbackReason: String? = null,
    // Phase 9 Diagnostic metrics
    val rmsEnergy: Float = 0.0f,
    val secondBestConfidence: Float = 0.0f,
    val secondBestClassIndex: Int? = null,
    val decision: String = if (isConfident) "ACCEPTED" else "REJECTED"
)

/**
 * Lightweight timestamp profiling for on-device execution (T0 - T4).
 */
data class PipelineTimestamps(
    val t0CaptureStartMs: Long = 0L,
    val t1CaptureEndMs: Long = 0L,
    val t2InferenceEndMs: Long = 0L,
    val t3TranslationEndMs: Long = 0L,
    val t4AudioDispatchMs: Long = 0L,
    val captureDurationMs: Float = (t1CaptureEndMs - t0CaptureStartMs).coerceAtLeast(0L).toFloat(),
    val inferenceLatencyMs: Float = (t2InferenceEndMs - t1CaptureEndMs).coerceAtLeast(0L).toFloat(),
    val translationLatencyMs: Float = (t3TranslationEndMs - t2InferenceEndMs).coerceAtLeast(0L).toFloat(),
    val audioDispatchLatencyMs: Float = (t4AudioDispatchMs - t3TranslationEndMs).coerceAtLeast(0L).toFloat(),
    val totalProcessingLatencyMs: Float = (t4AudioDispatchMs - t1CaptureEndMs).coerceAtLeast(0L).toFloat(),
    val totalEndToEndLatencyMs: Float = (t4AudioDispatchMs - t0CaptureStartMs).coerceAtLeast(0L).toFloat()
)
