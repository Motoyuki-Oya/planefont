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

# Remove variable and vertical tables to pass sanitizer
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

# Ensure dummy combining marks in cmap so input text parses
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

# Now generate true ligature glyphs for EVERY base character:
# [base] + [mark] -> [base_with_line]
# The line spans exactly from x=0 to x=width of that specific base character!
# This guarantees 100% continuous, gapless, overhang-free lines!

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
        # Draw original character contours
        orig_glyph.draw(pen, glyf)
        
        # Draw horizontal line spanning EXACTLY 0 to width!
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

# Build GSUB LigatureSubst
if 'GSUB' not in font:
    from fontTools.ttLib.tables.G_S_U_B_ import table_G_S_U_B_
    font['GSUB'] = table_G_S_U_B_()
    font['GSUB'].table = otTables.GSUB()
    font['GSUB'].table.Version = 0x00010000
    font['GSUB'].table.ScriptList = otTables.ScriptList()
    font['GSUB'].table.ScriptList.ScriptRecord = []
    font['GSUB'].table.FeatureList = otTables.FeatureList()
    font['GSUB'].table.FeatureList.FeatureRecord = []
    font['GSUB'].table.LookupList = otTables.LookupList()
    font['GSUB'].table.LookupList.Lookup = []

gsub = font['GSUB'].table

# Create LigatureSubst table (Lookup Type 4)
subtable = otTables.LigatureSubst()
subtable.ligatures = {}

for base_gn, m_name, lig_name in ligatures:
    lig = otTables.Ligature()
    lig.Component = [m_name] # [base] followed by [mark]
    lig.LigGlyph = lig_name
    if base_gn not in subtable.ligatures:
        subtable.ligatures[base_gn] = []
    subtable.ligatures[base_gn].append(lig)

lookup = otTables.Lookup()
lookup.LookupType = 4 # Ligature substitution
lookup.LookupFlag = 0
lookup.SubTable = [subtable]
lookup.SubTableCount = 1

lookup_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(lookup)

# Register lookup under 'ccmp', 'liga', 'calt' for all scripts
def add_feature_to_all_scripts(tag, l_idx):
    feat = otTables.Feature()
    feat.FeatureParams = None
    feat.LookupListIndex = [l_idx]
    feat.LookupCount = 1
    fr = otTables.FeatureRecord()
    fr.FeatureTag = tag
    fr.Feature = feat
    f_idx = len(gsub.FeatureList.FeatureRecord)
    gsub.FeatureList.FeatureRecord.append(fr)

    if not gsub.ScriptList.ScriptRecord:
        sr = otTables.ScriptRecord()
        sr.ScriptTag = 'DFLT'
        sr.Script = otTables.Script()
        sr.Script.DefaultLangSys = otTables.LangSys()
        sr.Script.DefaultLangSys.ReqFeatureIndex = 0xFFFF
        sr.Script.DefaultLangSys.FeatureIndex = []
        sr.Script.LangSysRecord = []
        gsub.ScriptList.ScriptRecord.append(sr)

    for sr in gsub.ScriptList.ScriptRecord:
        if sr.Script.DefaultLangSys:
            if sr.Script.DefaultLangSys.FeatureIndex is None:
                sr.Script.DefaultLangSys.FeatureIndex = []
            sr.Script.DefaultLangSys.FeatureIndex.append(f_idx)
            sr.Script.DefaultLangSys.FeatureCount = len(sr.Script.DefaultLangSys.FeatureIndex)
        for lsr in (sr.Script.LangSysRecord or []):
            if lsr.LangSys.FeatureIndex is None:
                lsr.LangSys.FeatureIndex = []
            lsr.LangSys.FeatureIndex.append(f_idx)
            lsr.LangSys.FeatureCount = len(lsr.LangSys.FeatureIndex)

add_feature_to_all_scripts('ccmp', lookup_idx)
add_feature_to_all_scripts('liga', lookup_idx)
add_feature_to_all_scripts('calt', lookup_idx)

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

print("Generated true gapless ligature font PlaneSans.woff2 and updated preview.html!")
