# AI 모델 선정 근거 & 실험 프롬프트

## 모델 선정

| 후보 | 실행 위치 | 비고 |
|:---|:---|:---|
| **Stable Diffusion 1.5 + ControlNet Pose (`lllyasviel/sd-controlnet-openpose`)** ✅ 선택 | Colab 무료 T4 | [pose-image-tool](../pose-image-tool)에서 이미 검증됨 — 참조 포즈를 그대로 재현하는 것을 두 사례로 확인. ControlNet을 처음 만든 곳이 공개한 조합이라 신뢰도가 높고, T4에서 여유 있게 동작 |
| FLUX.2-klein (N017 강의 기본 모델) | Colab 무료 T4 | ControlNet과 함께 쓰면 무료 T4에서 메모리가 빠듯함(pose-image-tool README에서 이미 확인한 이유와 동일) → 후보에서 제외 |
| SDXL + ControlNet | Colab 무료 T4 | 품질은 더 좋을 수 있으나 모델 용량이 커 무료 T4에서 두 파이프라인(조건 A/B)을 동시에 굴리기 부담스러움 → 이번 PoC 스코프(포즈 재현 여부 비교)에는 SD1.5로 충분 |

**최종 선택 이유를 한 줄로**: 이미 같은 도메인 문제(포즈 고정)에서 검증된 조합을 그대로 재사용하고, 새로 검증해야 할 변수(웹툰 도메인에서도 통하는가·조건 A 대비 개선되는가)에만 실험을 집중한다.

## 조건 A / B 구성 방식

같은 베이스 체크포인트(`runwayml/stable-diffusion-v1-5`)에서 **컴포넌트를 공유**해 두 파이프라인을 만든다.

- **조건 A**: `StableDiffusionPipeline` — 텍스트 프롬프트만, ControlNet 없음 (현재 방식 시뮬레이션)
- **조건 B**: `StableDiffusionControlNetPipeline` — 같은 텍스트 프롬프트 + 포즈 스켈레톤 (개선안)

같은 `unet`·`vae`·`text_encoder`·`scheduler`·시드를 공유하므로, 두 결과의 차이는 **오직 "포즈 조건을 줬는가"** 하나에서만 발생한다 — PoC 비교의 공정성을 위한 설계.

## 실험 세트 3개

| 세트 | 참조 포즈 사진 | 포즈 설명 | 장면(공통 프롬프트) |
|:--:|:---|:---|:---|
| **1** | `pose_01.jpg` (재사용) | 나무 자세 — 한 다리로 서고 반대 발은 무릎 옆, 두 손은 가슴 앞에 모음 | 산속 사원 마당에서 한 발로 서서 기를 모으는 수련 장면 |
| **2** | `pose_02.jpg` (재사용) | 삼각 자세 — 다리를 넓게 벌리고 몸을 옆으로 기울여 한 팔은 위·한 팔은 아래 | 위기의 순간, 몸을 젖히며 한 손으로 공격을 막고 반격을 준비하는 액션 장면 |
| **3** | `pose_03.jpg` (신규 촬영 필요) | 무릎 꿇고 두 팔을 하늘로 향해 뻗는 절규 자세 | 큰 상실을 겪고 무너져 내리는 감정적인 장면 (빗속 절규) |

> **세트 3은 새로 촬영해야 합니다.** 직접 무릎을 꿇고 두 팔을 위로 뻗은 자세를 사진 한 장 찍어 `samples/pose_03.jpg`로 저장한 뒤 Colab에 업로드하면 됩니다. (본인이 배경·조명 신경 쓸 필요 없이, 관절 위치만 정확히 나오면 됩니다 — pose_01·02와 같은 방식)

## 프롬프트 (공통 — 조건 A·B에 동일하게 사용, `SEED=42` 동일)

**세트 1**
```
prompt: a young swordsman in traditional training robes standing in a quiet mountain
temple courtyard at dawn, meditative atmosphere, Korean webtoon illustration style,
clean digital linework, soft cel shading, dramatic backlight
negative: low quality, blurry, bad anatomy, extra limbs, watermark, photo, 3d render
```

**세트 2**
```
prompt: a determined heroine in a flowing battle cloak, leaning to the side while
blocking an incoming attack, dynamic action pose, dramatic lighting, Korean webtoon
illustration style, bold linework, vivid colors
negative: low quality, blurry, bad anatomy, extra limbs, watermark, photo, 3d render
```

**세트 3**
```
prompt: a heartbroken protagonist kneeling on the ground in the rain, arms raised
toward the sky in anguish, emotional webtoon panel, dramatic chiaroscuro lighting,
Korean manhwa illustration style
negative: low quality, blurry, bad anatomy, extra limbs, watermark, photo, 3d render
```

## 예상되는 한계 (미리 적어두는 이유 — PoC는 실패도 기록해야 함)

- SD1.5 기본 체크포인트는 실사 사진 위주로 학습되어 있어, "webtoon style" 문구를 넣어도 완전한 웹툰 선화·셀 셰이딩까지는 재현하지 못할 수 있다 (포즈 재현 여부와는 별개 문제로 구분해서 기록할 것).
- 조건 A도 우연히 비슷한 자세로 나올 가능성이 있다(특히 흔한 자세일 때) — 그런 경우는 "조건 B의 우위가 뚜렷하지 않은 사례"로 그대로 기록한다.
