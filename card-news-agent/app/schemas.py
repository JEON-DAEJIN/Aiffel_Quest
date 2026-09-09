from pydantic import BaseModel, Field

# ---------- AI 호출 계약 (구조화 출력 스키마) ----------
# DJ 체크리스트 3번(필요한 만큼만 받기): 후보/카드마다 꼭 필요한 필드만 요구한다.

RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "search_window_days": {"type": "integer"},
        "expanded_search": {"type": "boolean"},
        "candidates": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                    "title": {"type": "string"},
                    "date": {"type": "string"},
                    "source_url": {"type": "string"},
                    "summary": {"type": "string"},
                    "why_worth_choosing": {"type": "string"},
                },
                "required": [
                    "candidate_id",
                    "title",
                    "date",
                    "source_url",
                    "summary",
                    "why_worth_choosing",
                ],
            },
        },
    },
    "required": ["search_window_days", "expanded_search", "candidates"],
}

# DJ 체크리스트 5번(근거 있는 답 요구): confirmed_facts/unconfirmed_claims/evidence_url을
# 분리 요구해서 "그럴듯한 결론"만 오는 걸 막는다.
STORYBOARD_SCHEMA = {
    "type": "object",
    "properties": {
        "verifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_id": {"type": "string"},
                    "confirmed_facts": {"type": "array", "items": {"type": "string"}},
                    "unconfirmed_claims": {"type": "array", "items": {"type": "string"}},
                    "evidence_url": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "candidate_id",
                    "confirmed_facts",
                    "unconfirmed_claims",
                    "evidence_url",
                ],
            },
        },
        "storyboard": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "card_number": {"type": "integer"},
                    "headline": {"type": "string"},
                    "body": {"type": "string"},
                    "image_role": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": ["card_number", "headline", "body", "image_role", "source"],
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verifications", "storyboard"],
}


# ---------- API 요청/응답 모델 ----------

class CreateRunRequest(BaseModel):
    topic_id: str
    source_text: str | None = None
    source_url: str | None = None


class SelectRequest(BaseModel):
    candidate_ids: list[str] = Field(min_length=1)


class ReviewRequest(BaseModel):
    action: str  # "approve" | "revise"
    notes: str | None = None


class RegenerateCardRequest(BaseModel):
    card_number: int
