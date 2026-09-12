package org.sih260042.pedagogy.service

import org.sih260042.pedagogy.contract.SpeechRecognitionService
import org.sih260042.pedagogy.dsp.AudioPreprocessor
import org.sih260042.pedagogy.dsp.PreprocessingConfig
import org.sih260042.pedagogy.model.AudioBuffer
import org.sih260042.pedagogy.model.SpeechRecognitionResult
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.sqrt

/**
 * Interface abstraction for TFLite / LiteRT inference execution.
 * Allows running via Android's org.tensorflow.lite.Interpreter or mock/host engine in JVM tests.
 */
interface TFLiteInferenceEngine {
    fun run(input: ByteBuffer, output: ByteBuffer)
}

class TFLiteSpeechRecognizer(
    private val inferenceEngine: TFLiteInferenceEngine,
    val config: PreprocessingConfig = PreprocessingConfig(),
    val confidenceThreshold: Float = 0.70f,
    val marginThreshold: Float = 0.10f
) : SpeechRecognitionService {

    private val preprocessor = AudioPreprocessor(config)

    companion object {
        val CLASS_LABELS = arrayOf(
            "_background_", // 0: Silence, ambient noise, unknown
            "एक",   // 1
            "दो",   // 2
            "तीन",  // 3
            "चार",  // 4
            "पांच", // 5
            "छह",   // 6
            "सात",  // 7
            "आठ",   // 8
            "नौ",   // 9
            "दस",   // 10
            "ग्यारह", // 11
            "बारह",  // 12
            "तेरह",  // 13
            "चौदह",  // 14
            "पंद्रह", // 15
            "सोलह",  // 16
            "सत्रह", // 17
            "अठारह", // 18
            "उन्नीस", // 19
            "बीस"   // 20
        )
    }

    override fun recognize(audio: AudioBuffer): SpeechRecognitionResult {
        val startTime = System.nanoTime()

        // Step 1: Check audio signal energy (RMS check)
        var sumSq = 0.0
        for (sample in audio.pcmData) {
            sumSq += (sample.toDouble() * sample.toDouble())
        }
        val rms = if (audio.pcmData.isNotEmpty()) sqrt(sumSq / audio.pcmData.size).toFloat() else 0.0f

        // If audio is practically silent (RMS < 30 on 16-bit PCM scale)
        if (rms < 30.0f) {
            val latency = (System.nanoTime() - startTime) / 1_000_000.0f
            return SpeechRecognitionResult(
                recognizedText = null,
                classIndex = 0,
                confidence = 0.0f,
                margin = 0.0f,
                status = "SILENCE",
                isConfident = false,
                durationSec = audio.durationSec,
                latencyMs = latency,
                engineName = "TFLiteSpeechClassifier_1_20",
                fallbackRecommended = true,
                fallbackReason = "Audio signal is below silence threshold (RMS: ${String.format("%.1f", rms)})",
                rmsEnergy = rms,
                secondBestConfidence = 0.0f,
                secondBestClassIndex = null,
                decision = "REJECTED_SILENCE"
            )
        }

        // Step 2: DSP Log-Mel Spectrogram extraction [101, 64]
        val floatAudio = audio.toFloatArray()
        val spectrogram = preprocessor.extractLogMelSpectrogram(floatAudio)
        val inputBuffer = preprocessor.toTFLiteInputBuffer(spectrogram)

        // Step 3: Run edge neural inference
        // Output tensor shape: [1, 21] float32 (21 classes * 4 bytes = 84 bytes)
        val outputBuffer = ByteBuffer.allocateDirect(CLASS_LABELS.size * 4)
        outputBuffer.order(ByteOrder.nativeOrder())
        outputBuffer.rewind()

        inferenceEngine.run(inputBuffer, outputBuffer)
        outputBuffer.rewind()

        val probabilities = FloatArray(CLASS_LABELS.size)
        for (i in probabilities.indices) {
            probabilities[i] = outputBuffer.float
        }

        // Step 4: Find top-1 and top-2 class indices
        var top1Idx = 0
        var top1Prob = -1.0f
        var top2Idx = -1
        var top2Prob = -1.0f

        for (i in probabilities.indices) {
            val p = probabilities[i]
            if (p > top1Prob) {
                top2Prob = top1Prob
                top2Idx = top1Idx
                top1Prob = p
                top1Idx = i
            } else if (p > top2Prob) {
                top2Prob = p
                top2Idx = i
            }
        }

        val secondBestIdx = if (top2Idx >= 0) top2Idx else null
        val secondBestProb = maxOf(0.0f, top2Prob)
        val margin = top1Prob - secondBestProb
        val latency = (System.nanoTime() - startTime) / 1_000_000.0f

        // Step 5: Decision Logic
        if (top1Idx == 0) {
            return SpeechRecognitionResult(
                recognizedText = null,
                classIndex = 0,
                confidence = top1Prob,
                margin = margin,
                status = "SILENCE",
                isConfident = false,
                durationSec = audio.durationSec,
                latencyMs = latency,
                engineName = "TFLiteSpeechClassifier_1_20",
                fallbackRecommended = true,
                fallbackReason = "Ambient noise or silence classified as background",
                rmsEnergy = rms,
                secondBestConfidence = secondBestProb,
                secondBestClassIndex = secondBestIdx,
                decision = "REJECTED_BACKGROUND"
            )
        }

        if (top1Prob < confidenceThreshold || margin < marginThreshold) {
            return SpeechRecognitionResult(
                recognizedText = CLASS_LABELS[top1Idx],
                classIndex = top1Idx,
                confidence = top1Prob,
                margin = margin,
                status = "LOW_CONFIDENCE",
                isConfident = false,
                durationSec = audio.durationSec,
                latencyMs = latency,
                engineName = "TFLiteSpeechClassifier_1_20",
                fallbackRecommended = true,
                fallbackReason = "Confidence (${String.format("%.2f", top1Prob)}) below threshold ($confidenceThreshold)",
                rmsEnergy = rms,
                secondBestConfidence = secondBestProb,
                secondBestClassIndex = secondBestIdx,
                decision = "REJECTED_LOW_CONFIDENCE"
            )
        }

        return SpeechRecognitionResult(
            recognizedText = CLASS_LABELS[top1Idx],
            classIndex = top1Idx,
            confidence = top1Prob,
            margin = margin,
            status = "RECOGNIZED",
            isConfident = true,
            durationSec = audio.durationSec,
            latencyMs = latency,
            engineName = "TFLiteSpeechClassifier_1_20",
            fallbackRecommended = false,
            fallbackReason = null,
            rmsEnergy = rms,
            secondBestConfidence = secondBestProb,
            secondBestClassIndex = secondBestIdx,
            decision = "ACCEPTED"
        )
    }

    override fun close() {
    }
}
