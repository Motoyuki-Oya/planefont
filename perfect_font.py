import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables import otTables

# 1. Load original font
font = TTFont('/tmp/NotoSansJP-Regular.ttf')

# 2. Subset with ALL required characters (including 済, み, キ and full text)
sample_text = (
    "Hello World"
    "平均値あいうえお"
    "下線テスト"
    "削除済みテキストー"
    "0123456789"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
)
sample_cps = set(ord(c) for c in sample_text)
sample_cps.update([0x0305, 0x0332, 0x0336, 0x0020, 0x3000])

options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=sample_cps)
subsetter.subset(font)

# Remove variable tables
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

# We create TWO variants for each combining mark:
# 1. Default (halfwidth): from x = -500 to x = 0 (for Latin / halfwidth)
# 2. Wide: from x = -1000 to x = 0 (for CJK / fullwidth)

marks = [
    # (cp, default_name, wide_name, y_min, y_max)
    (0x0305, 'uni0305', 'uni0305.wide', ascender, ascender + thickness),
    (0x0332, 'uni0332', 'uni0332.wide', underline, underline + thickness),
    (0x0336, 'uni0336', 'uni0336.wide', strikeout, strikeout + thickness),
]

for cp, name_half, name_wide, y_min, y_max in marks:
    # Halfwidth: [-500, 0]
    pen = TTGlyphPen(glyf)
    pen.moveTo((-500, y_min))
    pen.lineTo((0, y_min))
    pen.lineTo((0, y_max))
    pen.lineTo((-500, y_max))
    pen.closePath()
    glyf.glyphs[name_half] = pen.glyph()
    hmtx.metrics[name_half] = (0, -500)
    if name_half not in glyph_order:
        glyph_order.append(name_half)

    # Wide: [-1000, 0]
    pen_w = TTGlyphPen(glyf)
    pen_w.moveTo((-1000, y_min))
    pen_w.lineTo((0, y_min))
    pen_w.lineTo((0, y_max))
    pen_w.lineTo((-1000, y_max))
    pen_w.closePath()
    glyf.glyphs[name_wide] = pen_w.glyph()
    hmtx.metrics[name_wide] = (0, -1000)
    if name_wide not in glyph_order:
        glyph_order.append(name_wide)

    # Map Unicode to default (halfwidth)
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = name_half

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# Identify fullwidth (width >= 800) vs halfwidth glyphs
fullwidth_glyphs = []
for gn in glyph_order:
    w, _ = hmtx.metrics.get(gn, (0, 0))
    if w >= 800 and not gn.startswith('uni03'):
        fullwidth_glyphs.append(gn)

print(f"Identified {len(fullwidth_glyphs)} fullwidth glyphs for wide mark substitution")

# Add GSUB calt: When preceded by a fullwidth glyph, substitute default mark with .wide mark
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

# Lookup 1: Single substitution (half -> wide)
sub_subtable = otTables.SingleSubst()
sub_subtable.mapping = {
    'uni0305': 'uni0305.wide',
    'uni0332': 'uni0332.wide',
    'uni0336': 'uni0336.wide',
}
sub_lookup = otTables.Lookup()
sub_lookup.LookupType = 1 # SingleSubst
sub_lookup.LookupFlag = 0
sub_lookup.SubTable = [sub_subtable]
sub_lookup.SubTableCount = 1
sub_lookup_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(sub_lookup)

# Lookup 2: Chained Contextual Substitution
# Context: [Backtrack: fullwidth_glyph] [Input: mark_half] -> apply sub_lookup
chain_sub = otTables.ChainContextSubst()
chain_sub.Format = 3
chain_sub.BacktrackCoverage = [otTables.Coverage()]
chain_sub.BacktrackCoverage[0].glyphs = fullwidth_glyphs
chain_sub.BacktrackGlyphCount = 1

chain_sub.InputCoverage = [otTables.Coverage()]
chain_sub.InputCoverage[0].glyphs = ['uni0305', 'uni0332', 'uni0336']
chain_sub.InputGlyphCount = 1

chain_sub.LookAheadCoverage = []
chain_sub.LookAheadGlyphCount = 0

sub_rec = otTables.SubstLookupRecord()
sub_rec.SequenceIndex = 0
sub_rec.LookupListIndex = sub_lookup_idx
chain_sub.SubstLookupRecord = [sub_rec]
chain_sub.SubstCount = 1

chain_lookup = otTables.Lookup()
chain_lookup.LookupType = 6 # Chained Contextual
chain_lookup.LookupFlag = 0
chain_lookup.SubTable = [chain_sub]
chain_lookup.SubTableCount = 1
chain_lookup_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(chain_lookup)

# Register in 'calt' and 'ccmp' for all scripts
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
    
    # Ensure DFLT script exists
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

register_feature('calt', chain_lookup_idx)
register_feature('ccmp', chain_lookup_idx)

# Ensure clean GDEF
if 'GDEF' not in font:
    from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
    font['GDEF'] = table_G_D_E_F_()
    font['GDEF'].table = otTables.GDEF()
    font['GDEF'].table.Version = 0x00010000

gdef = font['GDEF'].table
gdef.GlyphClassDef = otTables.GlyphClassDef()
classes = {}
all_marks = {'uni0305', 'uni0305.wide', 'uni0332', 'uni0332.wide', 'uni0336', 'uni0336.wide'}
for gn in font.getGlyphOrder():
    if gn in all_marks:
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

print("Generated perfected PlaneSans.woff2 with contextual half/wide marks!")
