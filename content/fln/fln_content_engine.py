"""
FLN Content Engine for Mother Tongue-Based Primary Education.

Provides modular pedagogical abstraction for Grade 1 Numeracy (Numbers 1-20):
- Lesson definitions mapping Hindi teacher input to Mundari student comprehension
- Pedagogical competencies and learning outcome tracking
- Activity generation (Listen & Identify, Count Objects, Teacher Bridge, Sequencing)
- Offline asset reference management
"""

import os
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class FLNLesson:
    """Complete pedagogical lesson representation for an individual number."""
    grade: int
    subject: str
    fln_domain: str
    topic: str
    number: int
    class_index: int
    hindi_content: Dict[str, str]
    mundari_content: Dict[str, Any]
    audio_ref: str
    audio_status: str
    flashcard_ref: str
    flashcard_status: str
    competency_code: str
    nipun_verification_status: str
    learning_outcome_hi: str
    learning_outcome_unr: str
    learning_outcome_en: str


@dataclass
class FLNActivity:
    """Interactive learning activity for classroom and mobile app use."""
    activity_id: str
    activity_type: str
    target_number: int
    title_hi: str
    title_unr: str
    instruction_hi: str
    instruction_unr: str
    prompt_data: Dict[str, Any]
    options: List[Dict[str, Any]]
    correct_answer: Any
    audio_ref: Optional[str]
    flashcard_ref: Optional[str]


class FLNContentEngine:
    """Core educational engine driving MTB-MLE classroom instruction."""

    def __init__(self, registry_path: Optional[str] = None, curriculum_path: Optional[str] = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.registry_path = registry_path or os.path.join(base_dir, "content", "content_registry.json")
        self.curriculum_path = curriculum_path or os.path.join(base_dir, "content", "fln", "curriculum_model.json")
        
        self.registry_data = self._load_json(self.registry_path)
        self.curriculum_data = self._load_json(self.curriculum_path) if os.path.exists(self.curriculum_path) else {}
        
        # Build quick lookup tables
        self._by_number = {}
        self._by_hindi_word = {}
        self._by_class_index = {}
        
        for item in self.registry_data.get("items", []):
            num = item["number"]
            self._by_number[num] = item
            self._by_hindi_word[item["hindi_text"].strip()] = item
            self._by_hindi_word[item["hindi_numeral"].strip()] = item
            self._by_hindi_word[str(num)] = item
            self._by_class_index[item["class_index"]] = item

    def _load_json(self, path: str) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_lesson(self, number: int) -> FLNLesson:
        """Retrieves structured bilingual lesson for a specific number (1-20)."""
        if number not in self._by_number:
            raise ValueError(f"Number {number} is out of range for Grade 1 FLN (1-20)")
        
        raw = self._by_number[number]
        
        hindi_content = {
            "numeral": raw["hindi_numeral"],
            "word": raw["hindi_text"],
            "teacher_prompt": f"बच्चों, यह संख्या {raw['hindi_text']} ({raw['hindi_numeral']}) है। इसे ध्यान से देखें।"
        }
        
        mundari_content = {
            "numeral": raw["mundari_numeral"],
            "word": raw["mundari_text"],
            "root": raw["mundari_root"],
            "phonetic": raw["mundari_phonetic"],
            "variants": raw.get("variants_attested", []),
            "student_echo": f"नेआ दो {raw['mundari_text']} तना।"
        }
        
        return FLNLesson(
            grade=raw["grade"],
            subject=raw["subject"],
            fln_domain=raw["fln_domain"],
            topic=raw["topic"],
            number=raw["number"],
            class_index=raw["class_index"],
            hindi_content=hindi_content,
            mundari_content=mundari_content,
            audio_ref=raw["audio_asset"],
            audio_status=raw["audio_status"],
            flashcard_ref=raw["flashcard_asset"],
            flashcard_status=raw["flashcard_status"],
            competency_code=raw["nipun_competency_code"],
            nipun_verification_status=raw.get("nipun_verification_status", "UNVERIFIED — PENDING SOURCE VALIDATION"),
            learning_outcome_hi=f"संख्या {raw['number']} ({raw['hindi_text']}) को पहचानना, गिनना और मातृभाषा में बोलना",
            learning_outcome_unr=f"{raw['mundari_text']} लेका उरुम, लेका आर आपान जगरते काजी",
            learning_outcome_en=f"Recognize, count, and pronounce numeral {raw['number']} in Mundari"
        )

    def get_all_lessons(self) -> List[FLNLesson]:
        """Returns all 20 lessons in sequential order."""
        return [self.get_lesson(n) for n in range(1, 21)]

    def bridge_teacher_input(self, query: str) -> Dict[str, Any]:
        """
        Translates teacher's Hindi spoken/typed number into student-facing Mundari pedagogy.
        Returns complete educational card, audio reference, and learning outcomes.
        """
        cleaned = query.strip()
        if cleaned in self._by_hindi_word:
            item = self._by_hindi_word[cleaned]
            lesson = self.get_lesson(item["number"])
            return {
                "matched": True,
                "confidence": 1.0,
                "source_input": query,
                "lesson": asdict(lesson)
            }
        
        return {
            "matched": False,
            "confidence": 0.0,
            "source_input": query,
            "message": "Number not found in Grade 1 FLN 1-20 curriculum"
        }

    def create_activity(self, activity_type: str, number: int) -> FLNActivity:
        """Generates deterministic, pedagogically aligned activity for a number."""
        lesson = self.get_lesson(number)
        act_id = f"ACT_{activity_type}_{number:02d}"

        if activity_type == "listen_and_identify":
            # Generate 3 distractor numbers
            all_nums = [n for n in range(1, 21) if n != number]
            # Deterministic distractors based on number
            d1 = ((number + 1) - 1) % 20 + 1
            d2 = ((number + 4) - 1) % 20 + 1
            d3 = ((number + 9) - 1) % 20 + 1
            options_nums = sorted(list({number, d1, d2, d3}))
            
            options = []
            for n in options_nums:
                opt_item = self._by_number[n]
                options.append({
                    "number": n,
                    "numeral": opt_item["hindi_numeral"],
                    "mundari_word": opt_item["mundari_text"],
                    "is_correct": (n == number)
                })

            return FLNActivity(
                activity_id=act_id,
                activity_type=activity_type,
                target_number=number,
                title_hi=f"ध्वनि सुनकर संख्या पहचानें: {lesson.hindi_content['word']}",
                title_unr=f"साड़ि आयूमकेआते लेका उरुमपे: {lesson.mundari_content['word']}",
                instruction_hi=f"मुंडारी शब्द '{lesson.mundari_content['word']}' सुनें और सही संख्या चुनें।",
                instruction_unr=f"'{lesson.mundari_content['word']}' आयूमपे आर सोझोः लेका चुनवावपे।",
                prompt_data={"target_number": number, "audio_to_play": lesson.audio_ref},
                options=options,
                correct_answer=number,
                audio_ref=lesson.audio_ref,
                flashcard_ref=lesson.flashcard_ref
            )

        elif activity_type == "count_objects":
            return FLNActivity(
                activity_id=act_id,
                activity_type=activity_type,
                target_number=number,
                title_hi=f"चित्र गिनें और संख्या बताएं ({lesson.hindi_content['word']})",
                title_unr=f"चित्र लेकापे आर काजीपे ({lesson.mundari_content['word']})",
                instruction_hi=f"दी गई वस्तुओं को गिनें और मुंडारी में बोलें।",
                instruction_unr=f"ने चिनहाः को लेकापे आर मुंडारी ते काजीपे।",
                prompt_data={
                    "quantity": number,
                    "visual_grouping": "ten_frame" if number > 10 else "single_group",
                    "tens": number // 10,
                    "ones": number % 10
                },
                options=[{"number": number, "mundari_word": lesson.mundari_content["word"]}],
                correct_answer=number,
                audio_ref=lesson.audio_ref,
                flashcard_ref=lesson.flashcard_ref
            )

        elif activity_type == "missing_number":
            # Missing number in simple sequence
            start = max(1, number - 2)
            seq = list(range(start, min(21, start + 5)))
            missing_idx = seq.index(number)
            display_seq = [None if i == missing_idx else s for i, s in enumerate(seq)]
            
            return FLNActivity(
                activity_id=act_id,
                activity_type=activity_type,
                target_number=number,
                title_hi="खाली स्थान भरें (क्रम पहचान)",
                title_unr="खाली जागह पेरेःपे (क्रम उरुम)",
                instruction_hi=f"क्रम को पूरा करने के लिए लुप्त संख्या पहचानें।",
                instruction_unr=f"सिरिस पूरा नातिन अदआकान लेका उरुमपे।",
                prompt_data={"sequence_display": display_seq, "missing_position": missing_idx},
                options=[
                    {"number": number, "is_correct": True},
                    {"number": (number % 20) + 1, "is_correct": False}
                ],
                correct_answer=number,
                audio_ref=lesson.audio_ref,
                flashcard_ref=lesson.flashcard_ref
            )
        else:
            raise ValueError(f"Unknown activity type: {activity_type}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    engine = FLNContentEngine()
    print("FLN Content Engine initialized.")
    lesson_5 = engine.get_lesson(5)
    print("Lesson 5:", lesson_5.hindi_content["word"], "->", lesson_5.mundari_content["word"])
    act = engine.create_activity("listen_and_identify", 5)
    print("Activity:", act.title_hi)
