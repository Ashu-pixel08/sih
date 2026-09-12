import os
import json
import hashlib
import pytest

workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

canon_reg_path = os.path.join(workspace_root, "content", "content_registry.json")
android_reg_path = os.path.join(workspace_root, "android", "app", "src", "main", "assets", "content", "content_registry.json")

canon_pb_path = os.path.join(workspace_root, "content", "translations", "classroom_phrasebook.json")
android_pb_path = os.path.join(workspace_root, "android", "app", "src", "main", "assets", "content", "classroom_phrasebook.json")

frontend_html_path = os.path.join(workspace_root, "frontend", "index.html")
android_assets_dir = os.path.join(workspace_root, "android", "app", "src", "main", "assets")

def sha256_file(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def extract_web_db():
    with open(frontend_html_path, encoding="utf-8") as f:
        html = f.read()
    start = html.find("const DB = {")
    assert start != -1, "const DB not found in frontend/index.html"
    end = html.find("};\n", start)
    assert end != -1, "end of const DB not found in frontend/index.html"
    return json.loads(html[start + len("const DB = "):end + 1])

class TestCrossPlatformCanonicalParity:

    def test_registry_file_byte_for_byte_identity(self):
        """Verify content_registry.json and its Android copy are byte-for-byte identical."""
        assert os.path.exists(canon_reg_path), "Canonical content_registry.json missing"
        assert os.path.exists(android_reg_path), "Android content_registry.json missing"
        h1 = sha256_file(canon_reg_path)
        h2 = sha256_file(android_reg_path)
        assert h1 == h2, f"Registry hash mismatch: {h1} != {h2}"

    def test_phrasebook_file_byte_for_byte_identity(self):
        """Verify classroom_phrasebook.json and its Android copy are byte-for-byte identical."""
        assert os.path.exists(canon_pb_path), "Canonical classroom_phrasebook.json missing"
        assert os.path.exists(android_pb_path), "Android classroom_phrasebook.json missing"
        h1 = sha256_file(canon_pb_path)
        h2 = sha256_file(android_pb_path)
        assert h1 == h2, f"Phrasebook hash mismatch: {h1} != {h2}"

    def test_web_vs_canonical_numbers_parity(self):
        """Verify Web DB numbers match canonical content_registry.json across all fields."""
        with open(canon_reg_path, encoding="utf-8") as f:
            canon = json.load(f)
        web_db = extract_web_db()

        canon_items = canon["items"]
        web_items = web_db["numbers"]

        assert len(canon_items) == 20, f"Expected 20 canonical numerals, got {len(canon_items)}"
        assert len(web_items) == 20, f"Expected 20 web numerals, got {len(web_items)}"

        for i in range(20):
            c = canon_items[i]
            w = web_items[i]
            num = c["number"]
            assert w["number"] == num, f"Number mismatch at index {i}"
            assert c["class_index"] == num, f"Off-by-one in class_index for number {num}: got {c['class_index']}"
            assert w["hindi_text"] == c["hindi_text"], f"Hindi text mismatch on #{num}"
            assert w["mundari_text"] == c["mundari_text"], f"Mundari text mismatch on #{num}"
            assert w["mundari_root"] == c["mundari_root"], f"Mundari root mismatch on #{num}"
            assert w["mundari_phonetic"] == c["mundari_phonetic"], f"Phonetic mismatch on #{num}"
            assert w["hindi_numeral"] == c["hindi_numeral"], f"Hindi numeral mismatch on #{num}"
            assert w["mundari_numeral"] == c["mundari_numeral"], f"Mundari numeral mismatch on #{num}"
            assert w.get("linguistic_status") == c["linguistic_status"], f"Status mismatch on #{num}"

    def test_web_vs_canonical_phrasebook_parity(self):
        """Verify Web DB phrasebook matches canonical classroom_phrasebook.json."""
        with open(canon_pb_path, encoding="utf-8") as f:
            canon_pb = json.load(f)
        web_db = extract_web_db()

        canon_phrases = {p["phrase_id"]: p for p in canon_pb["phrases"]}
        web_phrases = {p["phrase_id"]: p for p in web_db.get("phrasebook", [])}

        assert len(canon_phrases) == 16, f"Expected 16 canonical phrases, got {len(canon_phrases)}"
        assert len(web_phrases) == 16, f"Expected 16 web phrases, got {len(web_phrases)}"

        for pid, c in canon_phrases.items():
            assert pid in web_phrases, f"Phrase {pid} missing from web DB"
            w = web_phrases[pid]
            assert w["hindi_text"] == c["hindi_text"], f"Hindi text mismatch on {pid}"
            assert w["mundari_text"] == c["mundari_text"], f"Mundari text mismatch on {pid}"
            assert w["mundari_phonetic"] == c["mundari_phonetic"], f"Phonetic mismatch on {pid}"
            assert w["category"] == c["category"], f"Category mismatch on {pid}"
            assert w.get("verification_level") == c["verification_level"], f"Verification level mismatch on {pid}"

    def test_class_index_safety_contract(self):
        """Verify class 0 is strictly background/silence and classes 1-20 map 1:1 without off-by-one."""
        with open(canon_reg_path, encoding="utf-8") as f:
            canon = json.load(f)

        bg = canon["background_class"]
        assert bg["class_index"] == 0, f"Background class must have class_index 0, got {bg['class_index']}"
        assert bg["label_id"] == "_background_", f"Background label_id must be '_background_', got {bg['label_id']}"

        for idx, item in enumerate(canon["items"], start=1):
            assert item["class_index"] == idx, f"Class index mismatch: expected {idx}, got {item['class_index']}"
            assert item["number"] == idx, f"Number mismatch: expected {idx}, got {item['number']}"

    def test_android_audio_assets_parity(self):
        """Verify all 20 canonical number WAVs and 16 phrase WAVs physically exist in Android assets."""
        with open(canon_reg_path, encoding="utf-8") as f:
            canon_reg = json.load(f)
        with open(canon_pb_path, encoding="utf-8") as f:
            canon_pb = json.load(f)

        for item in canon_reg["items"]:
            num = item["number"]
            rel_wav = os.path.join(android_assets_dir, "audio", "prototype_tts", "numbers", f"num_{num:02d}.wav")
            assert os.path.exists(rel_wav), f"Android asset missing: {rel_wav}"
            assert os.path.getsize(rel_wav) > 0, f"Android asset empty: {rel_wav}"

        for p in canon_pb["phrases"]:
            pid = p["phrase_id"]
            rel_wav = os.path.join(android_assets_dir, "audio", "prototype_tts", "phrases", f"{pid}.wav")
            assert os.path.exists(rel_wav), f"Android asset missing: {rel_wav}"
            assert os.path.getsize(rel_wav) > 0, f"Android asset empty: {rel_wav}"
