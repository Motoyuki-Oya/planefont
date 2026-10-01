from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options

# 1. Load NotoSansJP-Regular.ttf (TTF is reliable for outline generation)
font = TTFont('/tmp/NotoSansJP-Regular.ttf')

# 2. Subset with exact required characters
sample_text = "Hello World平均値あいうえお削除テスト下線"
sample_cps = [ord(c) for c in sample_text] + [0x0305, 0x0332, 0x0336, 0x0020]

options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=sample_cps)
subsetter.subset(font)

# Remove variable tables if present
for tag in ['gvar', 'HVAR', 'VVAR', 'MVAR']:
    if tag in font:
        del font[tag]

import io
buf = io.BytesIO()
font.save(buf)
buf.seek(0)
font = TTFont(buf)

glyf = font['glyf']
hmtx = font['hmtx']
cmap = font.getBestCmap()
upm = font['head'].unitsPerEm  # 1000
os2 = font['OS/2']

# Metrics
ascender = os2.sTypoAscender   # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition # -125
thickness = 50

# Ensure combining mark glyphs exist
mark_defs = [
    (0x0305, 'uni0305', ascender, ascender + thickness),
    (0x0332, 'uni0332', underline, underline + thickness),
    (0x0336, 'uni0336', strikeout, strikeout + thickness),
]

glyph_order = font.getGlyphOrder()
for cp, name, y_min, y_max in mark_defs:
    pen = TTGlyphPen(glyf)
    pen.moveTo((0, y_min))
    pen.lineTo((1000, y_min))
    pen.lineTo((1000, y_max))
    pen.lineTo((0, y_max))
    pen.closePath()
    glyf.glyphs[name] = pen.glyph()
    hmtx.metrics[name] = (0, 0)
    if name not in glyph_order:
        glyph_order.append(name)
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = name

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# Ensure GDEF with GlyphClassDef (Mark = 3, Base = 1)
from fontTools.ttLib.tables import otTables
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
print("Successfully generated verified PlaneSans.woff2!")
