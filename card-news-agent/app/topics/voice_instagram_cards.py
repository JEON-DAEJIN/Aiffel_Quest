from .base import TopicConfig

# 프로젝트 VOICE(Making_Contents)의 M7 "채널 파생" 모듈 중 인스타그램 카드 출력을
# 앞당겨 구현한 토픽. 입력은 웹 조사가 아니라 이미 완성된 원고 1편(source_text)이고,
# "후보"는 뉴스 후보가 아니라 그 원고를 8장 카드로 나누는 서로 다른 분할안이다.
VOICE_COLUMN_CARDS = TopicConfig(
    topic_id="voice_column_cards",
    display_name="VOICE 칼럼 → 인스타그램 카드",
    input_mode="source_text",
    tools=[],  # 원고 안에서만 근거를 찾는다 — 외부 검색 불필요
    research_prompt_template=(
        "Here is a finished Korean column/article:\n\n---\n{source_text}\n---\n\n"
        "Propose {min_candidates} to {max_candidates} DIFFERENT ways to divide this article "
        "into an 8-card Instagram carousel (one core message per card). For each division plan, "
        "describe the overall flow/ordering it uses (e.g. \"event first, then metaphor, then "
        "present-day application\") and why that flow works for this particular article. Do not "
        "write the actual card text yet — only describe the division strategy at a high level. "
        "Use the 'title' field for a short name of the division plan, 'summary' for the flow "
        "description, 'why_worth_choosing' for its strength, 'date' for today's date, and "
        "'source_url' left as an empty string (not applicable here)."
    ),
    candidate_count_range=(2, 3),
    selection_range=(1, 1),
    storyboard_card_range=(8, 8),
    image_style_guidance=(
        "warm editorial illustration style evoking everyday Korean life and gentle nostalgia, "
        "muted warm color palette, simple uncluttered composition, avoid generic corporate "
        "stock-photo look, leave empty space near the top for a title overlay"
    ),
)
