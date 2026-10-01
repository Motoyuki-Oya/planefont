import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables import otTables

# 1. Load original font
font = TTFont('/tmp/NotoSansJP-Regular.ttf')

# ALL preview text characters
sample_text = (
    "Hello World"
    "平均値あいうえお"
    "下線テスト"
    "削除済みテキストー"
    " "
    "　"
)
sample_cps = set(ord(c) for c in sample_text)
sample_cps.update([0x0305, 0x0332, 0x0336])

options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=sample_cps)
subsetter.subset(font)

# Remove ONLY tables that trigger OTS rejection (do NOT remove GPOS!)
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

# Exact mark definitions from make_verified.py (leftward drawing)
mark_defs = [
    (0x0305, 'uni0305', ascender, ascender + thickness),
    (0x0332, 'uni0332', underline, underline + thickness),
    (0x0336, 'uni0336', strikeout, strikeout + thickness),
]

glyph_order = font.getGlyphOrder()
for cp, name, y_min, y_max in mark_defs:
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
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = name

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# GDEF with Mark = 3
if 'GDEF' not in font:
    from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
    font['GDEF'] = table_G_D_E_F_()
    font['GDEF'].table = otTables.GDEF()
    font['GDEF'].table.Version = 0x00010000

gdef = font['GDEF'].table
gdef.GlyphClassDef = otTables.GlyphClassDef()
classes = {}
mark_names = {'uni0305', 'uni0332', 'uni0336'}
for gn in font.getGlyphOrder():
    if gn in mark_names:
        classes[gn] = 3
    elif gn != '.notdef':
        classes[gn] = 1
gdef.GlyphClassDef.classDefs = classes

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

print("Restored exact 20:42 working pipeline with all characters included!")
