# SIH260042: Acoustic Recording Specification
**Project**: AI-Powered Vernacular Pedagogy and Real-Time Translation Tool for Mother Tongue-Based Primary Education  
**Target Language**: Mundari (`unr`)  
**Domain**: Foundational Literacy and Numeracy (FLN) Grade 1 Speech Processing  
**Document Version**: 1.0.0  
**Status**: ACTIVE PROTOCOL SPECIFICATION  

---

## 1. Technical Audio Format Requirements

Every raw audio recording collected in the field must strictly satisfy the following uncompressed audio container and encoding specifications. Compressed formats (MP3, AAC, OGG, Opus) or lossy transcoding are strictly prohibited.

| Parameter | Mandatory Value | Verification Rule |
| :--- | :--- | :--- |
| **Container Format** | WAV (RIFF header) | Header magic bytes `RIFF` and `WAVE` |
| **Audio Encoding** | Linear PCM (`WAVE_FORMAT_PCM`, tag `0x0001`) | Uncompressed signed integer linear PCM |
| **Sampling Rate** | Exactly **16,000 Hz** (16.0 kHz) | Header `nSamplesPerSec == 16000` |
| **Bit Depth** | Exactly **16-bit** signed integer | Header `wBitsPerSample == 16` |
| **Channel Count** | Exactly **1 channel (Mono)** | Header `nChannels == 1` |
| **Byte Order** | Little-Endian (Standard RIFF) | Standard x86/ARM little-endian PCM |
| **Data Alignment** | 2 bytes per sample (Block align = 2) | Header `nBlockAlign == 2` |

> [!IMPORTANT]
> **No Post-Hoc Upsampling**: Audio recorded at 8 kHz, 11.025 kHz, or through telephony narrow-band codecs must NOT be upsampled to 16 kHz. Audio recorded at higher rates (e.g. 44.1 kHz or 48 kHz on studio equipment) must be downsampled to 16 kHz using high-order polyphase Kaiser-window FIR filtering (zero phase distortion) as specified in `audio_preprocessing_spec.json`.

---

## 2. Quantitative Signal-Level Acceptance Thresholds

Every recorded file must undergo automated DSP parameter validation before human linguistic inspection.

```
                  ┌──────────── Target Utterance ────────────┐
[Silence] ─────── │ [Onset] ──── Word Core ──── [Offset]     │ ─────── [Silence]
 100-250 ms       └──────────────────────────────────────────┘        100-300 ms
                  │◄────────────── 400 - 2500 ms ───────────►│
```

| Signal Metric | Minimum Limit | Nominal Target | Maximum Limit | Rejection Condition |
| :--- | :---: | :---: | :---: | :--- |
| **RMS Energy** | $-28.0$ dBFS | $-22.0$ dBFS | $-16.0$ dBFS | RMS $< -30.0$ dBFS (whisper/too far) or $> -14.0$ dBFS (mic overload) |
| **Peak Amplitude** | $-20.0$ dBFS | $-6.0$ dBFS | **$-1.0$ dBFS** | Peak $\ge -0.5$ dBFS or $> 0$ consecutive samples at max integer range ($\pm 32767$) |
| **Signal-to-Noise Ratio (SNR)** | **$\ge 22.0$ dB** | $\ge 28.0$ dB | $\infty$ | Estimated SNR $< 20.0$ dB (unacceptable background noise) |
| **Lead-In Silence** | $100$ ms | $150$ ms | $300$ ms | Lead-in $< 50$ ms (word onset clipped) or $> 500$ ms (excessive latency) |
| **Lead-Out Silence** | $100$ ms | $200$ ms | $400$ ms | Lead-out $< 50$ ms (word ending clipped) or $> 600$ ms |
| **Total Speech Duration** | $400$ ms | $900$ ms | $2500$ ms | Single word $< 300$ ms (unnatural rush) or $> 3000$ ms |
| **DC Offset** | $-0.005$ | $0.000$ | $+0.005$ | Mean sample value $> 0.01$ (microphone bias hardware flaw) |

---

## 3. Physical Recording Environment & Hardware Standards

### 3.1 Hardware Configuration
1. **Microphone Type**: Directional cardioid condenser or high-grade USB lavalier microphone with integrated 16-bit/24-bit ADC.
2. **Pop Filter / Windshield**: High-density foam pop filter must be mounted on the microphone to eliminate explosive plosive bursts ($p, b, t, d$ sounds common in Mundari prefixes and roots).
3. **Consistent Distance**: Fixed distance of **15 cm to 20 cm** between the speaker's mouth and the microphone capsule. The microphone should be positioned at a $30^\circ$ off-axis angle from the direct breath stream.
4. **Gain Setting**: Fixed hardware gain set during acoustic calibration so that a loud test vocalization does not exceed $-3.0$ dBFS peak. Hardware AGC (Automatic Gain Control) must be **strictly disabled** to prevent dynamic pumping of room noise floors.

### 3.2 Controlled Recording Environment
- **Ambient Noise Floor**: Quiet enclosed room with background ambient level $\le -45.0$ dBFS (measured prior to recording session).
- **Acoustic Isolation**: Windows and doors closed; ceiling fans, air coolers, and external machinery turned OFF during recording takes.
- **Reverberation Control**: Recording space should have soft furnishings, curtains, or foam baffles to ensure reverberation time $T_{60} < 0.25$s. Avoid bare tiled or concrete empty rooms.

---

## 4. Class 0 / Background Acoustic Capture Protocol

To properly train and evaluate Class 0 (`_background_`), field teams must also collect authentic environmental acoustic recordings:
1. **Quiet Classroom Silence**: 60 seconds of natural ambient room room-tone (fans off, no voices).
2. **Classroom Mechanical Ambience**: 60 seconds of ceiling fan hum, window wind, and room vibration.
3. **Classroom Activity Sounds**: 60 seconds of desk tapping, slate writing, paper rustling, and footsteps (isolated from vocalizations).
4. **Distant Non-Target Babble**: 60 seconds of distant murmurs (outside classroom, low energy $< -35$ dBFS).
5. **Non-Target Vocalizations**: Coughs, throat clears, sighs, and laughter from native speakers.

Every environmental segment must be stored in `data/raw/background/` and segmented into standard 1.0-second windows without synthetic noise generation.
