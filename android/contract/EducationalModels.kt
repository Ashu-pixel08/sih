package org.sih260042.pedagogy.model

/**
 * Foundational Literacy and Numeracy (FLN) educational content asset.
 */
data class EducationalContent(
    val contentId: String,          // e.g. "num_01", "PHR_MGMT_01"
    val category: String,           // "NUMBER", "CLASSROOM_INSTRUCTION", "GREETING", "PRAISE"
    val grade: Int = 1,
    val subject: String = "Mathematics",
    val flnDomain: String = "Foundational Numeracy",
    val topic: String,
    val learningOutcome: String,
    val nipunCompetencyCode: String,
    val nipunStatus: String = "UNVERIFIED — PENDING SOURCE VALIDATION",
    
    // Bilingual Text
    val hindiText: String,
    val hindiNumeral: String? = null,
    val mundariText: String,
    val mundariNumeral: String? = null,
    val mundariPhonetic: String,
    
    // Media Assets
    val flashcardAssetPath: String? = null, // Asset relative path: "flashcards/numbers/card_01.svg"
    val flashcardStatus: String = "GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
    val audioAssetPath: String? = null,     // Asset relative path: "audio/prototype_tts/numbers/num_01.wav"
    val audioId: String? = null,
    val audioStatus: String = "SYNTHETIC_PROTOTYPE", // "SYNTHETIC_PROTOTYPE" or "MISSING"
    
    // Pedagogical Exercises
    val worksheetId: String? = null,
    val recommendedActivityId: String? = null,
    val activityTitle: String? = null,
    val activityInstructionHi: String? = null,
    val activityInstructionUnr: String? = null
)
