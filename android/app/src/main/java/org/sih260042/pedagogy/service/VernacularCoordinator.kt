package org.sih260042.pedagogy.service

import org.sih260042.pedagogy.contract.*
import org.sih260042.pedagogy.model.*
import java.util.UUID

class VernacularCoordinator(
    private val speechRecognizer: SpeechRecognitionService,
    private val translationService: TranslationService,
    private val contentRegistry: ContentRegistryService
) : VernacularPedagogyCoordinator {

    override fun processSpokenAudio(audio: AudioBuffer): PedagogySessionResponse {
        return processTeacherSpeech(audio)
    }

    override fun processTeacherSpeech(audio: AudioBuffer): PedagogySessionResponse {
        return processTeacherSpeech(audio, null)
    }

    override fun processTeacherSpeech(audio: AudioBuffer, timestamps: PipelineTimestamps?): PedagogySessionResponse {
        val sessionId = UUID.randomUUID().toString()
        val speechResult = speechRecognizer.recognize(audio)

        val diagSummary = "RMS: ${String.format("%.1f", speechResult.rmsEnergy)} | Class: ${speechResult.classIndex ?: 0} (${speechResult.recognizedText ?: "—"}) | Conf: ${String.format("%.2f", speechResult.confidence)} | Margin: ${String.format("%.2f", speechResult.margin)} | Decision: ${speechResult.decision}"

        if (!speechResult.isConfident || speechResult.recognizedText == null) {
            val statusMsg = if (speechResult.status == "SILENCE") {
                "Silence or classroom background noise detected."
            } else {
                "This phrase is not available in the verified classroom vocabulary."
            }
            return PedagogySessionResponse(
                sessionId = sessionId,
                inputMode = "TEACHER_HINDI_VOICE",
                inputContent = speechResult.recognizedText ?: "",
                isSuccess = false,
                statusCode = if (speechResult.status == "SILENCE") "SILENCE_DETECTED" else "UNSUPPORTED_VOCABULARY",
                message = statusMsg,
                speechResult = speechResult,
                translationStatus = "OUT_OF_VOCABULARY_UNVERIFIED",
                hindiText = speechResult.recognizedText,
                confidence = speechResult.confidence,
                fallbackRecommended = true,
                fallbackPathway = "PATHWAY_C_DIRECT_CARD_SELECTION",
                audioStatus = "MISSING",
                latencyBreakdownMs = mapOf(
                    "speech_inference_ms" to speechResult.latencyMs
                ),
                hardwareProfileStatus = "ANDROID_MEASURED_PENDING",
                pipelineTimestamps = timestamps,
                diagnosticSummary = diagSummary
            )
        }

        val recognizedText = speechResult.recognizedText
        val translation = translationService.translate(recognizedText)
        val content = speechResult.classIndex?.let { contentRegistry.getContentByNumber(it) }

        val isVerified = translation.status == "VERIFIED_EDUCATIONAL_LOOKUP" && translation.translatedText != null

        if (!isVerified) {
            return PedagogySessionResponse(
                sessionId = sessionId,
                inputMode = "TEACHER_HINDI_VOICE",
                inputContent = recognizedText,
                isSuccess = false,
                statusCode = "UNSUPPORTED_VOCABULARY",
                message = "This phrase is not available in the verified classroom vocabulary.",
                speechResult = speechResult,
                translationStatus = translation.status,
                hindiText = recognizedText,
                mundariText = null,
                mundariPhonetic = null,
                confidence = speechResult.confidence,
                fallbackRecommended = true,
                fallbackPathway = "PATHWAY_C_DIRECT_CARD_SELECTION",
                audioStatus = "MISSING",
                latencyBreakdownMs = mapOf(
                    "speech_inference_ms" to speechResult.latencyMs
                ),
                hardwareProfileStatus = "ANDROID_MEASURED_PENDING",
                pipelineTimestamps = timestamps,
                diagnosticSummary = "$diagSummary | Translation: ${translation.status}"
            )
        }

        return PedagogySessionResponse(
            sessionId = sessionId,
            inputMode = "TEACHER_HINDI_VOICE",
            inputContent = recognizedText,
            isSuccess = true,
            statusCode = "SUCCESS",
            message = "Recognized numeral $recognizedText",
            speechResult = speechResult,
            translationStatus = translation.status,
            hindiText = translation.sourceText,
            mundariText = translation.translatedText,
            mundariPhonetic = translation.phoneticText,
            confidence = speechResult.confidence,
            contentId = content?.contentId,
            content = content,
            audioAssetPath = content?.audioAssetPath,
            audioId = content?.audioId,
            audioStatus = content?.audioStatus ?: "SYNTHETIC_PROTOTYPE",
            fallbackRecommended = false,
            latencyBreakdownMs = mapOf(
                "speech_inference_ms" to speechResult.latencyMs
            ),
            hardwareProfileStatus = "ANDROID_MEASURED_PENDING",
            pipelineTimestamps = timestamps,
            diagnosticSummary = "$diagSummary | Audio: ${content?.audioStatus ?: "SYNTHETIC_PROTOTYPE"}"
        )
    }

    override fun processTeacherText(hindiText: String): PedagogySessionResponse {
        val sessionId = UUID.randomUUID().toString()
        val translation = translationService.translate(hindiText)
        val isExact = translation.matchType == "EXACT_VERIFIED_LOOKUP"

        var eduContent: EducationalContent? = null
        val num = (translation.metadata["numeral"] as? Int)
        if (num != null) {
            eduContent = contentRegistry.getContentByNumber(num)
        } else {
            val cid = translation.metadata["contentId"] as? String
            if (cid != null) {
                eduContent = contentRegistry.getContentById(cid)
            }
        }

        return PedagogySessionResponse(
            sessionId = sessionId,
            inputMode = "TEACHER_HINDI_TEXT",
            inputContent = hindiText,
            isSuccess = isExact,
            statusCode = if (isExact) "SUCCESS" else translation.status,
            message = if (isExact) "Verified translation lookup" else "Translation unverified or fragmented",
            translationStatus = translation.status,
            hindiText = translation.sourceText,
            mundariText = translation.translatedText,
            mundariPhonetic = translation.phoneticText,
            confidence = translation.confidence,
            contentId = eduContent?.contentId,
            content = eduContent,
            audioAssetPath = eduContent?.audioAssetPath,
            audioId = eduContent?.audioId,
            audioStatus = eduContent?.audioStatus ?: "MISSING",
            fallbackRecommended = !isExact,
            fallbackPathway = "PATHWAY_C_DIRECT_CARD_SELECTION"
        )
    }

    override fun processDirectCardSelection(number: Int): PedagogySessionResponse {
        val sessionId = UUID.randomUUID().toString()
        val content = contentRegistry.getContentByNumber(number)
        if (content == null) {
            return PedagogySessionResponse(
                sessionId = sessionId,
                inputMode = "DIRECT_CARD_SELECTION",
                inputContent = number.toString(),
                isSuccess = false,
                statusCode = "NUMBER_OUT_OF_RANGE",
                message = "Number $number not in range 1-20",
                translationStatus = "NOT_FOUND",
                confidence = 0.0f,
                fallbackRecommended = false,
                audioStatus = "MISSING"
            )
        }

        return PedagogySessionResponse(
            sessionId = sessionId,
            inputMode = "DIRECT_CARD_SELECTION",
            inputContent = number.toString(),
            isSuccess = true,
            statusCode = "SUCCESS",
            message = "Card selected directly (Pathway C)",
            translationStatus = "VERIFIED_EDUCATIONAL_LOOKUP",
            hindiText = content.hindiText,
            mundariText = content.mundariText,
            mundariPhonetic = content.mundariPhonetic,
            confidence = 1.0f,
            contentId = content.contentId,
            content = content,
            audioAssetPath = content.audioAssetPath,
            audioId = content.audioId,
            audioStatus = content.audioStatus,
            fallbackRecommended = false
        )
    }
}
