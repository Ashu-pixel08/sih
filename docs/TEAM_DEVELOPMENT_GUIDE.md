# Team Development & Collaboration Guide

Welcome to the **Bhasha Setu** project repository (`https://github.com/Ashu-pixel08/sih`). This document serves as the primary onboarding manual and operational standard for all engineers, researchers, and contributors working across the Frontend, Backend, AI/ML, Android, and Educational Curriculum layers.

---

## 1. Prerequisites & Toolchain Requirements

Ensure your development machine has the following tools installed:

| Tool | Recommended Version | Purpose |
|---|---|---|
| **Git** | 2.40+ | Version control |
| **Git LFS** | 3.2+ | Large file storage for neural model checkpoints (`*.pt`) |
| **Python** | 3.10, 3.11, or 3.12 | Backend API server, NMT training, data pipelines, test runner |
| **JDK** | OpenJDK 17 LTS | Android build system & Gradle daemon |
| **Android SDK** | API Level 34 (UpsideDownCake) | Native Android application compilation |
| **Node.js** | 18+ (LTS) | Optional: Browser headless testing & CDP automation |

---

## 2. Step-by-Step Developer Onboarding

### Step 2.1: Clone Repository & Initialize Git LFS
Large model binaries (including the 110 MB production PyTorch checkpoint `models/nmt/final/best_transformer.pt`) are tracked via **Git LFS**. You must initialize LFS before or immediately after cloning:

```bash
# 1. Install Git LFS hooks on your machine (one-time global setup)
git lfs install

# 2. Clone the repository
git clone https://github.com/Ashu-pixel08/sih.git
cd sih

# 3. Pull all Git LFS binary pointer objects
git lfs pull
```

> [!IMPORTANT]
> If you omit `git lfs pull`, `.pt` model files will only exist as tiny text pointer files (~130 bytes) and PyTorch will raise `_pickle.UnpicklingError` when loading checkpoints.

---

### Step 2.2: Setup Python Virtual Environment

Always use an isolated virtual environment to prevent dependency conflicts.

#### On Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### On Windows (Command Prompt):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

#### On macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 2.3: Install Python Dependencies

Install all core libraries required for the local server, translation engine, and test suite:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verify your environment:
```bash
python -c "import torch, sentencepiece, tokenizers, sklearn; print('All core AI/ML dependencies loaded successfully!')"
```

---

## 3. Running the Application Locally

### Starting the Local Development Server
The application features a zero-external-dependency local HTTP and REST API server:

```bash
python server.py 8080
```

Once running, navigate to:
* **Teacher Command Center & Full App**: `http://localhost:8080/`
  * **Teacher Login**: Enter password `1234`.
  * **Student Login**: Enter student name (e.g. `Birsa Munda`) and roll number (e.g. `12`).
* **Direct Evaluator / Demo Mode**: `http://localhost:8080/?demo=1`
  * Bypasses auth gate with pre-seeded presets, live room simulation, and immediate access to all modules.

### Testing Key Modules
1. **Overview Page**: Quick KPI cards, system status, quick action buttons, and FLN module launcher.
2. **Voice Mode & Continuous Voice Orb**:
   * Click the glowing circular Voice Orb to cycle through listening states.
   * Test simulated speech recognition and real-time barge-in interruption.
3. **Educational Modules & Flashcards**:
   * Inspect 10 FLN categories (Animals, Birds, Body Parts, Colors, Family, Flowers, Food, Insects, Vegetables, Vehicles).
   * Interactive ten-frames, image previews, and pronunciation buttons.
4. **Worksheet Generator**:
   * Dynamic worksheets (`recognition`, `counting`, `matching`, `sequencing`, `missing_numbers`) with printable A4 preview.
5. **Practice Arena**:
   * Bilingual interactive quiz engine with instant score tallying.

---

## 4. Running the Automated Test Suite

Every commit and pull request must pass the complete project test suite (**245 automated tests**).

### Run the Full Test Suite:
```bash
pytest tests/ -v
```

### Run Focused Test Suites:
```bash
# UI & Backend REST API integration
pytest tests/test_ui_backend_integration.py -v

# Continuous Voice Orb state machine & audio contracts
pytest tests/test_continuous_voice_orb.py -v

# Educational content layer & dynamic catalog routing
pytest tests/test_educational_content_layer.py -v

# Neural Seq2Seq NMT model inference & beam search
pytest tests/test_neural_translation.py -v

# Cross-platform contract parity (Web <-> Android)
pytest tests/test_cross_platform_parity.py -v

# End-to-end browser prototype flows
pytest tests/test_phase_8_browser_prototype.py -v
```

---

## 5. Building and Running the Android Application

The repository includes a complete native Android application in `android/`.

### Prerequisites:
* Android Studio Iguana / Jellyfish or standalone Android SDK 34
* JDK 17 configured as `JAVA_HOME`

### Compiling and Running Unit Tests:
```bash
cd android

# Linux / macOS
./gradlew testDebugUnitTest

# Windows
gradlew.bat testDebugUnitTest
```

### Assembling Debug APK:
```bash
# Linux / macOS
./gradlew assembleDebug

# Windows
gradlew.bat assembleDebug
```
The output APK is generated at:
`android/app/build/outputs/apk/debug/app-debug.apk`

### Installing to Connected Device / Emulator:
```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## 6. Collaborative Git Workflow

To maintain clean project history and avoid conflicting code, adhere strictly to this workflow:

### Step 6.1: Branch Naming Conventions
Never commit directly to `main`. Create descriptive feature branches:
* `feature/<feature-name>` (e.g., `feature/voice-synthesis`, `feature/offline-sync`)
* `fix/<bug-name>` (e.g., `fix/flashcard-image-render`, `fix/orb-barge-in`)
* `data/<dataset-update>` (e.g., `data/add-vegetables-vocab`)
* `docs/<topic>` (e.g., `docs/api-contracts`)

### Step 6.2: Daily Development Loop
```bash
# 1. Fetch latest changes from origin
git checkout main
git pull --rebase origin main

# 2. Branch off latest main
git checkout -b feature/your-feature-name

# 3. Implement your changes and verify tests pass
pytest tests/

# 4. Stage your changes (do NOT add untracked cache or build dirs)
git add <files>

# 5. Commit with atomic, clear messages
git commit -m "feat(ui): add interactive audio feedback to practice quiz"
```

### Step 6.3: Keeping Branch Updated (Rebase Workflow)
Before opening a PR or pushing, always rebase against `origin/main`:
```bash
git fetch origin
git rebase origin/main
```
If merge conflicts occur:
1. Open conflicting files and resolve markers (`<<<<<<<`, `=======`, `>>>>>>>`).
2. Run `git add <resolved-file>`.
3. Run `git rebase --continue`.
4. Run `pytest tests/` to ensure no regression was introduced.

### Step 6.4: Pushing and Opening a Pull Request
```bash
git push -u origin feature/your-feature-name
```
Open a Pull Request on GitHub targeting `main`:
* Describe what was added or changed.
* Mention the automated tests that were run.
* Attach screenshots for UI modifications.

---

## 7. Strict Coding & Repository Rules

> [!CAUTION]
> **Violations of the following rules will cause automated CI / PR rejection:**

1. **Zero Personal Machine Paths**:
   Never hardcode paths like `C:\Users\username\...` or `/home/username/...`. Always resolve paths dynamically relative to the repository root:
   ```python
   # Correct:
   BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
   data_path = os.path.join(BASE_DIR, "data", "custom", "cleaned_team_pairs.jsonl")
   ```

2. **Zero Hardcoded Secrets & Tokens**:
   Never commit `.env` files, API keys, private certificates, or user credentials.

3. **No Large Binaries Outside Git LFS**:
   Any binary model file (`*.pt`, `*.onnx`) must be tracked by Git LFS. Never commit uncompressed archives (`.zip`, `.tgz`, `.tar.gz`) directly to Git history.

4. **Never Commit Build Artifacts**:
   Keep `.gitignore` respected at all times. Never commit `.venv/`, `android/build/`, `android/.gradle/`, `__pycache__/`, or `*.apk` files.

5. **Cross-Platform Contract Parity**:
   If you update `content/content_registry.json`, you must synchronize the identical JSON file into `android/app/src/main/assets/content_registry.json`. Both platforms must share the identical ground-truth registry.

6. **All 245 Tests Must Pass**:
   Never push code that breaks existing unit or integration tests. Run `pytest tests/` prior to every push.
