package org.sih260042.pedagogy.model

/**
 * Complete multi-modal response returned by the Vernacular Pedagogy Manager.
 */
data class PedagogySessionResponse(
    val sessionId: String,
    val inputMode: String, // "TEACHER_HINDI_VOICE", "TEACHER_HINDI_TEXT", "DIRECT_CARD_SELECTION", "SPOKEN_SPEECH"
    val inputContent: String,
    val isSuccess: Boolean,
    val statusCode: String,
    val message: String,
    
    // Speech Recognition Result (null if text or touch input)
    val speechResult: SpeechRecognitionResult? = null,
    
    // Translation Result
    val translationStatus: String,
    val hindiText: String? = null,
    val mundariText: String? = null,
    val mundariPhonetic: String? = null,
    val confidence: Float,
    
    // Educational Content
    val contentId: String? = null,
    val content: EducationalContent? = null,
    
    // Audio Playback
    val audioAssetPath: String? = null,
    val audioId: String? = null,
    val audioStatus: String, // "SYNTHETIC_PROTOTYPE" or "MISSING"
    
    // Fallback Recommendations
    val fallbackRecommended: Boolean,
    val fallbackPathway: String = "PATHWAY_C_DIRECT_CARD_SELECTION",
    
    // Execution Profiling
    val latencyBreakdownMs: Map<String, Float> = emptyMap(),
    val hardwareProfileStatus: String = "ANDROID_MEASURED_PENDING"
)
