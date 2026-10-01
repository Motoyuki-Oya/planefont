import copy
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables
from fontTools.pens.ttGlyphPen import TTGlyphPen

font = TTFont('/tmp/NotoSansJP-Regular.ttf')

# Subset first
from fontTools.subset import Subsetter, Options
options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)
subsetter.populate(unicodes=[ord(c) for c in "Hello World平均値あいうえお"] + [0x0305, 0x0332, 0x0336])
subsetter.subset(font)

# Remove variable font tables
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
glyph_order = font.getGlyphOrder()

# Let's test GSUB ligature for U+0305 (overline)
# For each base glyph, create base_overline glyph:
# copy original glyph contours + add horizontal line from x=0 to x=advanceWidth at y=880
overline_y = 880
line_height = 50

ligatures_to_add = [] # (base_name, mark_name, lig_name)

mark_gn = cmap.get(0x0305)
if not mark_gn:
    mark_gn = 'uni0305'
    from fontTools.ttLib.tables._g_l_y_f import Glyph
    glyf.glyphs[mark_gn] = Glyph()
    hmtx.metrics[mark_gn] = (0, 0)
    glyph_order.append(mark_gn)
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[0x0305] = mark_gn

for char in "Hello World平均値あいうえお":
    cp = ord(char)
    base_gn = cmap.get(cp)
    if not base_gn:
        continue
    width, lsb = hmtx.metrics[base_gn]
    lig_name = f"{base_gn}_overline"
    
    # Draw original contours + overline rectangle
    pen = TTGlyphPen(glyf)
    orig_glyph = glyf[base_gn]
    orig_glyph.draw(pen, glyf)
    
    # Add overline rectangle: [0, overline_y] to [width, overline_y + line_height]
    pen.moveTo((0, overline_y))
    pen.lineTo((width, overline_y))
    pen.lineTo((width, overline_y + line_height))
    pen.lineTo((0, overline_y + line_height))
    pen.closePath()
    
    glyf.glyphs[lig_name] = pen.glyph()
    hmtx.metrics[lig_name] = (width, lsb)
    glyph_order.append(lig_name)
    ligatures_to_add.append((base_gn, mark_gn, lig_name))

font.setGlyphOrder(glyph_order)

# Add GSUB ligature lookup
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

# Create LigatureSubst subtable
subtable = otTables.LigatureSubst()
subtable.ligatures = {}
for base_gn, mark_gn, lig_name in ligatures_to_add:
    lig = otTables.Ligature()
    lig.Component = [mark_gn] # [base, mark] -> lig
    lig.LigGlyph = lig_name
    if base_gn not in subtable.ligatures:
        subtable.ligatures[base_gn] = []
    subtable.ligatures[base_gn].append(lig)

lookup = otTables.Lookup()
lookup.LookupType = 4 # Ligature
lookup.LookupFlag = 0
lookup.SubTable = [subtable]
lookup.SubTableCount = 1

lookup_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(lookup)

# Add to 'calt' and 'liga' and 'ccmp' features
for feat_tag in ['ccmp', 'liga', 'calt']:
    feat = otTables.Feature()
    feat.FeatureParams = None
    feat.LookupListIndex = [lookup_idx]
    feat.LookupCount = 1
    fr = otTables.FeatureRecord()
    fr.FeatureTag = feat_tag
    fr.Feature = feat
    feat_idx = len(gsub.FeatureList.FeatureRecord)
    gsub.FeatureList.FeatureRecord.append(fr)
    
    for sr in gsub.ScriptList.ScriptRecord:
        if sr.Script.DefaultLangSys:
            sr.Script.DefaultLangSys.FeatureIndex.append(feat_idx)
        for lsr in (sr.Script.LangSysRecord or []):
            lsr.LangSys.FeatureIndex.append(feat_idx)

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneSans-lig.woff2')
print("Saved PlaneSans-lig.woff2!")
