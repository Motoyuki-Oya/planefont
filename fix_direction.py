import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.ttf')
glyf = font['glyf']
hmtx = font['hmtx']
os2 = font['OS/2']

ascender = os2.sTypoAscender   # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition # -125
thickness = 50

# Redraw combining marks with NEGATIVE X coordinates:
# From x = -1000 to x = 0 (leftward from current cursor)
# So it covers the character just typed!
mark_defs = [
    ('uni0305', ascender, ascender + thickness),
    ('uni0332', underline, underline + thickness),
    ('uni0336', strikeout, strikeout + thickness),
]

for name, y_min, y_max in mark_defs:
    pen = TTGlyphPen(glyf)
    pen.moveTo((-1000, y_min))
    pen.lineTo((0, y_min))
    pen.lineTo((0, y_max))
    pen.lineTo((-1000, y_max))
    pen.closePath()
    glyf.glyphs[name] = pen.glyph()
    hmtx.metrics[name] = (0, -1000)

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

print("Fixed combining marks to draw from -1000 to 0 (leftward)!")
