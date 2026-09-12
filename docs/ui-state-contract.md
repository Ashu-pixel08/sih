# UI State Contract & Lifecycle Specification

**Project Code**: SIH260042  
**Component**: State Machine and Screen Contracts for APP_NAME_PENDING  
**Operating Mode**: Deterministic Finite State Machine (FSM)  
**Deployment Status**: OFFLINE ARCHITECTURE READY — PHYSICAL ANDROID VALIDATION PENDING  

---

## 1. Global Screen State Hierarchy

Every screen in the application observes a standardized state envelope:

```kotlin
sealed class ScreenState<out T> {
    object Idle : ScreenState<Nothing>()
    data class Loading(val message: String = "Processing...") : ScreenState<Nothing>()
    data class Success<out T>(val data: T) : ScreenState<T>()
    data class Fallback(val reason: FallbackReason, val data: T? = null) : ScreenState<T>()
    data class Error(val code: ErrorCode, val message: String) : ScreenState<Nothing>()
}
```

---

## 2. Voice Interaction State Machine (Teacher)

```
       ┌─────────────┐
       │    IDLE     │◄───────────────────┐
       └──────┬──────┘                    │
              │ onMicPressed              │
              ▼                           │
       ┌─────────────┐                    │
       │  LISTENING  │                    │
       └──────┬──────┘                    │
              │ VAD speech end            │
              ▼                           │
       ┌─────────────┐                    │
       │ PROCESSING  │                    │
       └──────┬──────┘                    │
              │ Inference complete        │
       ┌──────┴──────────────────────┐    │
       │                             │    │
       ▼                             ▼    │
┌──────────────┐             ┌────────────┴──┐
│    REVIEW    │             │   FALLBACK    │
│  (Confident) │             │ (Ambiguous/   │
└──────┬───────┘             │    Noise)     │
       │ onBroadcastApproved └───────────────┘
       ▼
┌──────────────┐
│  BROADCAST   │──────────────────────────┘
└──────────────┘
```

### State Definitions:
1. **IDLE**: Microphone is inactive. System listens for touch inputs or button presses.
2. **LISTENING**: Microphone capturing PCM chunks at 16 kHz. VAD tracking speech energy against ambient floor.
3. **PROCESSING**: DSP feature extraction (`AudioPreprocessor`) -> TFLite acoustic inference -> Translation -> Content lookup.
4. **REVIEW**: Translation and phonetics rendered on teacher preview card. Teacher verifies accuracy before broadcast.
5. **FALLBACK**:
   - `LOW_CONFIDENCE`: Speech model confidence < 0.65. UI highlights top-3 candidate cards with "Tap to Select".
   - `SILENCE`: No speech detected within 2.0s. Prompts teacher to speak.
   - `HIGH_NOISE`: Ambient SNR < 5 dB. Prompts teacher to move closer to microphone.
   - `OUT_OF_VOCABULARY`: Utterance outside FLN domain. Recommends manual topic search.
6. **BROADCAST**: Content payload transmitted to connected student devices via `ClassroomSessionService` (contract ready).

---

## 3. Strict Verification Status Contract

### 3.1 Text Status Contract
Every text translation must display its precise provenance status:

| Text Status Code | UI Badge Text | Badge Style | Meaning & Governance Rule |
| :--- | :--- | :--- | :--- |
| `EXACT_CANONICAL_LOOKUP` | `● EXACT_CANONICAL_LOOKUP` | Green (`#2d6339`) | Exact 1-to-1 match in canonical Grade 1 FLN vocabulary registry. |
| `CORPUS_ATTESTED` | `● CORPUS_ATTESTED` | Green (`#2d6339`) | Attested in reference bilingual lexicography or parallel corpus. |
| `CORPUS_RETRIEVAL_MATCH` | `● CORPUS_RETRIEVAL_MATCH` | Blue (`#24543D`) | Matched via character 3-gram TF-IDF corpus retrieval. |
| `LINGUISTICALLY_REVIEWED`| `● LINGUISTICALLY_REVIEWED`| Green (`#2d6339`) | Reviewed by a qualified linguist/expert. |
| `NATIVE_VALIDATED` | `● NATIVE_VALIDATED` | Gold (`#735d11`) | Formally validated by native speaker educator (PENDING FIELD DATA). |
| `OUT_OF_VOCABULARY` | `⚠ OUT_OF_VOCABULARY` | Red (`#8a332e`) | Unattested phrase. Never broadcast as authoritative translation. |

### 3.2 Audio Status Contract
Audio status must NEVER be implied from text status:

| Audio Status Code | UI Badge Text | Badge Style | Meaning & Governance Rule |
| :--- | :--- | :--- | :--- |
| `SYNTHETIC_PROTOTYPE` | `⚙ SYNTHETIC_PROTOTYPE` | Gray (`#59645e`) | Generated TTS prototype. Pending native-speaker field validation. |
| `REAL_RECORDING_UNVERIFIED`| `🎙 REAL_UNVERIFIED` | Blue (`#24543D`) | Field recording received but pending linguistic review. |
| `NATIVE_VALIDATED` | `● NATIVE_VALIDATED` | Gold (`#735d11`) | Authentic native recording passing technical and linguistic QA. |

---

## 4. Student Receiver State Contract

The Student Live Classroom screen manages the following reactive states:

```kotlin
data class StudentLiveState(
    val connectionStatus: ClassroomConnectionState, // DISCONNECTED, CONNECTING, CONNECTED, RECONNECTING, ERROR
    val roomCode: String?,
    val teacherName: String?,
    val activeBroadcast: BroadcastPayload?,
    val isAudioPlaying: Boolean,
    val audioProgressPercent: Int
)
```

- **Guardrail**: If `verificationStatus == "OUT_OF_VOCABULARY"`, the student receiver displays an "Unverified content suppressed" safeguard to prevent incorrect language acquisition.
