# 테스트에 쓴 프롬프트 모음

공통 설정: `runwayml/stable-diffusion-v1-5` + `lllyasviel/sd-controlnet-openpose`, `num_inference_steps=25`, `guidance_scale=7.5`, `seed=42`

## pose_01 → output_01
- **원본 포즈**: 나무 자세(Tree Pose) — 한 다리로 서고 반대 발은 무릎 옆에, 두 손은 가슴 앞에 모음
- **프롬프트**: `a warrior in bronze armor standing on a mountain cliff at sunrise, golden hour lighting, cinematic photography, epic fantasy style`
- **네거티브 프롬프트**: `low quality, blurry, bad anatomy, extra limbs, watermark`
- **결과**: 잘 됨 — 자세 구조(한 다리 지지, 반대 다리 접힘, 손 모음) 정확히 재현

## pose_02 → output_02
- **원본 포즈**: 삼각 자세(Triangle Pose) — 다리를 넓게 벌리고 몸을 옆으로 기울여 한 팔은 아래, 한 팔은 위로 뻗음
- **프롬프트**: `a dancer in a flowing red silk dress on a rainy city street at night, neon lights reflecting on wet pavement, cinematic photography`
- **네거티브 프롬프트**: `low quality, blurry, bad anatomy, extra limbs, watermark`
- **결과**: 잘 됨 — 몸의 기울기와 팔 각도(한쪽 위, 한쪽 아래)가 원본과 일치
