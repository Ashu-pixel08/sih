package org.sih260042.pedagogy

import org.sih260042.pedagogy.service.LocalContentRegistry
import java.io.File

class LocalContentRegistryTest(private val assetsDir: File) {

    fun testLoadRegistry20Numerals() {
        val registryFile = File(assetsDir, "content/content_registry.json")
        assert(registryFile.exists()) { "content_registry.json missing from assets" }

        val registry = LocalContentRegistry()
        registry.loadRegistryFromJsonString(registryFile.readText(Charsets.UTF_8))

        val numerals = registry.getAllNumerals()
        assert(numerals.size == 20) { "Expected 20 numerals, got ${numerals.size}" }

        // Verify numerals 1 to 20
        for (i in 1..20) {
            val item = registry.getContentByNumber(i)
            assert(item != null) { "Missing numeral $i in registry" }
            assert(item!!.contentId == String.format("num_%02d", i)) { "Invalid contentId for $i: ${item.contentId}" }
            assert(item.hindiText.isNotEmpty()) { "Missing Hindi text for $i" }
            assert(item.mundariText.isNotEmpty()) { "Missing Mundari text for $i" }
            assert(item.mundariPhonetic.isNotEmpty()) { "Missing Mundari phonetic for $i" }
            assert(item.audioAssetPath != null) { "Missing audio asset path for $i" }

            // Verify audio asset physically exists in assets directory
            val audioFile = File(assetsDir, item.audioAssetPath!!)
            assert(audioFile.exists()) { "Audio asset does not exist on disk: ${item.audioAssetPath}" }
            assert(audioFile.length() > 0) { "Audio asset is empty: ${item.audioAssetPath}" }
        }

        // Test specific canonical values from content_registry.json
        val num1 = registry.getContentByNumber(1)!!
        assert(num1.hindiText == "एक")
        assert(num1.mundariText == "मिअद")
        assert(num1.mundariPhonetic == "miad")

        // Canonical verification for Numeral 5: "मोड़ेया" (NOT "मोनेया")
        val num5 = registry.getContentByNumber(5)!!
        assert(num5.hindiText == "पाँच")
        assert(num5.mundariText == "मोड़ेया") { "Canonical #5 Mundari text must be 'मोड़ेया', got ${num5.mundariText}" }
        assert(num5.mundariPhonetic == "môṛẽa")

        // Canonical verification for Numeral 7: "एयाएया"
        val num7 = registry.getContentByNumber(7)!!
        assert(num7.hindiText == "सात")
        assert(num7.mundariText == "एयाएया")

        // Canonical verification for Numeral 10: "गेलेया"
        val num10 = registry.getContentByNumber(10)!!
        assert(num10.hindiText == "दस")
        assert(num10.mundariText == "गेलेया")
    }

    fun testLoadClassroomPhrasebook() {
        val phrasebookFile = File(assetsDir, "content/classroom_phrasebook.json")
        if (phrasebookFile.exists()) {
            val registry = LocalContentRegistry()
            registry.loadPhrasebookFromJsonString(phrasebookFile.readText(Charsets.UTF_8))
            val phrases = registry.getAllPhrases()
            assert(phrases.size == 16) { "Expected 16 phrases, got ${phrases.size}" }
            
            val greeting = registry.getContentById("PHR_GREET_01")
            assert(greeting != null) { "PHR_GREET_01 missing" }
            assert(greeting!!.hindiText == "नमस्ते")
            assert(greeting.mundariText == "जोहार")

            val sitDown = registry.getContentById("PHR_MGMT_01")
            assert(sitDown != null) { "PHR_MGMT_01 missing" }
            assert(sitDown!!.hindiText == "बैठो")
            assert(sitDown.mundariText == "दुबपे")
        }
    }

    fun testDynamicLoadingProofNoHardcodedKotlinDictionary() {
        // Test proves LocalContentRegistry dynamically parses whatever JSON string is provided,
        // rather than using a static, hardcoded Kotlin dictionary.
        val syntheticJson = """
        {
          "items": [
            {
              "class_index": 99,
              "label_id": "num_99",
              "number": 99,
              "hindi_numeral": "९९",
              "hindi_text": "परीक्षण_संख्या",
              "mundari_numeral": "99",
              "mundari_text": "डायनामिक_लोडिंग_सफल",
              "mundari_root": "टेस्ट",
              "mundari_phonetic": "dynamic_test",
              "linguistic_status": "CORPUS_ATTESTED",
              "learning_outcome": "Dynamic loading verification"
            }
          ]
        }
        """
        val dynamicRegistry = LocalContentRegistry()
        dynamicRegistry.loadRegistryFromJsonString(syntheticJson)

        val item99 = dynamicRegistry.getContentByNumber(99)
        assert(item99 != null) { "Dynamic item 99 was not loaded from JSON" }
        assert(item99!!.mundariText == "डायनामिक_लोडिंग_सफल") { 
            "Expected dynamic string 'डायनामिक_लोडिंग_सफल', got ${item99.mundariText}" 
        }
        // Verify canonical numbers are NOT in this fresh registry instance
        assert(dynamicRegistry.getContentByNumber(1) == null) {
            "Isolated registry instance should have no entries before loading"
        }
    }
}
