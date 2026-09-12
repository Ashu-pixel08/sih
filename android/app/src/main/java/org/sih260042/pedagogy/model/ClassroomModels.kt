package org.sih260042.pedagogy.model

/**
 * Payload broadcasted from Teacher to connected Students in a live classroom.
 */
data class BroadcastPayload(
    val broadcastId: String,
    val roomCode: String,
    val timestampMs: Long = System.currentTimeMillis(),
    val teacherName: String = "Teacher",
    val hindiText: String,
    val mundariText: String,
    val phoneticText: String? = null,
    val verificationStatus: String, // "VERIFIED_EDUCATIONAL_LOOKUP", "CORPUS_RETRIEVAL_MATCH", "OUT_OF_VOCABULARY"
    val audioAssetId: String? = null,
    val visualAssetId: String? = null,
    val activityType: String? = null,
    val metadata: Map<String, String> = emptyMap()
)

/**
 * State and metadata for an active classroom room.
 */
data class ClassroomSessionInfo(
    val roomCode: String,
    val teacherId: String,
    val sessionStartTimeMs: Long = System.currentTimeMillis(),
    val activeStudentCount: Int = 0,
    val isLive: Boolean = true,
    val topic: String = "Foundational Numeracy 1-20"
)

/**
 * Connected student registration entry.
 */
data class StudentRosterEntry(
    val studentId: String,
    val name: String,
    val rollNumber: String,
    val joinedAtMs: Long = System.currentTimeMillis(),
    val isConnected: Boolean = true
)

/**
 * Connection states for live classroom communication.
 */
enum class ClassroomConnectionState {
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    RECONNECTING,
    ERROR
}
