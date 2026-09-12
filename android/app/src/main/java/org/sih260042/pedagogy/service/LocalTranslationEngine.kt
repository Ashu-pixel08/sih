package org.sih260042.pedagogy.service

import org.sih260042.pedagogy.contract.TranslationService
import org.sih260042.pedagogy.model.TranslationResult

class LocalTranslationEngine(
    private val registry: LocalContentRegistry
) : TranslationService {

    private val numeralWordToNumber = mapOf(
        "एक" to 1, "दो" to 2, "तीन" to 3, "चार" to 4, "पांच" to 5, "पाँच" to 5,
        "छह" to 6, "छः" to 6, "छ:" to 6, "सात" to 7, "आठ" to 8, "नौ" to 9, "दस" to 10,
        "ग्यारह" to 11, "बारह" to 12, "तेरह" to 13, "चौदह" to 14, "पंद्रह" to 15,
        "सोलह" to 16, "सत्रह" to 17, "अठारह" to 18, "उन्नीस" to 19, "बीस" to 20
    )

    private val digitToWord = mapOf(
        "1" to "एक", "2" to "दो", "3" to "तीन", "4" to "चार", "5" to "पांच",
        "6" to "छह", "7" to "सात", "8" to "आठ", "9" to "नौ", "10" to "दस",
        "11" to "ग्यारह", "12" to "बारह", "13" to "तेरह", "14" to "चौदह", "15" to "पंद्रह",
        "16" to "सोलह", "17" to "सत्रह", "18" to "अठारह", "19" to "उन्नीस", "20" to "बीस",
        "१" to "एक", "२" to "दो", "३" to "तीन", "४" to "चार", "५" to "पांच",
        "६" to "छह", "७" to "सात", "८" to "आठ", "९" to "नौ", "१०" to "दस",
        "११" to "ग्यारह", "१२" to "बारह", "१३" to "तेरह", "१४" to "चौदह", "१५" to "पंद्रह",
        "१६" to "सोलह", "१७" to "सत्रह", "१८" to "अठारह", "१९" to "उन्नीस", "२०" to "बीस"
    )

    fun normalizeHindi(rawText: String): String {
        var clean = rawText.trim()
        clean = clean.replace(Regex("[.,?!;:।॥\"'()]+"), "")
        clean = clean.trim()
        digitToWord[clean]?.let { return it }
        if (clean == "पाँच") return "पांच"
        if (clean == "छः" || clean == "छ:") return "छह"
        return clean
    }

    override fun translate(hindiText: String): TranslationResult {
        val normalized = normalizeHindi(hindiText)

        // Check if normalized matches an attested numeral in the registry
        val num = numeralWordToNumber[normalized]
        if (num != null) {
            val content = registry.getContentByNumber(num)
            if (content != null) {
                return TranslationResult(
                    sourceLanguage = "hi",
                    targetLanguage = "unr",
                    sourceText = hindiText,
                    normalizedSource = normalized,
                    translatedText = content.mundariText,
                    phoneticText = content.mundariPhonetic,
                    confidence = 1.0f,
                    matchType = "EXACT_VERIFIED_LOOKUP",
                    status = "VERIFIED_EDUCATIONAL_LOOKUP",
                    provenance = "CORPUS_ATTESTED",
                    verificationStatus = "CORPUS_ATTESTED",
                    metadata = mapOf(
                        "isBroadcastable" to true,
                        "contentId" to content.contentId,
                        "numeral" to num
                    )
                )
            }
        }

        // Check if matches an attested classroom phrase
        val phraseContent = registry.getContentByHindi(normalized)
        if (phraseContent != null) {
            return TranslationResult(
                sourceLanguage = "hi",
                targetLanguage = "unr",
                sourceText = hindiText,
                normalizedSource = normalized,
                translatedText = phraseContent.mundariText,
                phoneticText = phraseContent.mundariPhonetic,
                confidence = 1.0f,
                matchType = "EXACT_VERIFIED_LOOKUP",
                status = "VERIFIED_EDUCATIONAL_LOOKUP",
                provenance = "CORPUS_ATTESTED",
                verificationStatus = "CORPUS_ATTESTED",
                metadata = mapOf(
                    "isBroadcastable" to true,
                    "contentId" to phraseContent.contentId
                )
            )
        }

        // Check for compound sentences containing fragments
        // CRITICAL SAFETY RULE: COMPOSED_FROM_ATTESTED_FRAGMENTS -> isBroadcastable MUST be false
        val words = normalized.split(Regex("\\s+"))
        var matchedFragments = 0
        for (w in words) {
            if (numeralWordToNumber.containsKey(w) || registry.getContentByHindi(w) != null) {
                matchedFragments++
            }
        }

        if (words.size > 1 && matchedFragments > 0) {
            return TranslationResult(
                sourceLanguage = "hi",
                targetLanguage = "unr",
                sourceText = hindiText,
                normalizedSource = normalized,
                translatedText = null, // Do NOT invent complete Mundari translation
                phoneticText = null,
                confidence = 0.5f,
                matchType = "COMPOSED_FROM_ATTESTED_FRAGMENTS",
                status = "COMPOSED_FROM_ATTESTED_FRAGMENTS",
                provenance = "COMPOSED_FROM_ATTESTED_FRAGMENTS",
                verificationStatus = "COMPOSED_FROM_ATTESTED_FRAGMENTS",
                metadata = mapOf(
                    "isBroadcastable" to false,
                    "reason" to "Full sentence is unverified and cannot be broadcast."
                )
            )
        }

        // Out of Vocabulary
        return TranslationResult(
            sourceLanguage = "hi",
            targetLanguage = "unr",
            sourceText = hindiText,
            normalizedSource = normalized,
            translatedText = null,
            phoneticText = null,
            confidence = 0.0f,
            matchType = "OUT_OF_VOCABULARY",
            status = "OUT_OF_VOCABULARY_UNVERIFIED",
            provenance = "OUT_OF_VOCABULARY",
            verificationStatus = "UNVERIFIED",
            metadata = mapOf(
                "isBroadcastable" to false,
                "reason" to "Word or phrase not in canonical registry."
            )
        )
    }
}
