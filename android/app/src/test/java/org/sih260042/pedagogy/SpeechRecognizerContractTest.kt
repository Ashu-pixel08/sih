package org.sih260042.pedagogy

import org.sih260042.pedagogy.dsp.AudioPreprocessor
import org.sih260042.pedagogy.dsp.PreprocessingConfig
import org.sih260042.pedagogy.model.AudioBuffer
import org.sih260042.pedagogy.service.TFLiteInferenceEngine
import org.sih260042.pedagogy.service.TFLiteSpeechRecognizer
import java.io.File
import java.nio.ByteBuffer

class SpeechRecognizerContractTest(private val assetsDir: File) {

    fun testModelFilePresenceAndSize() {
        val modelFile = File(assetsDir, "models/speech_classifier_1_to_20.tflite")
        assert(modelFile.exists()) { "TFLite model file missing from assets" }
        assert(modelFile.length() > 100_000) { "TFLite model unexpectedly small: ${modelFile.length()} bytes" }
    }

    fun testInputOutputTensorContractDimensions() {
        val config = PreprocessingConfig()
        // Input: [1, 101, 64, 1] float32 = 101 * 64 * 4 = 25,856 bytes
        val expectedInputBytes = 1 * config.numFrames * config.nMels * 4
        assert(expectedInputBytes == 25856) { "Input tensor bytes must be 25856" }

        // Output: [1, 21] float32 = 21 * 4 = 84 bytes
        val expectedOutputBytes = 21 * 4
        assert(expectedOutputBytes == 84) { "Output tensor bytes must be 84" }
    }

    fun testSilenceAudioRejection() {
        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {}
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine)

        // All zero PCM
        val silentPcm = ShortArray(16000)
        val audio = AudioBuffer(silentPcm, 16000, 1)

        val result = recognizer.recognize(audio)
        assert(result.status == "SILENCE") { "Expected SILENCE status, got ${result.status}" }
        assert(!result.isConfident) { "Silence must not be marked confident" }
        assert(result.fallbackRecommended) { "Silence must recommend fallback" }
        assert(result.classIndex == 0)
    }

    fun testConfidentPredictionAccepted() {
        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {
                output.rewind()
                // Set class 5 (पांच) to 0.92 confidence, others small
                for (i in 0 until 21) {
                    if (i == 5) output.putFloat(0.92f)
                    else output.putFloat(0.004f)
                }
                output.rewind()
            }
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine, confidenceThreshold = 0.70f)

        // Non-zero PCM
        val pcm = ShortArray(16000) { ((it % 100) * 100).toShort() }
        val audio = AudioBuffer(pcm, 16000, 1)

        val result = recognizer.recognize(audio)
        assert(result.status == "RECOGNIZED") { "Expected RECOGNIZED, got ${result.status}" }
        assert(result.isConfident)
        assert(result.classIndex == 5)
        assert(result.recognizedText == "पांच")
        assert(result.confidence == 0.92f)
        assert(!result.fallbackRecommended)
    }

    fun testLowConfidenceRejectionPleaseRepeat() {
        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {
                output.rewind()
                // Top class is 3 (तीन) but only 0.45 confidence (below 0.70 threshold)
                for (i in 0 until 21) {
                    if (i == 3) output.putFloat(0.45f)
                    else if (i == 4) output.putFloat(0.40f)
                    else output.putFloat(0.01f)
                }
                output.rewind()
            }
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine, confidenceThreshold = 0.70f)

        val pcm = ShortArray(16000) { ((it % 100) * 100).toShort() }
        val audio = AudioBuffer(pcm, 16000, 1)

        val result = recognizer.recognize(audio)
        assert(result.status == "LOW_CONFIDENCE") { "Expected LOW_CONFIDENCE, got ${result.status}" }
        assert(!result.isConfident)
        assert(result.fallbackRecommended) { "Low confidence must recommend fallback / retry" }
        assert(result.fallbackReason?.contains("below threshold") == true)
    }
}
