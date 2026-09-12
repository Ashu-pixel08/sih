package org.sih260042.pedagogy.service

import org.json.JSONObject
import org.sih260042.pedagogy.contract.ContentRegistryService
import org.sih260042.pedagogy.model.EducationalContent
import java.io.InputStream
import java.nio.charset.StandardCharsets

class LocalContentRegistry : ContentRegistryService {
    private val numeralsByNumber = mutableMapOf<Int, EducationalContent>()
    private val contentById = mutableMapOf<String, EducationalContent>()
    private val contentByHindi = mutableMapOf<String, EducationalContent>()
    private val phraseList = mutableListOf<EducationalContent>()

    fun loadRegistryFromJsonString(jsonString: String) {
        val root = JSONObject(jsonString)
        val items = root.getJSONArray("items")
        for (i in 0 until items.length()) {
            val item = items.getJSONObject(i)
            val number = item.getInt("number")
            val labelId = item.getString("label_id")
            val hindiText = item.getString("hindi_text")
            val mundariText = item.getString("mundari_text")
            val mundariPhonetic = item.optString("mundari_phonetic", "")
            val hindiNumeral = item.optString("hindi_numeral", "")
            val mundariNumeral = item.optString("mundari_numeral", "")
            val learningOutcome = item.optString("learning_outcome", "Recognize and count number $number")
            val competencyCode = item.optString("nipun_competency_code", "M1.1")
            
            val audioPath = "audio/prototype_tts/numbers/num_${String.format("%02d", number)}.wav"
            val flashcardPath = "flashcards/numbers/card_${String.format("%02d", number)}.svg"

            val edu = EducationalContent(
                contentId = labelId,
                category = "NUMBER",
                grade = 1,
                subject = "Mathematics",
                flnDomain = "Foundational Numeracy",
                topic = "Numbers 1-20",
                learningOutcome = learningOutcome,
                nipunCompetencyCode = competencyCode,
                hindiText = hindiText,
                hindiNumeral = hindiNumeral,
                mundariText = mundariText,
                mundariNumeral = mundariNumeral,
                mundariPhonetic = mundariPhonetic,
                flashcardAssetPath = flashcardPath,
                flashcardStatus = "GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
                audioAssetPath = audioPath,
                audioId = labelId,
                audioStatus = "SYNTHETIC_PROTOTYPE"
            )
            numeralsByNumber[number] = edu
            contentById[labelId] = edu
            contentByHindi[hindiText] = edu
        }
    }

    fun loadPhrasebookFromJsonString(jsonString: String) {
        val root = JSONObject(jsonString)
        val phrases = root.getJSONArray("phrases")
        for (i in 0 until phrases.length()) {
            val p = phrases.getJSONObject(i)
            val phraseId = p.getString("phrase_id")
            val category = p.optString("category", "CLASSROOM_INSTRUCTION")
            val hindiText = p.getString("hindi_text")
            val mundariText = p.getString("mundari_text")
            val phonetic = p.optString("mundari_phonetic", "")
            val audioPath = "audio/prototype_tts/phrases/$phraseId.wav"

            val edu = EducationalContent(
                contentId = phraseId,
                category = category,
                grade = 1,
                subject = "Pedagogical Interaction",
                flnDomain = "Classroom Management",
                topic = "Teacher Routine",
                learningOutcome = "Classroom instruction in vernacular",
                nipunCompetencyCode = "FLN.CR.1",
                hindiText = hindiText,
                mundariText = mundariText,
                mundariPhonetic = phonetic,
                audioAssetPath = audioPath,
                audioId = phraseId,
                audioStatus = "SYNTHETIC_PROTOTYPE"
            )
            contentById[phraseId] = edu
            contentByHindi[hindiText] = edu
            phraseList.add(edu)
        }
    }

    fun loadFromStreams(registryStream: InputStream, phrasebookStream: InputStream? = null) {
        val regStr = String(registryStream.readBytes(), StandardCharsets.UTF_8)
        loadRegistryFromJsonString(regStr)
        if (phrasebookStream != null) {
            val phrStr = String(phrasebookStream.readBytes(), StandardCharsets.UTF_8)
            loadPhrasebookFromJsonString(phrStr)
        }
    }

    override fun getContentByNumber(number: Int): EducationalContent? = numeralsByNumber[number]
    override fun getContentById(contentId: String): EducationalContent? = contentById[contentId]
    fun getContentByHindi(hindiText: String): EducationalContent? = contentByHindi[hindiText.trim()]
    override fun getAllNumerals(): List<EducationalContent> = numeralsByNumber.values.sortedBy { 
        it.contentId.replace("num_", "").toIntOrNull() ?: 0 
    }
    fun getAllPhrases(): List<EducationalContent> = phraseList.toList()
}
