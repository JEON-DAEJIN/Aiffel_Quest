"""OpenAI gpt-image-1 호출 래퍼.

DJ 체크리스트 적용:
- 1) 언제 쓰고 안 쓰는지: 이 모듈은 오직 카드 배경 이미지 생성에만 쓰인다. 프롬프트
  끝에 항상 "글자 넣지 마" 지시를 강제로 덧붙여 목적 밖 결과(이미지 안에 텍스트가
  박히는 것)를 막는다.
- 2) 실패했을 때 뭘 할지 미리 정한다: API 키 미설정·API 에러는 즉시 명확한 예외로
  올린다 — 추측성 재시도를 하지 않는다. 호출자(engine.py)가 카드 단위로 실패를
  기록하고 넘어간다.

gpt-image-1은 임의 크기(예: 1080x1350)를 받지 않는다 — 1024x1024/1536x1024/1024x1536/
auto 중 하나만 허용된다. 카드뉴스 세로형 비율에 가장 가까운 1024x1536으로 생성하고,
실제 1080x1350 크롭은 image_compose.py가 담당한다.
"""

import base64
import os

from openai import OpenAI

# 실제로 "경쟁사 로고" 묘사를 요청했더니 전혀 무관한 실제 상표(그럽허브·우버이츠·도어대시)를
# 그려낸 사례가 나와서(2026-09-09, voice_column_cards 카드4) 명시적으로 금지 문구를 추가했다.
NO_TEXT_SUFFIX = (
    " No text, no lettering, no captions, no speech bubbles, no watermarks anywhere in the image."
    " Do not depict any real brand names, logos, or trademarks (even as generic-looking "
    "'competitor' icons) — use abstract or clearly fictional shapes/icons instead."
)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 키를 넣고 서버를 재시작하세요."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def generate_card_background(prompt: str, *, quality: str = "medium") -> bytes:
    """카드 배경 이미지를 생성해 PNG raw bytes로 반환한다. 실패하면 예외를 그대로 던진다
    (호출자가 카드 단위로 잡아서 처리)."""
    client = _get_client()
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt + NO_TEXT_SUFFIX,
        n=1,
        size="1024x1536",
        quality=quality,
        output_format="png",
        background="opaque",
    )
    b64 = response.data[0].b64_json
    if not b64:
        raise RuntimeError("OpenAI 응답에 b64_json이 없습니다.")
    return base64.b64decode(b64)
