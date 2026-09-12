package org.sih260042.pedagogy.contract

import org.sih260042.pedagogy.model.*

/**
 * Interface managing multi-device or local classroom synchronization.
 * Offline-first design: implementations may use Local Wi-Fi P2P, Hotspot Multicast, or Local Mock Bus.
 */
interface ClassroomSessionService {
    // Teacher lifecycle
    fun createRoom(topic: String = "Foundational Numeracy 1-20"): ClassroomSessionInfo
    fun endRoom(roomCode: String)
    fun broadcastToStudents(payload: BroadcastPayload)
    fun getConnectedStudents(): List<StudentRosterEntry>

    // Student lifecycle
    fun joinRoom(roomCode: String, student: StudentRosterEntry, onMessageReceived: (BroadcastPayload) -> Unit): Boolean
    fun leaveRoom()
    val connectionState: ClassroomConnectionState

    // Observation
    fun observeBroadcasts(callback: (BroadcastPayload) -> Unit)
}
