"""
Bilingual Worksheet Generator for FLN Grade 1 Numeracy.

Generates reproducible, offline-compatible bilingual worksheets:
1. Number Recognition (संख्या पहचान / लेका उरुम)
2. Object Counting (गिनती / लेका)
3. Matching Quantity to Numeral (मात्रा मिलान / जोड़ाव)
4. Simple Sequencing (क्रमबद्धता / सिरिस)
5. Missing Numbers (लुप्त संख्या / अदआकान लेका)

Dual Output:
- Structured JSON for interactive Android app rendering
- Standalone printable HTML/CSS for offline physical classroom printing
"""

import os
import json
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class WorksheetProblem:
    problem_id: str
    problem_type: str
    instruction_hi: str
    instruction_unr: str
    prompt_data: Dict[str, Any]
    options: Optional[List[Dict[str, Any]]] = None
    solution: Any = None


@dataclass
class WorksheetDocument:
    worksheet_id: str
    title_hi: str
    title_unr: str
    grade: int
    subject: str
    fln_domain: str
    topic: str
    target_competency: str
    generation_seed: int
    provenance_status: str
    problems: List[Dict[str, Any]]


class WorksheetGenerator:
    """Generates deterministic, pedagogically structured worksheets."""

    def __init__(self, registry_path: Optional[str] = None, seed: int = 42):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.registry_path = registry_path or os.path.join(base_dir, "content", "content_registry.json")
        self.output_dir = os.path.join(base_dir, "content", "worksheets", "generated")
        os.makedirs(self.output_dir, exist_ok=True)
        self.seed = seed

        with open(self.registry_path, "r", encoding="utf-8") as f:
            self.registry = json.load(f)

        self.items = {item["number"]: item for item in self.registry.get("items", [])}

    def generate_number_recognition_worksheet(self, seed: Optional[int] = None) -> WorksheetDocument:
        """Type 1: Identify and circle correct numeral for Mundari + Hindi word."""
        rng = random.Random(seed or self.seed)
        sample_nums = [1, 3, 5, 8, 10, 12, 14, 17, 20]
        problems = []

        for idx, num in enumerate(sample_nums, 1):
            item = self.items[num]
            # Generate 3 distractors
            distractors = rng.sample([n for n in range(1, 21) if n != num], 3)
            choices = sorted([num] + distractors)

            options = [
                {
                    "number": c,
                    "numeral": self.items[c]["hindi_numeral"],
                    "is_correct": (c == num),
                }
                for c in choices
            ]

            prob = WorksheetProblem(
                problem_id=f"recog_{idx:02d}",
                problem_type="number_recognition",
                instruction_hi="सही संख्या पर गोला लगाएँ:",
                instruction_unr="सोझोः लेका रे गोल चिन्हाः बाइपे:",
                prompt_data={
                    "target_number": num,
                    "mundari_word": item["mundari_text"],
                    "mundari_phonetic": item["mundari_phonetic"],
                    "hindi_word": item["hindi_text"],
                    "hindi_numeral": item["hindi_numeral"],
                },
                options=options,
                solution=num,
            )
            problems.append(asdict(prob))

        return WorksheetDocument(
            worksheet_id="WS_01_NUMBER_RECOGNITION",
            title_hi="कार्यपत्रक १: संख्या पहचान (Numbers 1-20)",
            title_unr="कामि साकाम १: लेका उरुम (Numbers 1-20)",
            grade=1,
            subject="Mathematics",
            fln_domain="Foundational Numeracy",
            topic="Numbers 1-20",
            target_competency="M1.1 (UNVERIFIED — PENDING SOURCE VALIDATION)",
            generation_seed=seed or self.seed,
            provenance_status="GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
            problems=problems,
        )

    def generate_counting_worksheet(self, seed: Optional[int] = None) -> WorksheetDocument:
        """Type 2: Count objects in ten-frame arrays and write numeral + Mundari word."""
        rng = random.Random(seed or self.seed + 1)
        sample_nums = [2, 4, 6, 7, 9, 11, 13, 15]
        problems = []

        for idx, num in enumerate(sample_nums, 1):
            item = self.items[num]
            prob = WorksheetProblem(
                problem_id=f"count_{idx:02d}",
                problem_type="counting",
                instruction_hi="गोलों को गिनें और खाली डिब्बे में संख्या लिखें:",
                instruction_unr="चिनहाः को लेकापे आर खाली बक्सा रे लेका ओलपे:",
                prompt_data={
                    "count": num,
                    "tens": num // 10,
                    "ones": num % 10,
                    "expected_mundari_word": item["mundari_text"],
                    "expected_hindi_word": item["hindi_text"],
                },
                solution={"number": num, "mundari": item["mundari_text"], "hindi": item["hindi_text"]},
            )
            problems.append(asdict(prob))

        return WorksheetDocument(
            worksheet_id="WS_02_COUNTING",
            title_hi="कार्यपत्रक २: वस्तु गणना और मातृभाषा लेखन",
            title_unr="कामि साकाम २: लेका आर ओल",
            grade=1,
            subject="Mathematics",
            fln_domain="Foundational Numeracy",
            topic="Numbers 1-20",
            target_competency="M1.2 (UNVERIFIED — PENDING SOURCE VALIDATION)",
            generation_seed=seed or self.seed + 1,
            provenance_status="GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
            problems=problems,
        )

    def generate_matching_worksheet(self, seed: Optional[int] = None) -> WorksheetDocument:
        """Type 3: Match visual quantities on left to numerals/names on right."""
        rng = random.Random(seed or self.seed + 2)
        group = [3, 5, 8, 10, 14, 18]
        shuffled_targets = list(group)
        rng.shuffle(shuffled_targets)

        problems = []
        for idx, num in enumerate(group, 1):
            item = self.items[num]
            prob = WorksheetProblem(
                problem_id=f"match_{idx:02d}",
                problem_type="matching_quantity_to_numeral",
                instruction_hi="मात्रा को सही संख्या और मुंडारी नाम से मिलाएँ:",
                instruction_unr="लेका के सोझोः चिन्हाः आर मुंडारी नुतुम ते जोड़ावपे:",
                prompt_data={
                    "left_index": idx,
                    "quantity": num,
                    "right_target_number": shuffled_targets[idx - 1],
                    "right_mundari_word": self.items[shuffled_targets[idx - 1]]["mundari_text"],
                    "right_hindi_numeral": self.items[shuffled_targets[idx - 1]]["hindi_numeral"],
                },
                solution={"left_quantity": num, "matches_number": num},
            )
            problems.append(asdict(prob))

        return WorksheetDocument(
            worksheet_id="WS_03_MATCHING",
            title_hi="कार्यपत्रक ३: मात्रा एवं संख्या मिलान",
            title_unr="कामि साकाम ३: जोड़ाव लेका",
            grade=1,
            subject="Mathematics",
            fln_domain="Foundational Numeracy",
            topic="Numbers 1-20",
            target_competency="M1.1 (UNVERIFIED — PENDING SOURCE VALIDATION)",
            generation_seed=seed or self.seed + 2,
            provenance_status="GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
            problems=problems,
        )

    def generate_sequencing_worksheet(self, seed: Optional[int] = None) -> WorksheetDocument:
        """Type 4: Arrange scrambled numbers in sequential order."""
        rng = random.Random(seed or self.seed + 3)
        sequences = [
            list(range(1, 6)),
            list(range(6, 11)),
            list(range(11, 16)),
            list(range(16, 21)),
        ]
        problems = []

        for idx, seq in enumerate(sequences, 1):
            scrambled = list(seq)
            while scrambled == seq:
                rng.shuffle(scrambled)

            prob = WorksheetProblem(
                problem_id=f"seq_{idx:02d}",
                problem_type="simple_sequencing",
                instruction_hi="संख्याओं को छोटे से बड़े क्रम में लिखें:",
                instruction_unr="लेका को हुडिंग ते मारांग सिरिस रे ओलपे:",
                prompt_data={
                    "scrambled_numbers": scrambled,
                    "correct_sequence": seq,
                    "mundari_names": [self.items[n]["mundari_text"] for n in seq],
                },
                solution=seq,
            )
            problems.append(asdict(prob))

        return WorksheetDocument(
            worksheet_id="WS_04_SEQUENCING",
            title_hi="कार्यपत्रक ४: संख्या क्रमबद्धता (छोटा से बड़ा)",
            title_unr="कामि साकाम ४: लेका सिरिस",
            grade=1,
            subject="Mathematics",
            fln_domain="Foundational Numeracy",
            topic="Numbers 1-20",
            target_competency="M1.4 (UNVERIFIED — PENDING SOURCE VALIDATION)",
            generation_seed=seed or self.seed + 3,
            provenance_status="GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
            problems=problems,
        )

    def generate_missing_numbers_worksheet(self, seed: Optional[int] = None) -> WorksheetDocument:
        """Type 5: Complete number line with missing values."""
        rng = random.Random(seed or self.seed + 4)
        lines = [
            {"full": list(range(1, 11)), "missing_indices": [1, 4, 7]},  # 2, 5, 8 missing
            {"full": list(range(11, 21)), "missing_indices": [2, 5, 8]},  # 13, 16, 19 missing
        ]
        problems = []

        for idx, item in enumerate(lines, 1):
            display = [
                None if i in item["missing_indices"] else val
                for i, val in enumerate(item["full"])
            ]
            missing_vals = [item["full"][i] for i in item["missing_indices"]]

            prob = WorksheetProblem(
                problem_id=f"missing_{idx:02d}",
                problem_type="missing_numbers",
                instruction_hi="रेलगाड़ी के छूटे हुए डिब्बों में सही संख्या लिखें:",
                instruction_unr="गाड़ी राः अदआकान डिब्बा रे सोझोः लेका ओलपे:",
                prompt_data={
                    "sequence_with_gaps": display,
                    "missing_numbers": missing_vals,
                    "missing_mundari_words": [self.items[n]["mundari_text"] for n in missing_vals],
                },
                solution=missing_vals,
            )
            problems.append(asdict(prob))

        return WorksheetDocument(
            worksheet_id="WS_05_MISSING_NUMBERS",
            title_hi="कार्यपत्रक ५: छूटी हुई संख्याएँ भरें",
            title_unr="कामि साकाम ५: अदआकान लेका पेरेःपे",
            grade=1,
            subject="Mathematics",
            fln_domain="Foundational Numeracy",
            topic="Numbers 1-20",
            target_competency="M1.4 (UNVERIFIED — PENDING SOURCE VALIDATION)",
            generation_seed=seed or self.seed + 4,
            provenance_status="GENERATED_PROTOTYPE (PENDING HUMAN VALIDATION)",
            problems=problems,
        )

    def render_worksheet_html(self, doc: WorksheetDocument) -> str:
        """Generates clean, printable offline A4-styled HTML/CSS worksheet."""
        problems_html = []

        for p in doc.problems:
            pid = p["problem_id"]
            p_type = p["problem_type"]
            data = p["prompt_data"]

            if p_type == "number_recognition":
                opts_html = "".join(
                    [
                        f'<div class="recog-bubble"><b>{opt["number"]}</b><br><span class="hi-num">{opt["numeral"]}</span></div>'
                        for opt in p["options"]
                    ]
                )
                problems_html.append(
                    f"""<div class="problem-card">
  <div class="problem-header">
    <span class="p-num">{pid.split('_')[-1]}</span>
    <div class="p-instruction">{p["instruction_hi"]} <b>{data["mundari_word"]}</b> ({data["hindi_word"]})</div>
  </div>
  <div class="bubble-row">{opts_html}</div>
</div>"""
                )

            elif p_type == "counting":
                count = data["count"]
                dots = "".join(['<span class="dot"></span>' for _ in range(count)])
                problems_html.append(
                    f"""<div class="problem-card">
  <div class="problem-header">
    <span class="p-num">{pid.split('_')[-1]}</span>
    <div class="p-instruction">{p["instruction_hi"]}</div>
  </div>
  <div class="counting-box">
    <div class="dots-grid">{dots}</div>
    <div class="answer-box">संख्या: [ &nbsp;&nbsp;&nbsp;&nbsp; ] &nbsp;|&nbsp; मुंडारी: __________________</div>
  </div>
</div>"""
                )

            elif p_type == "matching_quantity_to_numeral":
                dots = "".join(['<span class="mini-dot"></span>' for _ in range(data["quantity"])])
                problems_html.append(
                    f"""<div class="match-row">
  <div class="match-left"><div class="dots-grid">{dots}</div></div>
  <div class="match-line-target">● ------------------------ ●</div>
  <div class="match-right"><b>{data["right_target_number"]}</b> ({data["right_hindi_numeral"]}) — <i>{data["right_mundari_word"]}</i></div>
</div>"""
                )

            elif p_type == "simple_sequencing":
                scrambled = " &nbsp;&nbsp;•&nbsp;&nbsp; ".join(str(n) for n in data["scrambled_numbers"])
                problems_html.append(
                    f"""<div class="problem-card">
  <div class="problem-header">
    <span class="p-num">{pid.split('_')[-1]}</span>
    <div class="p-instruction">{p["instruction_hi"]}</div>
  </div>
  <div class="scramble-box">उलटे क्रम: <b>{scrambled}</b></div>
  <div class="sequence-fill">सही क्रम: [ &nbsp;&nbsp;&nbsp; ] &rarr; [ &nbsp;&nbsp;&nbsp; ] &rarr; [ &nbsp;&nbsp;&nbsp; ] &rarr; [ &nbsp;&nbsp;&nbsp; ] &rarr; [ &nbsp;&nbsp;&nbsp; ]</div>
</div>"""
                )

            elif p_type == "missing_numbers":
                train_cars = []
                for val in data["sequence_with_gaps"]:
                    if val is None:
                        train_cars.append('<div class="car missing">[ &nbsp; ]</div>')
                    else:
                        train_cars.append(f'<div class="car filled">{val}</div>')
                problems_html.append(
                    f"""<div class="problem-card">
  <div class="problem-header">
    <span class="p-num">{pid.split('_')[-1]}</span>
    <div class="p-instruction">{p["instruction_hi"]}</div>
  </div>
  <div class="train-track">{''.join(train_cars)}</div>
</div>"""
                )

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{doc.title_hi}</title>
  <style>
    @page {{ size: A4; margin: 15mm; }}
    body {{
      font-family: 'Segoe UI', 'Noto Sans Devanagari', sans-serif;
      color: #1E293B;
      background: #FFFFFF;
      margin: 0;
      padding: 15px;
    }}
    .sheet-header {{
      border-bottom: 2px solid #0F172A;
      padding-bottom: 10px;
      margin-bottom: 16px;
    }}
    .title-hi {{ font-size: 20px; font-weight: bold; color: #0F172A; margin: 0 0 4px 0; }}
    .title-unr {{ font-size: 14px; color: #047857; margin: 0 0 8px 0; font-weight: 600; }}
    .meta-row {{
      display: flex;
      justify-content: space-between;
      font-size: 12px;
      background: #F8FAFC;
      padding: 6px 12px;
      border-radius: 4px;
      border: 1px solid #E2E8F0;
    }}
    .student-bar {{
      display: flex;
      gap: 20px;
      margin-top: 8px;
      font-size: 13px;
      padding: 4px 0;
    }}
    .badge {{
      display: inline-block;
      background: #FEF3C7;
      color: #B45309;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: bold;
    }}
    .problem-card {{
      margin-bottom: 14px;
      padding: 10px;
      border: 1px solid #E2E8F0;
      border-radius: 8px;
      background: #FAFAFA;
      page-break-inside: avoid;
    }}
    .problem-header {{
      display: flex;
      gap: 10px;
      align-items: baseline;
      margin-bottom: 8px;
    }}
    .p-num {{
      background: #0F172A;
      color: #FFF;
      font-size: 11px;
      font-weight: bold;
      padding: 2px 6px;
      border-radius: 4px;
    }}
    .p-instruction {{ font-size: 14px; font-weight: 500; }}
    .bubble-row {{ display: flex; gap: 16px; margin-top: 6px; }}
    .recog-bubble {{
      width: 60px;
      height: 60px;
      border-radius: 50%;
      border: 2px solid #3B82F6;
      background: #FFF;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      cursor: pointer;
    }}
    .recog-bubble .hi-num {{ font-size: 12px; color: #64748B; }}
    .counting-box {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #FFF;
      padding: 8px 12px;
      border-radius: 6px;
      border: 1px solid #CBD5E1;
    }}
    .dots-grid {{ display: flex; flex-wrap: wrap; gap: 6px; max-width: 260px; }}
    .dot {{ width: 16px; height: 16px; border-radius: 50%; background: #E11D48; display: inline-block; }}
    .mini-dot {{ width: 12px; height: 12px; border-radius: 50%; background: #059669; display: inline-block; }}
    .answer-box {{ font-size: 14px; font-weight: bold; color: #1E40AF; }}
    .match-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 12px;
      border-bottom: 1px dashed #CBD5E1;
    }}
    .match-left {{ width: 35%; }}
    .match-line-target {{ width: 30%; text-align: center; color: #94A3B8; font-size: 12px; }}
    .match-right {{ width: 35%; text-align: right; font-size: 15px; }}
    .scramble-box {{ font-size: 14px; color: #64748B; margin: 4px 0 8px 0; }}
    .sequence-fill {{ font-size: 14px; font-weight: bold; color: #0F172A; }}
    .train-track {{ display: flex; gap: 6px; margin-top: 6px; }}
    .car {{
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 4px;
      font-size: 16px;
      font-weight: bold;
    }}
    .car.filled {{ background: #DBEAFE; border: 2px solid #3B82F6; color: #1E40AF; }}
    .car.missing {{ background: #FEF3C7; border: 2px dashed #D97706; color: #B45309; }}
    .footer {{
      text-align: center;
      font-size: 10px;
      color: #94A3B8;
      margin-top: 20px;
      border-top: 1px solid #E2E8F0;
      padding-top: 6px;
    }}
  </style>
</head>
<body>
  <div class="sheet-header">
    <div class="title-hi">{doc.title_hi}</div>
    <div class="title-unr">{doc.title_unr}</div>
    <div class="meta-row">
      <span>कक्षा: {doc.grade} | विषय: {doc.subject}</span>
      <span>डोमेन: {doc.fln_domain} ({doc.topic})</span>
      <span class="badge">{doc.provenance_status}</span>
    </div>
    <div class="student-bar">
      <span>विद्यार्थी का नाम (होड़ो नुतुम): ________________________</span>
      <span>दिनांक: ____________</span>
      <span>हस्ताक्षर: ____________</span>
    </div>
  </div>

  <div class="problems-container">
    {''.join(problems_html)}
  </div>

  <div class="footer">
    SIH260042 • AI-Powered Vernacular Pedagogy & MTB-MLE Primary Education (Jharkhand) • Offline Educational Asset
  </div>
</body>
</html>"""
        return html

    def generate_all_worksheets(self) -> Dict[str, str]:
        """Generates all 5 worksheet types in both JSON and printable HTML formats."""
        generators = [
            ("ws_01_recognition", self.generate_number_recognition_worksheet),
            ("ws_02_counting", self.generate_counting_worksheet),
            ("ws_03_matching", self.generate_matching_worksheet),
            ("ws_04_sequencing", self.generate_sequencing_worksheet),
            ("ws_05_missing_numbers", self.generate_missing_numbers_worksheet),
        ]

        generated_paths = {}
        for name, gen_func in generators:
            doc = gen_func()
            # Save JSON
            json_path = os.path.join(self.output_dir, f"{name}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(asdict(doc), f, ensure_ascii=False, indent=2)

            # Save HTML
            html_content = self.render_worksheet_html(doc)
            html_path = os.path.join(self.output_dir, f"{name}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            generated_paths[f"{name}_json"] = json_path
            generated_paths[f"{name}_html"] = html_path

        return generated_paths


if __name__ == "__main__":
    generator = WorksheetGenerator()
    paths = generator.generate_all_worksheets()
    print(f"Generated {len(paths)} worksheet asset files in content/worksheets/generated/")
