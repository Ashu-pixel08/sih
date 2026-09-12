package org.sih260042.pedagogy.model

/**
 * Bilingual translation result bridging teacher instruction to vernacular pedagogy.
 */
data class TranslationResult(
    val sourceLanguage: String = "hi",
    val targetLanguage: String = "unr",
    val sourceText: String,
    val normalizedSource: String,
    val translatedText: String?,
    val phoneticText: String? = null,
    val confidence: Float,
    val matchType: String,      // "EXACT_VERIFIED_LOOKUP", "CORPUS_RETRIEVAL_MATCH", "OUT_OF_VOCABULARY"
    val status: String,         // "VERIFIED_EDUCATIONAL_LOOKUP", "CORPUS_RETRIEVAL_MATCH", "OUT_OF_VOCABULARY_UNVERIFIED"
    val provenance: String,
    val verificationStatus: String, // "CORPUS_ATTESTED", "LINGUISTICALLY_REVIEWED", "UNVERIFIED"
    val metadata: Map<String, Any> = emptyMap()
)
