package org.sih260042.pedagogy.model

/**
 * Tracks a student's practice attempt on an FLN pedagogical activity.
 */
data class ActivityAttempt(
    val attemptId: String,
    val studentId: String,
    val activityType: String, // "identify_number", "count_objects", "find_successor"
    val targetConcept: String, // e.g. "num_07"
    val selectedAnswer: String,
    val isCorrect: Boolean,
    val responseTimeMs: Long,
    val timestampMs: Long = System.currentTimeMillis()
)

/**
 * Aggregate progress for an individual student.
 */
data class StudentProgressRecord(
    val studentId: String,
    val studentName: String,
    val rollNumber: String,
    val totalAttempts: Int,
    val correctAttempts: Int,
    val accuracyPercent: Float,
    val masteredConceptsCount: Int,
    val lastActiveTimestampMs: Long,
    val status: String // "ON_TRACK", "NEEDS_SUPPORT", "EXCELLING"
)

/**
 * Summary analytics for the teacher's classroom view.
 */
data class ClassroomProgressSummary(
    val classId: String,
    val totalStudents: Int,
    val averagePracticePercent: Float,
    val activeStudentsThisWeek: Int,
    val studentRecords: List<StudentProgressRecord>,
    val dataSourceTag: String = "LOCAL_CLASSROOM_DATA"
)
