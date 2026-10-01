import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables import otTables

# 1. Load font
font = TTFont('/tmp/NotoSansJP-Regular.ttf')

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

# Collect unique widths of all base characters in sample_text
# For each unique width, create a custom-fitted mark line from [-width, 0]
base_glyphs = {}
unique_widths = set()

for char in sample_text:
    cp = ord(char)
    gn = cmap.get(cp)
    if gn:
        w, lsb = hmtx.metrics[gn]
        base_glyphs[gn] = w
        unique_widths.add(w)

print(f"Unique character widths in text: {sorted(unique_widths)}")

# Create combining marks for each mark type and each width
# E.g. uni0305.w733 for width 733, drawn exactly from -733 to 0!
mark_types = [
    (0x0305, 'uni0305', ascender, 'overline'),
    (0x0332, 'uni0332', underline, 'underline'),
    (0x0336, 'uni0336', strikeout, 'strike'),
]

created_mark_names = set()

for w in unique_widths:
    for cp, default_name, y_pos, tag in mark_types:
        # Default mark is 1000 width
        if w == 1000:
            m_name = default_name
        else:
            m_name = f"{default_name}.w{w}"
        
        pen = TTGlyphPen(glyf)
        pen.moveTo((-w, y_pos))
        pen.lineTo((0, y_pos))
        pen.lineTo((0, y_pos + thickness))
        pen.lineTo((-w, y_pos + thickness))
        pen.closePath()
        
        glyf.glyphs[m_name] = pen.glyph()
        hmtx.metrics[m_name] = (0, -w)
        if m_name not in glyph_order:
            glyph_order.append(m_name)
        created_mark_names.add(m_name)

# Ensure default marks in cmap
for cp, default_name, _, _ in mark_types:
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = default_name

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# Build contextual substitution in GSUB:
# When base glyph with width W is followed by default mark,
# substitute default mark with the exact fitted mark for width W!

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

# Create SingleSubst lookups for each width < 1000
width_to_lookup_idx = {}

for w in unique_widths:
    if w == 1000:
        continue # default mark is already 1000
    
    sub_table = otTables.SingleSubst()
    sub_table.mapping = {}
    for cp, default_name, _, _ in mark_types:
        sub_table.mapping[default_name] = f"{default_name}.w{w}"
    
    l = otTables.Lookup()
    l.LookupType = 1 # SingleSubst
    l.LookupFlag = 0
    l.SubTable = [sub_table]
    l.SubTableCount = 1
    
    idx = len(gsub.LookupList.Lookup)
    gsub.LookupList.Lookup.append(l)
    width_to_lookup_idx[w] = idx

# Now create ChainContextSubst:
# Group base glyphs by width:
glyphs_by_width = {}
for gn, w in base_glyphs.items():
    glyphs_by_width.setdefault(w, []).append(gn)

chain_subtables = []
for w, b_glyphs in glyphs_by_width.items():
    if w == 1000:
        continue
    l_idx = width_to_lookup_idx[w]
    
    chain = otTables.ChainContextSubst()
    chain.Format = 3
    chain.BacktrackCoverage = [otTables.Coverage()]
    chain.BacktrackCoverage[0].glyphs = b_glyphs
    chain.BacktrackGlyphCount = 1
    
    chain.InputCoverage = [otTables.Coverage()]
    chain.InputCoverage[0].glyphs = ['uni0305', 'uni0332', 'uni0336']
    chain.InputGlyphCount = 1
    
    chain.LookAheadCoverage = []
    chain.LookAheadGlyphCount = 0
    
    rec = otTables.SubstLookupRecord()
    rec.SequenceIndex = 0
    rec.LookupListIndex = l_idx
    chain.SubstLookupRecord = [rec]
    chain.SubstCount = 1
    
    chain_subtables.append(chain)

main_chain_lookup = otTables.Lookup()
main_chain_lookup.LookupType = 6 # Chained contextual
main_chain_lookup.LookupFlag = 0
main_chain_lookup.SubTable = chain_subtables
main_chain_lookup.SubTableCount = len(chain_subtables)

main_chain_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(main_chain_lookup)

# Register main_chain_idx in 'calt' and 'ccmp' for all scripts
def register_feature(tag, l_idx):
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
            sr.Script.DefaultLangSys.FeatureIndex.insert(0, f_idx)
            sr.Script.DefaultLangSys.FeatureCount = len(sr.Script.DefaultLangSys.FeatureIndex)
        for lsr in (sr.Script.LangSysRecord or []):
            if lsr.LangSys.FeatureIndex is None:
                lsr.LangSys.FeatureIndex = []
            lsr.LangSys.FeatureIndex.insert(0, f_idx)
            lsr.LangSys.FeatureCount = len(lsr.LangSys.FeatureIndex)

register_feature('calt', main_chain_idx)
register_feature('ccmp', main_chain_idx)

# GDEF table with GlyphClassDef (Mark = 3) for ALL mark glyphs
if 'GDEF' not in font:
    from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
    font['GDEF'] = table_G_D_E_F_()
    font['GDEF'].table = otTables.GDEF()
    font['GDEF'].table.Version = 0x00010000

gdef = font['GDEF'].table
gdef.GlyphClassDef = otTables.GlyphClassDef()
classes = {}
for gn in font.getGlyphOrder():
    if gn in created_mark_names:
        classes[gn] = 3 # Mark glyph
    elif gn != '.notdef':
        classes[gn] = 1 # Base glyph
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

print("SUCCESS: Exact per-character-width contextual mark font generated and deployed!")
