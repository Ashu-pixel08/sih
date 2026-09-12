package org.sih260042.pedagogy

import org.sih260042.pedagogy.service.LocalContentRegistry
import org.sih260042.pedagogy.service.LocalTranslationEngine
import java.io.File

class LocalTranslationEngineTest(private val assetsDir: File) {

    private fun setupEngine(): LocalTranslationEngine {
        val registryFile = File(assetsDir, "content/content_registry.json")
        val phrasebookFile = File(assetsDir, "content/classroom_phrasebook.json")

        val registry = LocalContentRegistry()
        registry.loadRegistryFromJsonString(registryFile.readText(Charsets.UTF_8))
        if (phrasebookFile.exists()) {
            registry.loadPhrasebookFromJsonString(phrasebookFile.readText(Charsets.UTF_8))
        }
        return LocalTranslationEngine(registry)
    }

    fun testExactCanonicalNumeralLookup() {
        val engine = setupEngine()

        // Test Word 1: "एक" -> "मिअद"
        val r0 = engine.translate("एक")
        assert(r0.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r0.translatedText == "मिअद")
        assert(r0.verificationStatus == "CORPUS_ATTESTED")
        assert(r0.metadata["isBroadcastable"] == true) { "Canonical numeral must be broadcastable" }

        // Test Word 5: "पांच" -> "मोड़ेया" (Canonical: मोड़ेया, NOT मोनेया)
        val r1 = engine.translate("पांच")
        assert(r1.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r1.translatedText == "मोड़ेया") { "Expected canonical 'मोड़ेया', got ${r1.translatedText}" }
        assert(r1.verificationStatus == "CORPUS_ATTESTED")
        assert(r1.metadata["isBroadcastable"] == true)

        // Test Digit: "5" -> "मोड़ेया"
        val r2 = engine.translate("5")
        assert(r2.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r2.translatedText == "मोड़ेया")
        assert(r2.metadata["isBroadcastable"] == true)

        // Test Devanagari digit: "५" -> "मोड़ेया"
        val r3 = engine.translate("५")
        assert(r3.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r3.translatedText == "मोड़ेया")
        assert(r3.metadata["isBroadcastable"] == true)

        // Test Word 20: "बीस" -> "हिसि"
        val r4 = engine.translate("बीस")
        assert(r4.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r4.translatedText == "हिसि")
        assert(r4.metadata["isBroadcastable"] == true)
    }

    fun testExactAttestedPhraseLookup() {
        val engine = setupEngine()

        val r = engine.translate("नमस्ते")
        assert(r.matchType == "EXACT_VERIFIED_LOOKUP")
        assert(r.translatedText == "जोहार")
        assert(r.verificationStatus == "CORPUS_ATTESTED")
        assert(r.metadata["isBroadcastable"] == true) { "Attested classroom phrase must be broadcastable" }
    }

    fun testComposedSentenceBroadcastBlocked() {
        val engine = setupEngine()

        // Composed sentence from fragments: "बच्चों, आज हम एक सेब के बारे में सीखेंगे।"
        val input = "बच्चों, आज हम एक सेब के बारे में सीखेंगे।"
        val r = engine.translate(input)
        
        assert(r.status == "COMPOSED_FROM_ATTESTED_FRAGMENTS") { "Expected COMPOSED_FROM_ATTESTED_FRAGMENTS, got ${r.status}" }
        assert(r.verificationStatus == "COMPOSED_FROM_ATTESTED_FRAGMENTS")
        // CRITICAL SAFETY RULE: Must NOT be broadcastable!
        assert(r.metadata["isBroadcastable"] == false) { "Composed sentence MUST NOT be broadcastable" }
        assert(r.translatedText == null) { "Must not fabricate a full translation for unverified sentences" }
    }

    fun testOutOfVocabularyBroadcastBlocked() {
        val engine = setupEngine()

        val r = engine.translate("अपरिचित शब्द")
        assert(r.matchType == "OUT_OF_VOCABULARY")
        assert(r.status == "OUT_OF_VOCABULARY_UNVERIFIED")
        assert(r.translatedText == null)
        assert(r.metadata["isBroadcastable"] == false) { "OOV word MUST NOT be broadcastable" }
    }
}
