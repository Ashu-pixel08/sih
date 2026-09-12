package org.sih260042.pedagogy

import org.sih260042.pedagogy.dsp.AudioPreprocessor
import org.sih260042.pedagogy.dsp.PreprocessingConfig
import kotlin.math.abs

class AudioPreprocessorTest {

    fun testHannWindowSpecification() {
        val config = PreprocessingConfig()
        val preprocessor = AudioPreprocessor(config)
        
        // Window length must be 400 (25ms at 16kHz)
        assert(config.winLength == 400) { "Hann window length must be 400" }
        assert(config.numFrames == 101) { "Spectrogram frames must be 101" }
        assert(config.nMels == 64) { "Mel filterbank bins must be 64" }
    }

    fun testSpectrogramOutputShapeAndBuffer() {
        val config = PreprocessingConfig()
        val preprocessor = AudioPreprocessor(config)

        // Generate 1.0 second of synthetic 440 Hz sine wave
        val sampleRate = 16000
        val audio = FloatArray(sampleRate)
        for (i in audio.indices) {
            audio[i] = (kotlin.math.sin(2.0 * Math.PI * 440.0 * i / sampleRate)).toFloat() * 0.8f
        }

        val spec = preprocessor.extractLogMelSpectrogram(audio)
        assert(spec.size == 101) { "Spectrogram must have 101 frames, got ${spec.size}" }
        assert(spec[0].size == 64) { "Spectrogram must have 64 Mel bins, got ${spec[0].size}" }

        // Test ByteBuffer formatting for TFLite
        val buffer = preprocessor.toTFLiteInputBuffer(spec)
        val expectedBytes = 101 * 64 * 4 // 25,856 bytes
        assert(buffer.capacity() == expectedBytes) { "Input buffer must have $expectedBytes bytes, got ${buffer.capacity()}" }
        assert(buffer.position() == 0) { "Buffer should be rewound to position 0" }
    }

    fun testEmptyOrSilenceSpectrogram() {
        val preprocessor = AudioPreprocessor()
        val silentAudio = FloatArray(16000) // All zeros
        val spec = preprocessor.extractLogMelSpectrogram(silentAudio)
        
        assert(spec.size == 101)
        assert(spec[0].size == 64)
        // With log offset 1e-6, log(1e-6) ~= -13.8155
        val expectedLogVal = kotlin.math.ln(1e-6f)
        val diff = abs(spec[0][0] - expectedLogVal)
        assert(diff < 0.01f) { "Silence spectrogram value drift: $diff" }
    }
}
