package org.sih260042.pedagogy.service

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import org.sih260042.pedagogy.contract.AudioCaptureService
import org.sih260042.pedagogy.model.AudioBuffer
import org.sih260042.pedagogy.model.AudioInputConfig
import java.util.concurrent.atomic.AtomicBoolean

class AndroidAudioRecordService(
    val config: AudioInputConfig = AudioInputConfig()
) : AudioCaptureService {

    @Volatile
    private var audioRecord: AudioRecord? = null
    private val capturing = AtomicBoolean(false)
    private var captureThread: Thread? = null

    override val isCapturing: Boolean
        get() = capturing.get()

    @SuppressLint("MissingPermission")
    override fun startCapture(chunkCallback: (AudioBuffer) -> Unit) {
        if (capturing.get()) return

        val sampleRate = config.sampleRate
        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT

        val minBufSize = AudioRecord.getMinBufferSize(sampleRate, channelConfig, audioFormat)
        val bufferSize = maxOf(minBufSize, config.bufferSizeBytes * 2)

        val record = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            channelConfig,
            audioFormat,
            bufferSize
        )

        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw IllegalStateException("AudioRecord initialization failed (state != STATE_INITIALIZED)")
        }

        audioRecord = record
        capturing.set(true)
        record.startRecording()

        captureThread = Thread {
            val readBuffer = ShortArray(config.bufferSizeBytes / 2)
            try {
                while (capturing.get()) {
                    val readCount = record.read(readBuffer, 0, readBuffer.size)
                    if (readCount > 0) {
                        val pcm = ShortArray(readCount)
                        System.arraycopy(readBuffer, 0, pcm, 0, readCount)
                        val buf = AudioBuffer(
                            pcmData = pcm,
                            sampleRate = sampleRate,
                            channelCount = 1
                        )
                        chunkCallback(buf)
                    }
                }
            } catch (_: Exception) {
            } finally {
                safeStopAndRelease(record)
            }
        }.apply {
            name = "AudioCaptureThread"
            isDaemon = true
            start()
        }
    }

    override fun stopCapture() {
        capturing.set(false)
        captureThread?.interrupt()
        captureThread = null
        audioRecord?.let { safeStopAndRelease(it) }
        audioRecord = null
    }

    @SuppressLint("MissingPermission")
    fun captureOneSecond(): AudioBuffer {
        val sampleRate = config.sampleRate
        val totalSamples = config.targetSamples
        val pcm = ShortArray(totalSamples)

        val minBuf = AudioRecord.getMinBufferSize(sampleRate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val bufSize = maxOf(minBuf, 32000)

        val record = AudioRecord(
            MediaRecorder.AudioSource.MIC,
            sampleRate,
            AudioFormat.CHANNEL_IN_MONO,
            AudioFormat.ENCODING_PCM_16BIT,
            bufSize
        )

        if (record.state != AudioRecord.STATE_INITIALIZED) {
            record.release()
            throw IllegalStateException("Failed to initialize AudioRecord for 1.0s capture")
        }

        try {
            record.startRecording()
            var samplesRead = 0
            val chunk = ShortArray(1600)
            while (samplesRead < totalSamples) {
                val toRead = minOf(chunk.size, totalSamples - samplesRead)
                val read = record.read(chunk, 0, toRead)
                if (read > 0) {
                    System.arraycopy(chunk, 0, pcm, samplesRead, read)
                    samplesRead += read
                } else if (read < 0) {
                    break
                }
            }
        } finally {
            safeStopAndRelease(record)
        }

        return AudioBuffer(
            pcmData = pcm,
            sampleRate = sampleRate,
            channelCount = 1
        )
    }

    private fun safeStopAndRelease(record: AudioRecord) {
        try {
            if (record.recordingState == AudioRecord.RECORDSTATE_RECORDING) {
                record.stop()
            }
        } catch (_: Exception) {}
        try {
            record.release()
        } catch (_: Exception) {}
    }
}
