# Android Application Architecture Specification

**Project Code**: SIH260042  
**Component**: Mobile Client Architecture (Android Kotlin)  
**Architectural Style**: Clean Architecture + MVVM + Unidirectional Data Flow (UDF)

---

## 1. High-Level Component Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                              │
│                                                                        │
│   ┌────────────────────────┐        ┌──────────────────────────────┐  │
│   │   Jetpack Compose UI   │◄───────┤    PedagogyViewModel         │  │
│   │  (Flashcard, Lesson,   │        │  (StateFlow<PedagogyUiState>)│  │
│   │   Worksheet, Activity) │───────►│  (Handles User Intents)      │  │
│   └────────────────────────┘        └──────────────┬───────────────┘  │
└────────────────────────────────────────────────────┼───────────────────┘
                                                     │
┌────────────────────────────────────────────────────┼───────────────────┐
│                           DOMAIN LAYER             ▼                   │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐  │
│   │                VernacularPedagogyCoordinator                   │  │
│   │                                                                │  │
│   │  ├── ProcessTeacherVoiceUseCase                                │  │
│   │  ├── ProcessStudentSpeechUseCase                               │  │
│   │  ├── ProcessTeacherTextUseCase                                 │  │
│   │  └── DirectCardSelectionUseCase (Pathway C - Fail-Safe)       │  │
│   └────────────────────────┬───────────────────────────────────────┘  │
└────────────────────────────┼───────────────────────────────────────────┘
                             │
┌────────────────────────────┼───────────────────────────────────────────┐
│                    DATA & INFERENCE LAYER (100% OFFLINE)               │
│                            ▼                                           │
│   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│   │ AudioCapture     │  │ AudioPreprocessor│  │ TFLiteInference    │   │
│   │ Service          │  │ (Kotlin DSP)     │  │ Service            │   │
│   │ (AudioRecord)    │  │ (STFT, Log-Mel)  │  │ (speech_model.tfl) │   │
│   └────────┬─────────┘  └────────┬─────────┘  └─────────┬──────────┘   │
│            │                     │                      │              │
│            ▼                     ▼                      ▼              │
│   ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│   │ Translation      │  │ ContentRegistry  │  │ AudioPlayback      │   │
│   │ Repository       │  │ Repository       │  │ Controller         │   │
│   │ (TSV Corpus)     │  │ (JSON Metadata)  │  │ (ExoPlayer/Media)  │   │
│   └──────────────────┘  └──────────────────┘  └────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Interaction Sequences

### 2.1 Pathway D: Teacher Voice Interaction
1. Teacher taps microphone button $\to$ `AudioCaptureService` starts recording PCM at 16 kHz.
2. `StreamingVAD` monitors audio chunks $\to$ detects start of speech.
3. Upon speech pause ($> 400\text{ ms}$ silence), `AudioPreprocessor` runs STFT and extracts Log-Mel spectrogram `[1, 101, 64, 1]`.
4. `TFLiteInferenceService` runs forward pass $\to$ outputs probabilities `[1, 21]`.
5. If confidence $\ge 0.65$ and margin $\ge 0.04$, `TranslationRepository` maps Hindi term to verified Mundari.
6. `ContentRegistryRepository` retrieves lesson plan, SVG flashcard, and worksheet template.
7. `AudioPlaybackController` plays pre-rendered prototype audio asset from APK assets.
8. `PedagogyViewModel` emits updated `PedagogyUiState.Success` to Compose UI.

### 2.2 Pathway C: Direct Card Selection (Guaranteed Presentation Fallback)
1. Teacher or student taps numeral 1–20 card on tablet screen.
2. Zero audio or model inference compute required.
3. `DirectCardSelectionUseCase` queries `ContentRegistryRepository` directly for numeral $N$.
4. Instantaneous deterministic retrieval ($< 2\text{ ms}$).
5. UI displays verified bilingual lesson, flashcard, and worksheet.

---

## 3. Dependency Injection (Hilt / Manual Container)

```kotlin
@Module
@InstallIn(SingletonComponent::class)
object PedagogyModule {

    @Provides
    @Singleton
    fun provideAudioPreprocessor(): AudioPreprocessor = AudioPreprocessor()

    @Provides
    @Singleton
    fun provideSpeechRecognitionService(
        @ApplicationContext context: Context
    ): SpeechRecognitionService = TFLiteSpeechRecognizer(context, "models/speech_model.tflite")

    @Provides
    @Singleton
    fun provideContentRegistryRepository(
        @ApplicationContext context: Context
    ): ContentRegistryRepository = LocalContentRegistryRepository(context, "registry/content_registry.json")

    @Provides
    @Singleton
    fun provideTranslationRepository(
        @ApplicationContext context: Context
    ): TranslationRepository = LocalTranslationRepository(context, "translation/translation-hi-unr.tsv")
}
```
