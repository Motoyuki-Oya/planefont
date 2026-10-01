import io
import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import uharfbuzz as hb

# 1. Load original font
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

for tag in ['gvar', 'HVAR', 'VVAR', 'MVAR', 'vhea', 'vmtx', 'BASE', 'STAT', 'avar', 'fvar', 'gasp', 'GSUB', 'GPOS']:
    if tag in font:
        del font[tag]

buf = io.BytesIO()
font.save(buf)
buf.seek(0)
font = TTFont(buf)

glyf = font['glyf']
hmtx = font['hmtx']
cmap = font.getBestCmap()
glyph_order = list(font.getGlyphOrder())
os2 = font['OS/2']

ascender = os2.sTypoAscender   # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition # -125
thickness = 50

mark_cps = {
    0x0305: ('uni0305', ascender, 'overline'),
    0x0332: ('uni0332', underline, 'underline'),
    0x0336: ('uni0336', strikeout, 'strike'),
}

for cp, (m_name, _, _) in mark_cps.items():
    pen = TTGlyphPen(glyf)
    glyf.glyphs[m_name] = pen.glyph() # empty glyph
    hmtx.metrics[m_name] = (0, 0)
    if m_name not in glyph_order:
        glyph_order.append(m_name)
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = m_name

fea_rules = []

for char in all_text:
    cp = ord(char)
    base_gn = cmap.get(cp)
    if not base_gn:
        continue
    width, lsb = hmtx.metrics[base_gn]
    orig_glyph = glyf[base_gn]

    for m_cp, (m_name, line_y, line_tag) in mark_cps.items():
        lig_name = f"{base_gn}_{line_tag}"
        
        pen = TTGlyphPen(glyf)
        orig_glyph.draw(pen, glyf)
        
        # Horizontal line spanning EXACTLY 0 to width!
        pen.moveTo((0, line_y))
        pen.lineTo((width, line_y))
        pen.lineTo((width, line_y + thickness))
        pen.lineTo((0, line_y + thickness))
        pen.closePath()
        
        glyf.glyphs[lig_name] = pen.glyph()
        hmtx.metrics[lig_name] = (width, lsb)
        if lig_name not in glyph_order:
            glyph_order.append(lig_name)
            
        fea_rules.append(f"    sub {base_gn} {m_name} by {lig_name};")

# Synchronize font glyphOrder
font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# Compile OpenType features directly into this font
fea_code = f"""
languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem kana dflt;
languagesystem hani dflt;

feature ccmp {{
    lookup COMBINING_LINES {{
{chr(10).join(fea_rules)}
    }} COMBINING_LINES;
}} ccmp;
"""

addOpenTypeFeaturesFromString(font, fea_code)

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneSans.woff2')

# Test shaping immediately with HarfBuzz
with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
hb_font = hb.Font(face)

for test_str in ["H\u0305e\u0305l\u0305l\u0305o\u0305 W\u0305o\u0305r\u0305l\u0305d\u0305", "平\u0305均\u0305値\u0305　あ\u0305い\u0305う\u0305え\u0305お\u0305", "削\u0336除\u0336済\u0336み\u0336テ\u0336キ\u0336ス\u0336ト\u0336ー\u0336"]:
    buf = hb.Buffer()
    buf.add_str(test_str)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, {"ccmp": True})
    
    print(f"\n--- Shaped: {test_str} ---")
    out = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = hb_font.glyph_to_string(info.codepoint)
        out.append(f"{name}(adv={pos.x_advance})")
    print(" ".join(out))

# Update preview.html
woff2_b64 = base64.b64encode(fdata).decode('ascii')
with open('/mnt/c/workspace/planefont/preview.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
new_src = f"url('data:font/woff2;charset=utf-8;base64,{woff2_b64}') format('woff2')"
html = re.sub(r"url\([^)]+\)\s*format\('[^']+'\)", new_src, html)

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("\nSuccessfully compiled ccmp ligatures and updated preview.html!")
