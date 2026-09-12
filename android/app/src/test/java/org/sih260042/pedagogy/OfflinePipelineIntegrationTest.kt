package org.sih260042.pedagogy

import org.sih260042.pedagogy.dsp.PreprocessingConfig
import org.sih260042.pedagogy.model.AudioBuffer
import org.sih260042.pedagogy.service.*
import java.io.File
import java.nio.ByteBuffer

class OfflinePipelineIntegrationTest(
    private val assetsDir: File,
    private val manifestFile: File
) {

    fun testOfflineArchitecturalGuarantee() {
        assert(manifestFile.exists()) { "AndroidManifest.xml missing" }
        val manifestText = manifestFile.readText(Charsets.UTF_8)
        
        // Assert RECORD_AUDIO is present
        assert(manifestText.contains("android.permission.RECORD_AUDIO")) {
            "RECORD_AUDIO permission must be declared in AndroidManifest.xml"
        }

        // CRITICAL OFFLINE GUARANTEE: INTERNET uses-permission MUST NOT be declared!
        assert(!manifestText.contains("<uses-permission android:name=\"android.permission.INTERNET\"") &&
               !manifestText.contains("<uses-permission android:name='android.permission.INTERNET'")) {
            "SECURITY/OFFLINE VIOLATION: android.permission.INTERNET found in AndroidManifest.xml!"
        }
    }

    fun testPathwayCDirectCardSelectionFallback() {
        val registryFile = File(assetsDir, "content/content_registry.json")
        val registry = LocalContentRegistry()
        registry.loadRegistryFromJsonString(registryFile.readText(Charsets.UTF_8))
        val translationEngine = LocalTranslationEngine(registry)

        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {}
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine)
        val coordinator = VernacularCoordinator(recognizer, translationEngine, registry)

        // Teacher selects card 7 directly (Pathway C)
        val response = coordinator.processDirectCardSelection(7)
        assert(response.isSuccess)
        assert(response.inputMode == "DIRECT_CARD_SELECTION")
        assert(response.hindiText == "सात")
        assert(response.mundariText == "एयाएया") { "Expected canonical 'एयाएया', got ${response.mundariText}" }
        assert(response.mundariPhonetic == "ēyāēa")
        assert(response.confidence == 1.0f)
        assert(response.audioAssetPath == "audio/prototype_tts/numbers/num_07.wav")
        assert(!response.fallbackRecommended)
    }

    fun testEndToEndCoordinatorFlow() {
        val registryFile = File(assetsDir, "content/content_registry.json")
        val registry = LocalContentRegistry()
        registry.loadRegistryFromJsonString(registryFile.readText(Charsets.UTF_8))
        val translationEngine = LocalTranslationEngine(registry)

        // Mock engine that predicts "दस" (numeral 10) with 0.95 confidence
        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {
                output.rewind()
                for (i in 0 until 21) {
                    if (i == 10) output.putFloat(0.95f)
                    else output.putFloat(0.002f)
                }
                output.rewind()
            }
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine)
        val coordinator = VernacularCoordinator(recognizer, translationEngine, registry)

        val pcm = ShortArray(16000) { ((it % 50) * 150).toShort() }
        val audio = AudioBuffer(pcm, 16000, 1)

        val response = coordinator.processTeacherSpeech(audio)
        assert(response.isSuccess) { "Coordinator processing failed: ${response.message}" }
        assert(response.hindiText == "दस")
        assert(response.mundariText == "गेलेया") { "Expected canonical 'गेलेया', got ${response.mundariText}" }
        assert(response.audioAssetPath == "audio/prototype_tts/numbers/num_10.wav")
        assert(response.confidence == 0.95f)
        assert(response.audioStatus == "SYNTHETIC_PROTOTYPE")
    }

    fun testPipelineTimestampsAndDiagnostics() {
        val registryFile = File(assetsDir, "content/content_registry.json")
        val registry = LocalContentRegistry()
        registry.loadRegistryFromJsonString(registryFile.readText(Charsets.UTF_8))
        val translationEngine = LocalTranslationEngine(registry)

        val mockEngine = object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {
                output.rewind()
                for (i in 0 until 21) {
                    if (i == 1) output.putFloat(0.98f)
                    else output.putFloat(0.001f)
                }
                output.rewind()
            }
        }
        val recognizer = TFLiteSpeechRecognizer(mockEngine)
        val coordinator = VernacularCoordinator(recognizer, translationEngine, registry)

        val pcm = ShortArray(16000) { ((it % 50) * 150).toShort() }
        val audio = AudioBuffer(pcm, 16000, 1)

        val t0 = 1000L
        val t1 = 2000L
        val t2 = 2015L
        val t3 = 2018L
        val t4 = 2020L
        val timestamps = org.sih260042.pedagogy.model.PipelineTimestamps(
            t0CaptureStartMs = t0,
            t1CaptureEndMs = t1,
            t2InferenceEndMs = t2,
            t3TranslationEndMs = t3,
            t4AudioDispatchMs = t4
        )

        assert(timestamps.captureDurationMs == 1000f)
        assert(timestamps.inferenceLatencyMs == 15f)
        assert(timestamps.translationLatencyMs == 3f)
        assert(timestamps.audioDispatchLatencyMs == 2f)
        assert(timestamps.totalProcessingLatencyMs == 20f)
        assert(timestamps.totalEndToEndLatencyMs == 1020f)

        val response = coordinator.processTeacherSpeech(audio, timestamps)
        assert(response.isSuccess)
        assert(response.pipelineTimestamps != null)
        assert(response.pipelineTimestamps?.captureDurationMs == 1000f)
        assert(response.diagnosticSummary != null)
        assert(response.diagnosticSummary?.contains("RMS:") == true)
        assert(response.diagnosticSummary?.contains("Decision: ACCEPTED") == true)
        assert(response.hardwareProfileStatus == "ANDROID_MEASURED_PENDING")
    }
}
