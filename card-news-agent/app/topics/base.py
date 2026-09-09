from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TopicConfig:
    """새 주제를 추가하려면 이 dataclass의 인스턴스를 하나 더 만들고
    registry.py의 TOPICS에 등록하면 된다. engine.py/main.py는 절대 수정하지 않는다."""

    topic_id: str
    display_name: str
    research_prompt_template: str
    candidate_count_range: tuple[int, int] = (7, 12)
    selection_range: tuple[int, int] = (1, 3)
    storyboard_card_range: tuple[int, int] = (5, 8)
    lookback_days_default: int = 7
    lookback_days_expanded: int = 30
    research_model: str = "claude-sonnet-5"
    verification_model: str = "claude-sonnet-5"
    output_language: str = "ko"
    image_style_guidance: str = (
        "clean modern illustration, consistent color palette across cards, "
        "simple composition, leave empty space near the top for a title overlay"
    )
    image_quality: str = "medium"  # OpenAI gpt-image-1: low | medium | high | auto
    tools: list[str] = field(default_factory=lambda: ["WebSearch", "WebFetch"])
    input_mode: str = "web_research"  # "web_research" | "source_text"
    cta_card: bool = False  # True면 마지막 스토리보드 카드를 QR+URL 안내 카드로 대체한다
    extra_params: dict[str, Any] = field(default_factory=dict)

    def research_prompt(self, source_text: str | None = None) -> str:
        lo, hi = self.candidate_count_range
        return self.research_prompt_template.format(
            lookback_days=self.lookback_days_default,
            expanded_days=self.lookback_days_expanded,
            min_candidates=lo,
            max_candidates=hi,
            source_text=source_text or "",
        )
