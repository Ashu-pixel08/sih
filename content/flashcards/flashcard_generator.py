"""
Flashcard Generator for FLN Grade 1 Numeracy (Numbers 1-20).

Generates high-contrast, scalable, child-friendly vector flashcards:
- 10-Frame quantity representation (visualizing units and base-10 structure)
- Dual numeral representation (International + Devanagari digits)
- Bilingual terminology (Mundari mother-tongue + Hindi classroom language)
- Clear provenance badge: 'GENERATED PROTOTYPE (PENDING HUMAN VALIDATION)'
- SVG vector format for crisp rendering at any resolution on low-cost Android tablets
"""

import os
import json
from typing import Dict, Any, List, Optional


class FlashcardGenerator:
    """Generates deterministic, offline-compatible SVG and HTML educational flashcards."""

    def __init__(self, registry_path: Optional[str] = None):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.registry_path = registry_path or os.path.join(base_dir, "content", "content_registry.json")
        self.output_dir = os.path.join(base_dir, "content", "flashcards", "numbers")
        os.makedirs(self.output_dir, exist_ok=True)

        with open(self.registry_path, "r", encoding="utf-8") as f:
            self.registry = json.load(f)

    def _render_ten_frame_svg(self, count: int, x_offset: int, y_offset: int, scale: float = 1.0) -> str:
        """
        Renders a 2x5 Ten-Frame grid with `count` filled counters.
        Ten-frame math layout is the NIPUN/FLN standard for visualizing base-10 quantities.
        """
        box_w, box_h = 32, 32
        radius = 11
        svg_parts = []

        # Outer border
        total_w = box_w * 5
        total_h = box_h * 2
        svg_parts.append(
            f'<rect x="{x_offset}" y="{y_offset}" width="{total_w}" height="{total_h}" '
            f'fill="#FFFFFF" stroke="#334155" stroke-width="2" rx="4"/>'
        )

        # Internal grid lines
        for c in range(1, 5):
            svg_parts.append(
                f'<line x1="{x_offset + c * box_w}" y1="{y_offset}" '
                f'x2="{x_offset + c * box_w}" y2="{y_offset + total_h}" stroke="#CBD5E1" stroke-width="1.5"/>'
            )
        svg_parts.append(
            f'<line x1="{x_offset}" y1="{y_offset + box_h}" '
            f'x2="{x_offset + total_w}" y2="{y_offset + box_h}" stroke="#CBD5E1" stroke-width="1.5"/>'
        )

        # Filled counters (top row 1-5, bottom row 6-10)
        filled = min(10, count)
        for i in range(filled):
            row = i // 5
            col = i % 5
            cx = x_offset + col * box_w + box_w // 2
            cy = y_offset + row * box_h + box_h // 2
            svg_parts.append(
                f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#E11D48" stroke="#9F1239" stroke-width="1.5"/>'
            )

        return "".join(svg_parts)

    def generate_card_svg(self, item: Dict[str, Any]) -> str:
        """
        Generates clean, scalable SVG string for an individual number card (width=400, height=520).
        """
        num = item["number"]
        hi_num = item["hindi_numeral"]
        hi_text = item["hindi_text"]
        mu_text = item["mundari_text"]
        mu_phonetic = item["mundari_phonetic"]
        mu_root = item["mundari_root"]
        audio_ref = item["audio_asset"]
        audio_status = item["audio_status"]

        # Quantity rendering: 1 frame for 1-10, 2 frames for 11-20
        if num <= 10:
            frame_x = 120
            frame_y = 175
            ten_frame_svg = self._render_ten_frame_svg(num, frame_x, frame_y)
        else:
            # First ten frame (complete 10)
            ten_frame_svg = self._render_ten_frame_svg(10, 35, 175)
            # Second ten frame (remainder)
            ten_frame_svg += self._render_ten_frame_svg(num - 10, 205, 175)

        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 520" width="400" height="520">
  <defs>
    <linearGradient id="cardBg" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#F8FAFC"/>
      <stop offset="100%" stop-color="#F1F5F9"/>
    </linearGradient>
    <filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-opacity="0.12"/>
    </filter>
  </defs>

  <!-- Card Background -->
  <rect x="15" y="15" width="370" height="490" rx="16" fill="url(#cardBg)" stroke="#CBD5E1" stroke-width="2" filter="url(#shadow)"/>

  <!-- Educational Provenance Banner -->
  <rect x="25" y="25" width="350" height="28" rx="6" fill="#FEF3C7"/>
  <text x="200" y="44" font-family="'Noto Sans', 'Segoe UI', Arial, sans-serif" font-size="11" font-weight="bold" fill="#B45309" text-anchor="middle">
    GENERATED PROTOTYPE (PENDING HUMAN VALIDATION)
  </text>

  <!-- Large Numeral Badges -->
  <circle cx="90" cy="105" r="42" fill="#3B82F6"/>
  <text x="90" y="120" font-family="'Segoe UI', Arial, sans-serif" font-size="44" font-weight="900" fill="#FFFFFF" text-anchor="middle">{num}</text>

  <circle cx="310" cy="105" r="42" fill="#059669"/>
  <text x="310" y="120" font-family="'Noto Sans Devanagari', 'Mangal', Arial, sans-serif" font-size="40" font-weight="bold" fill="#FFFFFF" text-anchor="middle">{hi_num}</text>

  <!-- Subtitle for numerals -->
  <text x="90" y="160" font-family="'Segoe UI', Arial, sans-serif" font-size="12" fill="#64748B" text-anchor="middle">
    DIGIT
  </text>
  <text x="310" y="160" font-family="'Noto Sans Devanagari', Arial, sans-serif" font-size="12" fill="#64748B" text-anchor="middle">
    देवनागरी
  </text>

  <!-- Quantity Representation (Ten Frame) -->
  {ten_frame_svg}

  <!-- Divider Line -->
  <line x1="40" y1="265" x2="360" y2="265" stroke="#E2E8F0" stroke-width="2"/>

  <!-- Mundari Language Section (Mother Tongue Focus) -->
  <rect x="35" y="280" width="330" height="95" rx="10" fill="#ECFDF5" stroke="#A7F3D0" stroke-width="1.5"/>
  <text x="50" y="302" font-family="'Segoe UI', Arial, sans-serif" font-size="11" font-weight="bold" fill="#047857">
    MUNDARI (मातृभाषा):
  </text>
  <text x="200" y="340" font-family="'Noto Sans Devanagari', 'Mangal', Arial, sans-serif" font-size="34" font-weight="bold" fill="#065F46" text-anchor="middle">
    {mu_text}
  </text>
  <text x="200" y="364" font-family="'Segoe UI', Arial, sans-serif" font-size="14" font-style="italic" fill="#047857" text-anchor="middle">
    "{mu_phonetic}" (Root: {mu_root})
  </text>

  <!-- Hindi Language Section (Teacher Medium) -->
  <rect x="35" y="385" width="330" height="60" rx="10" fill="#EFF6FF" stroke="#BFDBFE" stroke-width="1.5"/>
  <text x="50" y="405" font-family="'Segoe UI', Arial, sans-serif" font-size="11" font-weight="bold" fill="#1D4ED8">
    HINDI (शिक्षक माध्यम):
  </text>
  <text x="200" y="432" font-family="'Noto Sans Devanagari', 'Mangal', Arial, sans-serif" font-size="24" font-weight="bold" fill="#1E40AF" text-anchor="middle">
    {hi_text} ({hi_num})
  </text>

  <!-- Footer: Asset & Audio Reference Status -->
  <text x="200" y="475" font-family="'Segoe UI', Arial, sans-serif" font-size="11" fill="#64748B" text-anchor="middle">
    Audio: {audio_ref} [{audio_status}]
  </text>
  <text x="200" y="492" font-family="'Segoe UI', Arial, sans-serif" font-size="10" fill="#94A3B8" text-anchor="middle">
    Class Index: {item["class_index"]} | Target Grade 1 FLN Numeracy
  </text>
</svg>"""
        return svg

    def generate_all_flashcards(self) -> List[str]:
        """Generates SVG flashcard files for all 20 numbers."""
        created_files = []
        for item in self.registry.get("items", []):
            num = item["number"]
            svg_content = self.generate_card_svg(item)
            file_name = f"card_{num:02d}.svg"
            file_path = os.path.join(self.output_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(svg_content)
            created_files.append(file_path)

        # Also generate the standalone HTML review deck
        self.generate_html_deck()
        return created_files

    def generate_html_deck(self) -> str:
        """Generates an offline interactive HTML visual gallery for the entire flashcard deck."""
        deck_path = os.path.join(os.path.dirname(self.output_dir), "flashcard_deck.html")
        items = self.registry.get("items", [])

        cards_html = []
        for item in items:
            num = item["number"]
            svg_content = self.generate_card_svg(item)
            cards_html.append(
                f'<div class="card-wrapper" id="card-{num}">\n{svg_content}\n</div>'
            )

        full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Mundari FLN Grade 1 Flashcards (Numbers 1-20)</title>
  <style>
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0F172A;
      color: #F8FAFC;
      margin: 0;
      padding: 24px;
    }}
    .header {{
      text-align: center;
      margin-bottom: 28px;
    }}
    h1 {{ margin: 0 0 8px 0; color: #38BDF8; font-size: 26px; }}
    .subtitle {{ color: #94A3B8; font-size: 14px; max-width: 680px; margin: 0 auto; line-height: 1.5; }}
    .badge {{
      display: inline-block;
      background: #B45309;
      color: #FEF3C7;
      padding: 4px 12px;
      border-radius: 9999px;
      font-size: 12px;
      font-weight: 600;
      margin-top: 10px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 24px;
      max-width: 1400px;
      margin: 0 auto;
    }}
    .card-wrapper {{
      display: flex;
      justify-content: center;
      transition: transform 0.2s ease;
    }}
    .card-wrapper:hover {{
      transform: translateY(-4px);
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Mundari FLN Grade 1 Numeracy Flashcards</h1>
    <div class="subtitle">
      Mother Tongue-Based Multilingual Education (MTB-MLE) visual cards pairing Hindi teacher instruction with Mundari child comprehension. Ten-frame quantity grids support base-10 cognitive scaffolding.
    </div>
    <div class="badge">PROTOTYPE GENERATION (PENDING NATIVE EDUCATOR REVIEW)</div>
  </div>
  <div class="grid">
    {''.join(cards_html)}
  </div>
</body>
</html>"""
        with open(deck_path, "w", encoding="utf-8") as f:
            f.write(full_html)
        return deck_path


if __name__ == "__main__":
    gen = FlashcardGenerator()
    cards = gen.generate_all_flashcards()
    print(f"Generated {len(cards)} SVG flashcards in content/flashcards/numbers/")
