"""Preview a non-invasive English UI layer over a Doubao Work screenshot."""
from __future__ import annotations

import argparse
import json
import pathlib
import re

from PIL import Image, ImageDraw, ImageFont
from rapidocr import RapidOCR


HAN = re.compile('[\u4e00-\u9fff]')
FONT_REGULAR = pathlib.Path(r'C:\Windows\Fonts\segoeui.ttf')
FONT_BOLD = pathlib.Path(r'C:\Windows\Fonts\segoeuib.ttf')


def text_rows(image: Image.Image, engine: RapidOCR):
    result = engine(image)
    if result.txts is None:
        return []
    rows = []
    for text, box, score in zip(result.txts, result.boxes, result.scores):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        rows.append((text, (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))), float(score)))
    return rows


def translate_screenshot(image: Image.Image, terms: dict[str, str], engine=None):
    engine = engine or RapidOCR()
    rows = text_rows(image, engine)
    if image.width > 1200:
        left_crop = image.crop((0, 45, 360, 335)).resize((720, 580))
        for text, (x1, y1, x2, y2), score in text_rows(left_crop, engine):
            rows.append((text, (x1//2, y1//2+45, x2//2, y2//2+45), score))
        left = int(image.width * .815)
        crop = image.crop((left, 45, image.width, image.height))
        for text, (x1, y1, x2, y2), score in text_rows(crop, engine):
            rows.append((text, (x1+left, y1+45, x2+left, y2+45), score))
    overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    matched = []
    seen = set()
    for text, box, score in rows:
        key = text.strip().replace('·', ' · ')
        translated = terms.get(text.strip()) or terms.get(key)
        x1, y1, x2, y2 = box
        if x1 > image.width*.90 and y1 < image.height*.12 and '新建' in text:
            translated = terms.get('新建')
            x1 += 18
        if y1 > image.height*.90 and x1 > image.width*.28:
            # The compact composer toolbar interleaves icons and text; leave it intact.
            continue
        if not translated or not HAN.search(text):
            continue
        unique = (text, round(x1/30), round(y1/15))
        if unique in seen:
            continue
        seen.add(unique)
        # User text inside chats and files is left intact; the phrase map controls scope.
        headline = (x1 > image.width*.35 and y1 < image.height*.58 and y2-y1 >= 34)
        size = max(12, min(40, round((y2-y1) * (.90 if headline else .79))))
        font_path = FONT_BOLD if headline else FONT_REGULAR
        limit = image.width-14 if x1 > image.width*.815 else (image.width*.8 if x1 > 350 else image.width*.235)
        max_width = max(50, int(limit-x1))
        while size > 11:
            font = ImageFont.truetype(str(font_path), size)
            length = draw.textlength(translated, font=font)
            if length <= max_width:
                break
            size -= 1
        width = max(x2-x1+8, int(length)+9)
        edge_x = max(0, x1-5)
        edge_y = max(0, y1-5)
        bg = image.getpixel((edge_x, edge_y))[:3]
        opacity = 255
        patch_rect = (x1-2, y1-3, min(image.width, x1+width), y2+4)
        draw.rectangle(patch_rect, fill=(*bg, opacity))
        fg = (26, 26, 26, 255) if not (score < .6) else (60, 60, 60, 255)
        if y1 < image.height*.55 and x1 < 90 and text in {'草稿', '项目', '最近'}:
            fg = (130, 130, 130, 255)
        draw.text((x1, y1-4), translated, font=font, fill=fg)
        matched.append({'source': text, 'translation': translated, 'box': box, 'patch_rect': patch_rect})
    return overlay, matched


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=pathlib.Path)
    parser.add_argument('terms', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    image = Image.open(args.image).convert('RGB')
    terms = json.loads(args.terms.read_text(encoding='utf-8'))
    overlay, matched = translate_screenshot(image, terms)
    Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB').save(args.output)
    print(json.dumps({'translated': len(matched), 'terms': [item['source'] for item in matched]}, ensure_ascii=True))


if __name__ == '__main__':
    main()
