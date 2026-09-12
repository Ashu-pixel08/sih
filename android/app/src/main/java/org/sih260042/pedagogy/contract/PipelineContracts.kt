package org.sih260042.pedagogy.contract

import org.sih260042.pedagogy.model.*

/**
 * Service capturing raw audio from hardware microphone.
 */
interface AudioCaptureService {
    fun startCapture(chunkCallback: (AudioBuffer) -> Unit)
    fun stopCapture()
    val isCapturing: Boolean
}

/**
 * Dual-stage Voice Activity Detector filtering classroom ambient noise.
 */
interface VoiceActivityDetector {
    fun processChunk(chunk: AudioBuffer): Boolean // Returns true if speech active
    fun reset()
}

/**
 * Speech Recognition Service executing edge neural inference.
 */
interface SpeechRecognitionService {
    fun recognize(audio: AudioBuffer): SpeechRecognitionResult
    fun close()
}

/**
 * Offline Translation Engine bridging Hindi to Mundari.
 */
interface TranslationService {
    fun translate(hindiText: String): TranslationResult
}

/**
 * Curriculum Content Registry retrieving FLN lessons, flashcards, and activities.
 */
interface ContentRegistryService {
    fun getContentByNumber(number: Int): EducationalContent?
    fun getContentById(contentId: String): EducationalContent?
    fun getAllNumerals(): List<EducationalContent>
}

/**
 * Unified Coordinator orchestrating end-to-end multi-modal interaction.
 */
interface VernacularPedagogyCoordinator {
    fun processSpokenAudio(audio: AudioBuffer): PedagogySessionResponse
    fun processTeacherSpeech(audio: AudioBuffer): PedagogySessionResponse
    fun processTeacherSpeech(audio: AudioBuffer, timestamps: PipelineTimestamps?): PedagogySessionResponse
    fun processTeacherText(hindiText: String): PedagogySessionResponse
    fun processDirectCardSelection(number: Int): PedagogySessionResponse
}
