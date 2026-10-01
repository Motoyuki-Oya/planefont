import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables import otTables

# 1. Load original font
font = TTFont('/tmp/NotoSansJP-Regular.ttf')

# All preview characters
all_text = "Hello World平均値あいうえお下線テスト削除済みテキストー"
all_cps = set(ord(c) for c in all_text)
all_cps.update([0x0305, 0x0332, 0x0336, 0x0020, 0x3000])

options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=all_cps)
subsetter.subset(font)

# Remove problematic tables
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
cmap = font.getBestCmap()
glyph_order = font.getGlyphOrder()
os2 = font['OS/2']

ascender = os2.sTypoAscender   # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition # -125
thickness = 50

# Ensure dummy combining marks in cmap
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

# Generate true gapless ligature glyphs for every character in sample text
ligatures = [] # (base_name, mark_name, lig_name)

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
            
        ligatures.append((base_gn, m_name, lig_name))

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# Build GSUB LigatureSubst with VALID Coverage table
gsub = font['GSUB'].table

subtable = otTables.LigatureSubst()
subtable.ligatures = {}

for base_gn, m_name, lig_name in ligatures:
    lig = otTables.Ligature()
    lig.Component = [m_name]
    lig.LigGlyph = lig_name
    if base_gn not in subtable.ligatures:
        subtable.ligatures[base_gn] = []
    subtable.ligatures[base_gn].append(lig)

# Explicitly set Coverage table!
subtable.Coverage = otTables.Coverage()
subtable.Coverage.glyphs = list(subtable.ligatures.keys())

lookup = otTables.Lookup()
lookup.LookupType = 4
lookup.LookupFlag = 0
lookup.SubTable = [subtable]
lookup.SubTableCount = 1

# Put lookup at index 0 for top priority
gsub.LookupList.Lookup.insert(0, lookup)

# Register feature 0 for all scripts under 'ccmp', 'liga', 'calt'
def add_feature(tag, l_idx):
    feat = otTables.Feature()
    feat.FeatureParams = None
    feat.LookupListIndex = [l_idx]
    feat.LookupCount = 1
    fr = otTables.FeatureRecord()
    fr.FeatureTag = tag
    fr.Feature = feat
    f_idx = len(gsub.FeatureList.FeatureRecord)
    gsub.FeatureList.FeatureRecord.append(fr)

    for sr in gsub.ScriptList.ScriptRecord:
        if sr.Script.DefaultLangSys:
            if sr.Script.DefaultLangSys.FeatureIndex is None:
                sr.Script.DefaultLangSys.FeatureIndex = []
            sr.Script.DefaultLangSys.FeatureIndex.insert(0, f_idx)
            sr.Script.DefaultLangSys.FeatureCount = len(sr.Script.DefaultLangSys.FeatureIndex)
        for lsr in (sr.Script.LangSysRecord or []):
            if lsr.LangSys.FeatureIndex is None:
                lsr.LangSys.FeatureIndex = []
            lsr.LangSys.FeatureIndex.insert(0, f_idx)
            lsr.LangSys.FeatureCount = len(lsr.LangSys.FeatureIndex)

add_feature('ccmp', 0)
add_feature('liga', 0)
add_feature('calt', 0)

# Save WOFF2
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

print("Deploy complete: PlaneSans.woff2 updated in preview.html with Coverage-fixed ligatures!")
