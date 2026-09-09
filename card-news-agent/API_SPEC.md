# API_SPEC — 화면과 서버의 약속

## 상태 머신

`status`(진행 상태) × `stage`(세부 단계) 두 값으로 화면이 무엇을 보여줄지 결정한다.

| status | stage | 의미 | 사람이 할 일 |
|---|---|---|---|
| running | research | AI가 후보(뉴스 또는 분할안)를 조사·제안 중 | 대기 |
| waiting_for_user | await_selection | 후보 준비됨 | 후보 선택 제출 |
| running | verify_storyboard | AI가 검증+스토리보드 작성 중 | 대기 |
| waiting_for_user | await_approval | 스토리보드 준비됨 | 승인 또는 수정 요청 |
| running | generate_images | AI가 카드별 이미지 생성 중 | 대기 |
| waiting_for_user | await_review | 카드 준비됨(카드별 성공/실패 표시) | 검수, 실패 카드 개별 재생성, 완료 |
| running | await_review | 카드 1장을 개별 재생성하는 중 | 대기 (검수 화면 그대로 유지) |
| completed | done | 전부 끝남 | ZIP 다운로드 |
| failed | (실패한 단계) | 복구 불가능한 오류 | 재시도 버튼 |

`waiting_for_user`는 오류가 아니라 정상 상태다 — 화면은 이 상태에서 다음 단계로 자동 진행하면 안 된다.

## 엔드포인트

| 메서드 | 경로 | 요청 | 응답 | 비고 |
|---|---|---|---|---|
| GET | `/topics` | — | `[{topic_id, display_name, selection_range, candidate_count_range, storyboard_card_range, input_mode, cta_card}]` | 화면이 이 값으로 입력 폼(원고 붙여넣기/URL 입력 필요 여부)을 동적으로 구성함 |
| POST | `/runs` | `{topic_id, source_text?, source_url?}` | `{run_id}` | `input_mode="source_text"`인 토픽은 `source_text` 필수. `cta_card=true`인 토픽은 `source_url`도 필수(없으면 400) |
| GET | `/runs/{id}` | — | 런 전체 상태(아래 스키마) | 폴링용. `status="running"`이면 프런트가 2초마다 다시 호출 |
| POST | `/runs/{id}/select` | `{candidate_ids: [...]}` | `{ok: true}` | 토픽의 `selection_range` 범위를 벗어나면 400. 현재 stage가 `await_selection`이 아니면 409 |
| POST | `/runs/{id}/review` | `{action: "approve"|"revise", notes?}` | `{ok: true}` | approve → 이미지 생성 시작. revise → 같은 세션을 이어 재작성 |
| POST | `/runs/{id}/retry` | — | `{ok: true}` | `status="failed"`인 런만 가능. 실패했던 단계부터 재시작 |
| POST | `/runs/{id}/regenerate_card` | `{card_number}` | `{ok: true}` | `await_review` 단계에서만. 해당 카드만 다시 생성, 나머지는 그대로 |
| POST | `/runs/{id}/finish` | — | `{ok: true}` | `await_review` → `completed` |
| GET | `/runs/{id}/download` | — | ZIP 파일(바이너리) | `status="completed"`인 런만 가능 |

## `GET /runs/{id}` 응답 스키마 (핵심 필드)

```
{
  "id": str,
  "topic_id": str,
  "status": "running" | "waiting_for_user" | "completed" | "failed",
  "stage": str,
  "source_text": str | null,       // 원고 입력형 토픽만 사용
  "source_url": str | null,        // cta_card 토픽만 사용
  "candidates": { "candidates": [...] } | null,
  "selected_candidates": [str] | null,
  "verification": {
    "verifications": [{candidate_id, confirmed_facts, unconfirmed_claims, evidence_url}],
    "storyboard": [{card_number, headline, body, image_role, source}],
    "caption": str,      // 선택 필드, 인스타 캡션
    "hashtags": [str]    // 선택 필드
  } | null,
  "images": [{card_number, headline, body, bg_path, final_path, status: "ok"|"failed", error}] | null,
  "error_message": str | null,
  "retry_count": int
}
```

## 사람이 결정하는 지점 (Project 2 설계 반영)

카드뉴스 실습에서 배운 "이미 입력한 조건은 다시 묻지 않고, 꼭 필요한 선택만 요청한다" 원칙을 그대로 지켰다.

| 지점 | 사람이 결정하는 것 | 다시 묻지 않는 것 |
|---|---|---|
| 런 생성 시 | 주제(topic) 선택, (원고형이면) 원고 텍스트와 URL 1회 입력 | 이후 단계에서 원고를 다시 붙여넣으라고 하지 않음(DB에 저장돼 재사용) |
| await_selection | 후보(뉴스 또는 분할안) 중 몇 개 선택 | 조사 기간·후보 개수 같은 내부 파라미터는 다시 안 물음(토픽 설정값 그대로) |
| await_approval | 스토리보드 승인 또는 수정 요청(자연어) | 승인 시 이미지 스타일을 다시 안 물음(토픽의 `image_style_guidance` 그대로) |
| await_review | 카드별 재생성 여부, 완료 여부 | 성공한 카드는 다시 만들라고 안 함(실패한 것만 개별 재생성) |
