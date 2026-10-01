import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options

font = TTFont('/tmp/NotoSansJP-Regular.ttf')

all_text = "Hello World平均値あいうえお下線テスト削除済みテキストー"
all_cps = set(ord(c) for c in all_text)
all_cps.update([0x0305, 0x0332, 0x0336, 0x0020, 0x3000])

options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=all_cps)
subsetter.subset(font)

for tag in ['gvar', 'HVAR', 'VVAR', 'MVAR', 'vhea', 'vmtx', 'BASE', 'STAT', 'avar', 'fvar', 'gasp']:
    if tag in font:
        del font[tag]

import io
buf = io.BytesIO()
font.save(buf)
buf.seek(0)
font = TTFont(buf)

glyf = font['glyf']
hmtx = font['hmtx']
os2 = font['OS/2']

ascender = os2.sTypoAscender   # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition # -125
thickness = 50

# In proportional font, character widths range from 250 (l) to 1000 (CJK).
# To make lines connect with NO GAPS, the line must be at least as wide as the character.
# Length = 1000 covers all characters from width 0 to 1000!
# By drawing from -1000 to 0, adjacent marks overlap smoothly and form a 100% continuous line.

mark_defs = [
    ('uni0305', ascender, ascender + thickness),
    ('uni0332', underline, underline + thickness),
    ('uni0336', strikeout, strikeout + thickness),
]

glyph_order = font.getGlyphOrder()
for name, y_min, y_max in mark_defs:
    pen = TTGlyphPen(glyf)
    pen.moveTo((-1000, y_min))
    pen.lineTo((0, y_min))
    pen.lineTo((0, y_max))
    pen.lineTo((-1000, y_max))
    pen.closePath()
    glyf.glyphs[name] = pen.glyph()
    hmtx.metrics[name] = (0, -1000)
    if name not in glyph_order:
        glyph_order.append(name)

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneSans.woff2')

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    woff2_b64 = base64.b64encode(f.read()).decode('ascii')

with open('/mnt/c/workspace/planefont/preview.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
new_src = f"url('data:font/woff2;charset=utf-8;base64,{woff2_b64}') format('woff2')"
html = re.sub(r"url\([^)]+\)\s*format\('[^']+'\)", new_src, html)

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Generated continuous line font and updated preview.html!")
