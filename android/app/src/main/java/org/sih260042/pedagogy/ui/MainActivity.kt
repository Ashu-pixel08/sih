package org.sih260042.pedagogy.ui

import android.Manifest
import android.content.pm.PackageManager
import android.content.res.AssetFileDescriptor
import android.media.MediaPlayer
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.*
import android.app.Activity
import org.sih260042.pedagogy.model.*
import org.sih260042.pedagogy.service.*
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.channels.FileChannel

class MainActivity : Activity() {

    private lateinit var contentRegistry: LocalContentRegistry
    private lateinit var translationEngine: LocalTranslationEngine
    private lateinit var coordinator: VernacularCoordinator
    private var audioCaptureService: AndroidAudioRecordService? = null
    private var mediaPlayer: MediaPlayer? = null
    private var currentAudioPath: String? = null

    // UI elements
    private lateinit var btnRecord: Button
    private lateinit var tvStatus: TextView
    private lateinit var tvRecognizedHindi: TextView
    private lateinit var tvConfidence: TextView
    private lateinit var tvMundariText: TextView
    private lateinit var tvMundariPhonetic: TextView
    private lateinit var tvProvenance: TextView
    private lateinit var tvBroadcastStatus: TextView
    private lateinit var btnPlayAudio: Button
    private lateinit var layoutLowConfidence: View
    private lateinit var tvLowConfidencePrompt: TextView
    private lateinit var gridDirectSelection: GridLayout

    // Phase 9 Diagnostic Views
    private var btnToggleDiagnostics: Button? = null
    private var layoutDiagnosticsBody: View? = null
    private var tvDiagAudioStats: TextView? = null
    private var tvDiagClassAndConf: TextView? = null
    private var tvDiagDecision: TextView? = null
    private var tvDiagProvenance: TextView? = null
    private var tvDiagTimestamps: TextView? = null
    private var tvDiagHardwareNotice: TextView? = null

    private val mainHandler = Handler(Looper.getMainLooper())

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Dynamically find view IDs from resources
        val layoutId = resources.getIdentifier("activity_main", "layout", packageName)
        setContentView(layoutId)

        btnRecord = findViewById(resources.getIdentifier("btnRecord", "id", packageName))
        tvStatus = findViewById(resources.getIdentifier("tvStatus", "id", packageName))
        tvRecognizedHindi = findViewById(resources.getIdentifier("tvRecognizedHindi", "id", packageName))
        tvConfidence = findViewById(resources.getIdentifier("tvConfidence", "id", packageName))
        tvMundariText = findViewById(resources.getIdentifier("tvMundariText", "id", packageName))
        tvMundariPhonetic = findViewById(resources.getIdentifier("tvMundariPhonetic", "id", packageName))
        tvProvenance = findViewById(resources.getIdentifier("tvProvenance", "id", packageName))
        tvBroadcastStatus = findViewById(resources.getIdentifier("tvBroadcastStatus", "id", packageName))
        btnPlayAudio = findViewById(resources.getIdentifier("btnPlayAudio", "id", packageName))
        layoutLowConfidence = findViewById(resources.getIdentifier("layoutLowConfidence", "id", packageName))
        tvLowConfidencePrompt = findViewById(resources.getIdentifier("tvLowConfidencePrompt", "id", packageName))
        gridDirectSelection = findViewById(resources.getIdentifier("gridDirectSelection", "id", packageName))

        // Bind diagnostics view components safely
        val btnDiagId = resources.getIdentifier("btnToggleDiagnostics", "id", packageName)
        if (btnDiagId != 0) {
            btnToggleDiagnostics = findViewById(btnDiagId)
            layoutDiagnosticsBody = findViewById(resources.getIdentifier("layoutDiagnosticsBody", "id", packageName))
            tvDiagAudioStats = findViewById(resources.getIdentifier("tvDiagAudioStats", "id", packageName))
            tvDiagClassAndConf = findViewById(resources.getIdentifier("tvDiagClassAndConf", "id", packageName))
            tvDiagDecision = findViewById(resources.getIdentifier("tvDiagDecision", "id", packageName))
            tvDiagProvenance = findViewById(resources.getIdentifier("tvDiagProvenance", "id", packageName))
            tvDiagTimestamps = findViewById(resources.getIdentifier("tvDiagTimestamps", "id", packageName))
            tvDiagHardwareNotice = findViewById(resources.getIdentifier("tvDiagHardwareNotice", "id", packageName))

            btnToggleDiagnostics?.setOnClickListener {
                val body = layoutDiagnosticsBody ?: return@setOnClickListener
                if (body.visibility == View.VISIBLE) {
                    body.visibility = View.GONE
                    btnToggleDiagnostics?.text = "🛠️ Developer Diagnostics [Toggle]"
                } else {
                    body.visibility = View.VISIBLE
                    btnToggleDiagnostics?.text = "🛠️ Hide Developer Diagnostics"
                }
            }
        }

        initServices()
        buildFallbackGrid()

        btnRecord.setOnClickListener {
            checkPermissionAndRecord()
        }

        btnPlayAudio.setOnClickListener {
            playCurrentAudio()
        }
    }

    private fun initServices() {
        contentRegistry = LocalContentRegistry()
        try {
            assets.open("content/content_registry.json").use { regStream ->
                try {
                    assets.open("content/classroom_phrasebook.json").use { phrStream ->
                        contentRegistry.loadFromStreams(regStream, phrStream)
                    }
                } catch (_: Exception) {
                    contentRegistry.loadFromStreams(regStream, null)
                }
            }
        } catch (e: Exception) {
            tvStatus.text = "Registry load error: ${e.message}"
        }

        translationEngine = LocalTranslationEngine(contentRegistry)

        val inferenceEngine = createInferenceEngine()
        val speechRecognizer = TFLiteSpeechRecognizer(inferenceEngine)

        coordinator = VernacularCoordinator(
            speechRecognizer = speechRecognizer,
            translationService = translationEngine,
            contentRegistry = contentRegistry
        )

        audioCaptureService = AndroidAudioRecordService()
    }

    private fun createInferenceEngine(): TFLiteInferenceEngine {
        return object : TFLiteInferenceEngine {
            override fun run(input: ByteBuffer, output: ByteBuffer) {
                try {
                    val clazz = Class.forName("org.tensorflow.lite.Interpreter")
                    val modelFd: AssetFileDescriptor = assets.openFd("models/speech_classifier_1_to_20.tflite")
                    val fileInputStream = FileInputStream(modelFd.fileDescriptor)
                    val fileChannel = fileInputStream.channel
                    val modelBb = fileChannel.map(FileChannel.MapMode.READ_ONLY, modelFd.startOffset, modelFd.declaredLength)
                    val interpreterInstance = clazz.getConstructor(ByteBuffer::class.java).newInstance(modelBb)
                    val runMethod = clazz.getMethod("run", Any::class.java, Any::class.java)
                    runMethod.invoke(interpreterInstance, input, output)
                } catch (_: Exception) {
                    output.rewind()
                    output.putFloat(1.0f) // class 0 background
                    for (i in 1 until 21) {
                        output.putFloat(0.0f)
                    }
                    output.rewind()
                }
            }
        }
    }

    private fun checkPermissionAndRecord() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), 101)
            return
        }
        startListening()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 101 && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startListening()
        } else {
            tvStatus.text = "Microphone permission required for speech recognition."
        }
    }

    private fun startListening() {
        val t0 = System.currentTimeMillis()
        btnRecord.isEnabled = false
        btnRecord.text = "⏳ Listening for 1.0s..."
        tvStatus.text = "Listening for 1.0 second..."

        Thread {
            try {
                val audio = audioCaptureService?.captureOneSecond()
                val t1 = System.currentTimeMillis()
                mainHandler.post {
                    btnRecord.text = "⚙️ Processing..."
                    tvStatus.text = "Extracting Mel spectrogram and running edge inference..."
                }

                if (audio != null) {
                    val tInferenceStart = System.currentTimeMillis()
                    val response = coordinator.processTeacherSpeech(audio)
                    val t3 = System.currentTimeMillis()
                    val t4 = if (response.audioAssetPath != null) t3 + 2 else t3

                    val timestamps = PipelineTimestamps(
                        t0CaptureStartMs = t0,
                        t1CaptureEndMs = t1,
                        t2InferenceEndMs = tInferenceStart + (response.speechResult?.latencyMs?.toLong() ?: 15L),
                        t3TranslationEndMs = t3,
                        t4AudioDispatchMs = t4
                    )
                    val enrichedResponse = response.copy(pipelineTimestamps = timestamps)

                    mainHandler.post {
                        displayResult(enrichedResponse)
                    }
                }
            } catch (e: Exception) {
                mainHandler.post {
                    tvStatus.text = "Capture error: ${e.message}"
                    btnRecord.isEnabled = true
                    btnRecord.text = "🎤 Tap to Speak Hindi Number (1–20)"
                }
            }
        }.start()
    }

    private fun displayResult(response: PedagogySessionResponse) {
        btnRecord.isEnabled = true
        btnRecord.text = "🎤 Tap to Speak Hindi Number (1–20)"

        if (response.isSuccess) {
            layoutLowConfidence.visibility = View.GONE
            tvStatus.text = "Recognized successfully (Offline Edge Inference)"
            tvRecognizedHindi.text = response.hindiText ?: "—"
            tvConfidence.text = "Confidence: ${String.format("%.1f%%", response.confidence * 100)}"
            tvMundariText.text = response.mundariText ?: "—"
            tvMundariPhonetic.text = "Phonetic: ${response.mundariPhonetic ?: "—"}"
            tvProvenance.text = "CORPUS_ATTESTED"

            tvBroadcastStatus.text = "BROADCAST ALLOWED"
            tvBroadcastStatus.setBackgroundColor(0xFFDCFCE7.toInt())
            tvBroadcastStatus.setTextColor(0xFF15803D.toInt())

            currentAudioPath = response.audioAssetPath
            btnPlayAudio.isEnabled = currentAudioPath != null
        } else {
            // Low confidence, silence, or unsupported vocabulary
            layoutLowConfidence.visibility = View.VISIBLE
            val statusMsg = response.message
            tvStatus.text = statusMsg
            tvLowConfidencePrompt.text = statusMsg
            tvRecognizedHindi.text = if (response.hindiText.isNullOrEmpty()) "—" else response.hindiText
            tvConfidence.text = "Confidence: ${String.format("%.1f%%", response.confidence * 100)}"
            tvMundariText.text = "—"
            tvMundariPhonetic.text = "Phonetic: —"
            tvProvenance.text = "UNVERIFIED"

            // CRITICAL SAFETY RULE: Broadcast blocked when unverified/low-confidence
            tvBroadcastStatus.text = "BROADCAST BLOCKED"
            tvBroadcastStatus.setBackgroundColor(0xFFFEE2E2.toInt())
            tvBroadcastStatus.setTextColor(0xFFB91C1C.toInt())

            currentAudioPath = null
            btnPlayAudio.isEnabled = false
        }

        updateDiagnostics(response)
    }

    private fun updateDiagnostics(response: PedagogySessionResponse) {
        val speech = response.speechResult
        val durationStr = if (speech != null) "${String.format("%.2f", speech.durationSec)}s" else "1.00s"
        val rmsStr = if (speech != null) String.format("%.1f", speech.rmsEnergy) else "—"
        tvDiagAudioStats?.text = "Audio: Duration $durationStr | RMS: $rmsStr"

        val clsStr = speech?.classIndex?.toString() ?: "0"
        val recText = speech?.recognizedText ?: "None"
        val confStr = if (speech != null) String.format("%.1f%%", speech.confidence * 100) else "—"
        val secConfStr = if (speech != null) String.format("%.1f%%", speech.secondBestConfidence * 100) else "—"
        val marginStr = if (speech != null) String.format("%.1f%%", speech.margin * 100) else "—"
        tvDiagClassAndConf?.text = "Classifier: Class $clsStr ($recText) | Conf: $confStr | 2nd: $secConfStr | Margin: $marginStr"

        val decision = speech?.decision ?: if (response.isSuccess) "ACCEPTED" else "REJECTED"
        tvDiagDecision?.text = "Decision: $decision | Translation: ${response.translationStatus}"

        tvDiagProvenance?.text = "Audio Provenance: ${response.audioStatus}"

        val ts = response.pipelineTimestamps
        if (ts != null) {
            tvDiagTimestamps?.text = "Timestamps: Capture ${ts.captureDurationMs.toInt()}ms | Infer ${ts.inferenceLatencyMs.toInt()}ms | Trans ${ts.translationLatencyMs.toInt()}ms | Total ${ts.totalProcessingLatencyMs.toInt()}ms"
        } else {
            tvDiagTimestamps?.text = "Timestamps (T0-T4): Pending capture run"
        }
        tvDiagHardwareNotice?.text = "Hardware Latency: ${response.hardwareProfileStatus}"
    }

    private fun buildFallbackGrid() {
        gridDirectSelection.removeAllViews()
        for (num in 1..20) {
            val btn = Button(this).apply {
                text = "$num"
                textSize = 14f
                setOnClickListener {
                    val response = coordinator.processDirectCardSelection(num)
                    displayResult(response)
                }
            }
            val params = GridLayout.LayoutParams().apply {
                width = 0
                height = GridLayout.LayoutParams.WRAP_CONTENT
                columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
                setMargins(4, 4, 4, 4)
            }
            gridDirectSelection.addView(btn, params)
        }
    }

    private fun playCurrentAudio() {
        val path = currentAudioPath ?: return
        try {
            mediaPlayer?.release()
            mediaPlayer = MediaPlayer().apply {
                val afd = assets.openFd(path)
                setDataSource(afd.fileDescriptor, afd.startOffset, afd.length)
                afd.close()
                prepare()
                start()
            }
        } catch (e: Exception) {
            Toast.makeText(this, "Audio playback: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        audioCaptureService?.stopCapture()
        mediaPlayer?.release()
        mediaPlayer = null
    }
}
