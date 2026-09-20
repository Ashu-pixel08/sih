package org.sih260042.pedagogy

import java.io.File

object AndroidNativeTestSuite {

    @JvmStatic
    fun main(args: Array<String>) {
        val workspaceRoot = if (args.isNotEmpty()) File(args[0]) else File(".")
        val androidAppDir = File(workspaceRoot, "android/app")
        val assetsDir = File(androidAppDir, "src/main/assets")
        val manifestFile = File(androidAppDir, "src/main/AndroidManifest.xml")

        println("================================================================================")
        println("  PROJECT SIH260042: ANDROID NATIVE PIPELINE TEST SUITE (PHASE J & AUDIT)")
        println("  Application Name: Bhasha Setu")
        println("  Package: org.sih260042.pedagogy")
        println("================================================================================")

        var totalTests = 0
        var passedTests = 0
        var failedTests = 0

        fun runTest(name: String, testAction: () -> Unit) {
            totalTests++
            print(String.format("  [%02d/15] %-60s ", totalTests, name))
            try {
                testAction()
                passedTests++
                println("✔ PASS")
            } catch (e: Throwable) {
                failedTests++
                println("✘ FAIL")
                println("       Error: ${e.message}")
                e.printStackTrace()
            }
        }

        val preprocessorTests = AudioPreprocessorTest()
        val registryTests = LocalContentRegistryTest(assetsDir)
        val translationTests = LocalTranslationEngineTest(assetsDir)
        val recognizerTests = SpeechRecognizerContractTest(assetsDir)
        val integrationTests = OfflinePipelineIntegrationTest(assetsDir, manifestFile)

        // 1. Model asset file presence & load
        runTest("1. Model asset file presence & load") {
            recognizerTests.testModelFilePresenceAndSize()
        }

        // 2. Input tensor shape [1, 101, 64, 1]
        runTest("2. Input tensor contract shape [1, 101, 64, 1]") {
            recognizerTests.testInputOutputTensorContractDimensions()
        }

        // 3. Output tensor shape [1, 21]
        runTest("3. Output tensor contract shape [1, 21]") {
            recognizerTests.testInputOutputTensorContractDimensions()
        }

        // 4. Content registry 20 canonical items
        runTest("4. Content registry loads all 20 canonical items") {
            registryTests.testLoadRegistry20Numerals()
        }

        // 5. Dynamic loading verification (proof against hardcoded dict)
        runTest("5. Dynamic asset parsing proof (no hardcoded dictionary)") {
            registryTests.testDynamicLoadingProofNoHardcodedKotlinDictionary()
        }

        // 6. Confidence threshold logic
        runTest("6. Confidence threshold logic (>= 0.70 accepted)") {
            recognizerTests.testConfidentPredictionAccepted()
        }

        // 7. Low-confidence rejection ("Please repeat")
        runTest("7. Low-confidence rejection prompts 'Please repeat'") {
            recognizerTests.testLowConfidenceRejectionPleaseRepeat()
        }

        // 8. Missing entry safety (OOV broadcast blocked)
        runTest("8. Missing entry safety (OOV broadcast blocked)") {
            translationTests.testOutOfVocabularyBroadcastBlocked()
        }

        // 9. Audio asset path mapping
        runTest("9. Audio asset path mapping (all 20 exist on disk)") {
            registryTests.testLoadRegistry20Numerals()
        }

        // 10. Preprocessor DSP specifications (Hann, Mel, STFT)
        runTest("10. AudioPreprocessor DSP specs (Hann, Mel, STFT)") {
            preprocessorTests.testHannWindowSpecification()
            preprocessorTests.testSpectrogramOutputShapeAndBuffer()
        }

        // 11. Preprocessor silence & numerical baseline
        runTest("11. Preprocessor silence & numerical baseline") {
            preprocessorTests.testEmptyOrSilenceSpectrogram()
        }

        // 12. Offline guarantee (zero internet permission in manifest)
        runTest("12. Offline architectural guarantee (No INTERNET perm)") {
            integrationTests.testOfflineArchitecturalGuarantee()
        }

        // 13. Empty/zero PCM handling (silence detection)
        runTest("13. Empty / zero PCM rejection (RMS silence check)") {
            recognizerTests.testSilenceAudioRejection()
        }

        // 14. Exact canonical translation (Numeral 5: 'मोड़ेया')
        runTest("14. Exact canonical numeral lookup (5 -> 'मोड़ेया')") {
            translationTests.testExactCanonicalNumeralLookup()
        }

        // 15. End-to-end offline pipeline & Pathway C fallback
        runTest("15. End-to-end offline pipeline & Pathway C fallback") {
            integrationTests.testPathwayCDirectCardSelectionFallback()
            integrationTests.testEndToEndCoordinatorFlow()
            integrationTests.testPipelineTimestampsAndDiagnostics()
            translationTests.testExactAttestedPhraseLookup()
            translationTests.testComposedSentenceBroadcastBlocked()
        }

        println("================================================================================")
        println("  TEST RESULTS SUMMARY:")
        println("  Total Tests:  $totalTests")
        println("  Passed:       $passedTests")
        println("  Failed:       $failedTests")
        println("================================================================================")

        if (failedTests > 0) {
            System.exit(1)
        }
    }
}
