import subprocess
import json
import os

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

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

report = {}

for role, page, label in views:
    url = f"http://localhost:8080/?role={role}&page={page}"
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--dump-dom",
        url
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=15)
    html = res.stdout.decode('utf-8', errors='replace')
    
    # Extract element summary
    from html.parser import HTMLParser
    class TagCounter(HTMLParser):
        def __init__(self):
            super().__init__()
            self.tags = {}
            self.classes = set()
            self.ids = set()
        def handle_starttag(self, tag, attrs):
            self.tags[tag] = self.tags.get(tag, 0) + 1
            for k, v in attrs:
                if k == 'class' and v:
                    for c in v.split():
                        self.classes.add(c)
                if k == 'id' and v:
                    self.ids.add(v)

    parser = TagCounter()
    parser.feed(html)
    
    # Find main content container
    c_start = html.find('id="content"')
    content_snippet = ""
    if c_start != -1:
        snippet = html[c_start:c_start+500]
        content_snippet = snippet.replace('\n', ' ')[:200]

    report[label] = {
        "url": url,
        "total_tags": sum(parser.tags.values()),
        "top_tags": sorted(parser.tags.items(), key=lambda x: x[1], reverse=True)[:8],
        "key_ids": [i for i in parser.ids if any(k in i.lower() for k in ['content', 'mic', 'feed', 'room', 'flash', 'quiz', 'preview', 'table', 'ws'])][:10],
        "key_classes": [c for c in parser.classes if any(k in c.lower() for k in ['theme', 'hero', 'card', 'num', 'flash', 'quiz', 'voice', 'action'])][:12],
        "content_start": content_snippet
    }

print(json.dumps(report, indent=2))
with open(r"C:\Users\chatu\.gemini\antigravity\brain\3dad20cc-c409-4fae-8a64-662cf41ef492\dom_analysis.json", "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2)
print("DOM analysis saved to dom_analysis.json")
