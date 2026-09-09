"""배경 이미지 위에 헤드라인·본문을 별도 텍스트 레이어로 합성한다 (N034 강의의
"텍스트 분리 편집" 원칙 — 이미지 생성 모델은 절대 글자를 넣지 않고, 배치는 여기서
로컬로 처리한다). OpenAI 호출이 전혀 없는 순수 함수라 오프라인으로 단위 테스트할 수
있다."""

import io

import qrcode
from PIL import Image, ImageDraw, ImageFont

CARD_W = 1080
CARD_H = 1350

FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REGULAR = r"C:\Windows\Fonts\malgun.ttf"

MARGIN = 60
HEADLINE_SIZE = 56
BODY_SIZE = 34
HEADLINE_LINE_HEIGHT = 66
BODY_LINE_HEIGHT = 44

CTA_BG_COLOR = (247, 243, 236)
CTA_TEXT_COLOR = (40, 34, 26)
CTA_MUTED_COLOR = (120, 110, 95)
CTA_URL_SIZE = 30


def _cover_resize_crop(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = round(src_w * scale), round(src_h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for w in words:
        candidate = (current + " " + w).strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
            current = ""
        if draw.textlength(w, font=font) <= max_width:
            current = w
            continue
        # 한 단어 자체가 너무 길면 글자 단위로 쪼갠다 (긴 URL/영단어 등 예외 상황 대비)
        chunk = ""
        for ch in w:
            if draw.textlength(chunk + ch, font=font) <= max_width:
                chunk += ch
            else:
                lines.append(chunk)
                chunk = ch
        current = chunk
    if current:
        lines.append(current)
    return lines


def compose_card(bg_bytes: bytes, headline: str, body: str, out_path: str) -> None:
    img = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    img = _cover_resize_crop(img, CARD_W, CARD_H).convert("RGBA")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    max_text_width = CARD_W - 2 * MARGIN
    headline_font = ImageFont.truetype(FONT_BOLD, HEADLINE_SIZE)
    body_font = ImageFont.truetype(FONT_REGULAR, BODY_SIZE)

    headline_lines = _wrap_text(draw, headline, headline_font, max_text_width)
    body_lines = _wrap_text(draw, body, body_font, max_text_width)

    text_block_height = (
        len(headline_lines) * HEADLINE_LINE_HEIGHT
        + 20
        + len(body_lines) * BODY_LINE_HEIGHT
        + MARGIN
    )
    box_top = max(CARD_H - text_block_height, int(CARD_H * 0.5))

    # 하단에 투명→반투명 검정 그라데이션을 깔아 흰 글자가 어떤 배경에서도 읽히게 한다.
    fade_height = CARD_H - box_top
    for y in range(box_top, CARD_H):
        alpha = int(190 * (y - box_top) / max(fade_height, 1))
        draw.line([(0, y), (CARD_W, y)], fill=(0, 0, 0, min(alpha, 190)))

    y = box_top + MARGIN * 0.5
    for line in headline_lines:
        draw.text((MARGIN, y), line, font=headline_font, fill=(255, 255, 255, 255))
        y += HEADLINE_LINE_HEIGHT
    y += 14
    for line in body_lines:
        draw.text((MARGIN, y), line, font=body_font, fill=(235, 235, 235, 255))
        y += BODY_LINE_HEIGHT

    composed = Image.alpha_composite(img, overlay).convert("RGB")
    composed.save(out_path, format="PNG")


def compose_cta_card(headline: str, body: str, url: str, out_path: str) -> None:
    """마지막 카드를 QR코드+URL 안내 카드로 만든다. 사진 배경이 필요 없는 순수 텍스트+QR
    카드라 OpenAI 호출 없이 로컬에서만 만든다(DJ 체크리스트 3번: 필요한 만큼만 쓴다)."""
    img = Image.new("RGB", (CARD_W, CARD_H), CTA_BG_COLOR)
    draw = ImageDraw.Draw(img)

    max_text_width = CARD_W - 2 * MARGIN
    headline_font = ImageFont.truetype(FONT_BOLD, HEADLINE_SIZE)
    body_font = ImageFont.truetype(FONT_REGULAR, BODY_SIZE)
    url_font = ImageFont.truetype(FONT_REGULAR, CTA_URL_SIZE)

    def draw_centered_lines(lines: list[str], font: ImageFont.FreeTypeFont, y: float, line_height: float, fill) -> float:
        for line in lines:
            w = draw.textlength(line, font=font)
            draw.text(((CARD_W - w) / 2, y), line, font=font, fill=fill)
            y += line_height
        return y

    headline_lines = _wrap_text(draw, headline, headline_font, max_text_width)
    body_lines = _wrap_text(draw, body, body_font, max_text_width)

    y = MARGIN * 1.5
    y = draw_centered_lines(headline_lines, headline_font, y, HEADLINE_LINE_HEIGHT, CTA_TEXT_COLOR)
    y += 20
    y = draw_centered_lines(body_lines, body_font, y, BODY_LINE_HEIGHT, CTA_TEXT_COLOR)

    qr_img = qrcode.make(url, box_size=10, border=2).convert("RGB")
    qr_size = 480
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    qr_top = int(CARD_H * 0.42)
    img.paste(qr_img, ((CARD_W - qr_size) // 2, qr_top))

    url_lines = _wrap_text(draw, url, url_font, max_text_width)
    draw_centered_lines(url_lines, url_font, qr_top + qr_size + 30, CTA_URL_SIZE + 10, CTA_MUTED_COLOR)

    img.save(out_path, format="PNG")
