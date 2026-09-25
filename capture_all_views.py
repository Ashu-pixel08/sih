import os
import subprocess
import time

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT_DIR = r"C:\Users\chatu\.gemini\antigravity\brain\3dad20cc-c409-4fae-8a64-662cf41ef492\view_inspections"
os.makedirs(OUT_DIR, exist_ok=True)

views = [
    ("student", "home", "1_student_home"),
    ("student", "modules", "2_student_numbers"),
    ("student", "flashcards", "3_student_flashcards"),
    ("student", "practice", "4_student_quiz"),
    ("student", "settings", "5_student_settings"),
    ("teacher", "dashboard", "6_teacher_dashboard"),
    ("teacher", "live", "7_teacher_voice_mode"),
    ("teacher", "curriculum", "8_teacher_curriculum"),
    ("teacher", "modules", "9_teacher_modules"),
    ("teacher", "worksheet", "10_teacher_worksheets"),
    ("teacher", "progress", "11_teacher_progress"),
    ("teacher", "settings", "12_teacher_settings"),
]

print("Capturing 12 views...")
for role, page, label in views:
    url = f"http://localhost:8080/?role={role}&page={page}"
    png_path = os.path.join(OUT_DIR, f"{label}.png")
    
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--window-size=1280,820",
        f"--screenshot={png_path}",
        url
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=15)
    print(f"[{label}] -> {os.path.exists(png_path)} ({os.path.getsize(png_path) if os.path.exists(png_path) else 0} bytes)")

print("All captures completed.")
