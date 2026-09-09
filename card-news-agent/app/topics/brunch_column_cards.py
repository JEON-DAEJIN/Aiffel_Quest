from .base import TopicConfig

# 브런치(@storywiz) 연재 에세이를 인스타그램 카드뉴스로 전환하는 토픽. voice_column_cards와
# 같은 "원고 1편 → 분할안 선택 → 8장 카드" 구조를 그대로 쓰되, 마지막 카드는 QR코드+URL로
# 원문(브런치 글)을 볼 수 있게 하는 안내 카드로 바뀐다(cta_card=True).
BRUNCH_COLUMN_CARDS = TopicConfig(
    topic_id="brunch_column_cards",
    display_name="브런치 칼럼 → 인스타그램 카드(원문 링크 포함)",
    input_mode="source_text",
    tools=[],
    cta_card=True,
    research_prompt_template=(
        "Here is a finished Korean personal essay published on Brunch (a Korean essay/blogging "
        "platform):\n\n---\n{source_text}\n---\n\n"
        "Propose {min_candidates} to {max_candidates} DIFFERENT ways to divide this essay into a "
        "7-card Instagram carousel (the 8th and final card is a fixed call-to-action card and is "
        "NOT part of this division — only plan the first 7 cards here). For each division plan, "
        "describe the overall flow/ordering it uses and why that flow suits this particular essay's "
        "personal, reflective tone. Do not write the actual card text yet — only describe the "
        "division strategy at a high level. Use the 'title' field for a short name of the division "
        "plan, 'summary' for the flow description, 'why_worth_choosing' for its strength, 'date' for "
        "today's date, and 'source_url' left as an empty string (not applicable here)."
    ),
    candidate_count_range=(2, 3),
    selection_range=(1, 1),
    storyboard_card_range=(8, 8),
    image_style_guidance=(
        "quiet literary illustration style with an introspective, memoir-like mood, soft natural "
        "light, gentle muted pastel colors, simple uncluttered composition evoking a personal diary "
        "or essay collection, avoid busy or corporate look, leave empty space near the top for a "
        "title overlay"
    ),
)
