import io
import time
import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib.tables._g_l_y_f import table__g_l_y_f
from fontTools.ttLib.tables._h_m_t_x import table__h_m_t_x
from fontTools.ttLib.tables._l_o_c_a import table__l_o_c_a
from fontTools.ttLib.tables._m_a_x_p import table__m_a_x_p
from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
from fontTools.ttLib.tables import otTables

t_start = time.time()
print("1. Loading LigaNotoSansMono (Programming ligatures)...")
src_mono = TTFont('/tmp/LigaNotoSansMono-Regular.otf')
mono_set = src_mono.getGlyphSet()
mono_hmtx = src_mono['hmtx']
mono_cmap = src_mono.getBestCmap()
mono_order = src_mono.getGlyphOrder()

print("2. Loading NotoSansMonoCJKjp (Japanese Monospace)...")
src_cjk = TTFont('/tmp/noto_mono/NotoSansMonoCJKjp-Regular.otf')
cjk_set = src_cjk.getGlyphSet()
cjk_hmtx = src_cjk['hmtx']
cjk_cmap = src_cjk.getBestCmap()

# Create target TrueType font based on LigaNoto (keeps OS/2, name, GSUB programming ligatures)
font = TTFont()
font.sfntVersion = '\x00\x01\x00\x00'
for tag in ['head', 'hhea', 'OS/2', 'post', 'cmap', 'name', 'GSUB']:
    if tag in src_mono:
        font[tag] = src_mono[tag]

# Initialize maxp table for TrueType format
maxp = table__m_a_x_p()
maxp.tableVersion = 0x00010000
for attr in ['maxPoints', 'maxContours', 'maxCompositePoints', 'maxCompositeContours',
             'maxZones', 'maxTwilightPoints', 'maxStorage', 'maxFunctionDefs',
             'maxInstructionDefs', 'maxStackElements', 'maxSizeOfInstructions',
             'maxComponentElements', 'maxComponentDepth']:
    setattr(maxp, attr, 0)
maxp.maxZones = 1
font['maxp'] = maxp

# Initialize glyf, hmtx, loca
glyf = table__g_l_y_f()
glyf.glyphs = {}
font['glyf'] = glyf

hmtx = table__h_m_t_x()
hmtx.metrics = {}
font['hmtx'] = hmtx

font['loca'] = table__l_o_c_a()

glyph_order = []

from fontTools.pens.cu2quPen import Cu2QuPen

# Copy all glyphs from LigaNotoSansMono (Latin + Programming Ligatures)
print("3. Converting LigaNoto glyphs to TrueType (cu2qu quadratic)...")
for gn in mono_order:
    pen = TTGlyphPen(None)
    cu2qu = Cu2QuPen(pen, max_err=1.0)
    mono_set[gn].draw(cu2qu)
    glyf.glyphs[gn] = pen.glyph()
    w, lsb = mono_hmtx.metrics.get(gn, (600, 0))
    hmtx.metrics[gn] = (w, lsb)
    glyph_order.append(gn)

# Merge Japanese characters from NotoSansMonoCJKjp
# Select comprehensive set: Hiragana, Katakana, Punctuation, Fullwidth symbols,
# Box drawing, Block elements, and common Kanji (covering all sample text + common CJK)
sample_jp_text = "Hello World 平均値あいうえお下線テスト削除済みテキストー、。！？（）「」"
extra_cps = set(ord(c) for c in sample_jp_text)

selected_cps = set()
for cp in cjk_cmap:
    if cp < 0x80:
        continue  # Keep all ASCII from LigaNotoSansMono for programming ligatures!
    if (0x3000 <= cp <= 0x33FF or 
        0xFF00 <= cp <= 0xFFEF or 
        0x2000 <= cp <= 0x27FF or
        0x4E00 <= cp <= 0x9FFF):
        selected_cps.add(cp)
    elif cp in extra_cps:
        selected_cps.add(cp)

print(f"4. Merging {len(selected_cps)} Japanese glyphs from NotoSansMonoCJKjp (Fullwidth 1200, cu2qu)...")

cjk_to_target = {}
for cp in selected_cps:
    cjk_gn = cjk_cmap[cp]
    if cjk_gn not in cjk_to_target:
        target_gn = f"jp_{cp:04X}"
        cjk_to_target[cjk_gn] = target_gn
        
        # Scale/center from 1000 to 1200 fullwidth:
        # Width 1200 = 600 * 2 (1:2 monospace ratio).
        # Source is 1000 wide, offset by +100 to center in 1200 box:
        orig_w, orig_lsb = cjk_hmtx.metrics.get(cjk_gn, (1000, 0))
        pen1200 = TTGlyphPen(None)
        cu2qu = Cu2QuPen(pen1200, max_err=1.0)
        tpen = TransformPen(cu2qu, (1, 0, 0, 1, 100, 0))
        cjk_set[cjk_gn].draw(tpen)
        
        glyf.glyphs[target_gn] = pen1200.glyph()
        hmtx.metrics[target_gn] = (1200, orig_lsb + 100)
        glyph_order.append(target_gn)
    else:
        target_gn = cjk_to_target[cjk_gn]
    
    # Register in cmap
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = target_gn

# 5. Add combining marks:
# Halfwidth line: [-600, 0] for Latin / code ligatures
# Fullwidth line: [-1200, 0] for Japanese
print("5. Adding continuous combining marks (Halfwidth 600 & Fullwidth 1200)...")
ascender = 880
strikeout = 325
underline = -125
thickness = 50

mark_configs = [
    (0x0305, 'uni0305', 'uni0305.wide', ascender),
    (0x0332, 'uni0332', 'uni0332.wide', underline),
    (0x0336, 'uni0336', 'uni0336.wide', strikeout),
]

fullwidth_glyphs = [gn for gn in glyph_order if hmtx.metrics.get(gn, (0, 0))[0] >= 1000 and not gn.startswith('uni03')]

for cp, name_half, name_wide, y_pos in mark_configs:
    # Halfwidth mark: [-600, 0]
    pen = TTGlyphPen(None)
    pen.moveTo((-600, y_pos))
    pen.lineTo((0, y_pos))
    pen.lineTo((0, y_pos + thickness))
    pen.lineTo((-600, y_pos + thickness))
    pen.closePath()
    glyf.glyphs[name_half] = pen.glyph()
    hmtx.metrics[name_half] = (0, -600)
    if name_half not in glyph_order:
        glyph_order.append(name_half)

    # Fullwidth mark: [-1200, 0]
    pen_w = TTGlyphPen(None)
    pen_w.moveTo((-1200, y_pos))
    pen_w.lineTo((0, y_pos))
    pen_w.lineTo((0, y_pos + thickness))
    pen_w.lineTo((-1200, y_pos + thickness))
    pen_w.closePath()
    glyf.glyphs[name_wide] = pen_w.glyph()
    hmtx.metrics[name_wide] = (0, -1200)
    if name_wide not in glyph_order:
        glyph_order.append(name_wide)

    # Map Unicode to default halfwidth mark
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = name_half

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# 6. Add contextual substitution for fullwidth marks and enable IgnoreMarks on ligatures
print("6. Configuring GSUB (IgnoreMarks on ligatures + fullwidth mark switching)...")
gsub = font['GSUB'].table

# Set IgnoreMarks (flag 8) on ligature lookups (avoiding conflict with UseMarkFilteringSet 0x0010)
for l in gsub.LookupList.Lookup:
    if not (l.LookupFlag & 0x0010):
        l.LookupFlag |= 8

# SingleSubst for wide marks
sub_table = otTables.SingleSubst()
sub_table.mapping = {
    'uni0305': 'uni0305.wide',
    'uni0332': 'uni0332.wide',
    'uni0336': 'uni0336.wide',
}
l_wide = otTables.Lookup()
l_wide.LookupType = 1
l_wide.LookupFlag = 0
l_wide.SubTable = [sub_table]
l_wide.SubTableCount = 1
l_wide_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(l_wide)

# Contextual: when preceded by fullwidth glyph, switch to .wide
chain = otTables.ChainContextSubst()
chain.Format = 3
chain.BacktrackCoverage = [otTables.Coverage()]
glyph_to_id = {gn: i for i, gn in enumerate(glyph_order)}
chain.BacktrackCoverage[0].glyphs = sorted(fullwidth_glyphs, key=lambda gn: glyph_to_id[gn])
chain.BacktrackGlyphCount = 1

chain.InputCoverage = [otTables.Coverage()]
chain.InputCoverage[0].glyphs = sorted(['uni0305', 'uni0332', 'uni0336'], key=lambda gn: glyph_to_id[gn])
chain.InputGlyphCount = 1

chain.LookAheadCoverage = []
chain.LookAheadGlyphCount = 0

rec = otTables.SubstLookupRecord()
rec.SequenceIndex = 0
rec.LookupListIndex = l_wide_idx
chain.SubstLookupRecord = [rec]
chain.SubstCount = 1

l_chain = otTables.Lookup()
l_chain.LookupType = 6
l_chain.LookupFlag = 0
l_chain.SubTable = [chain]
l_chain.SubTableCount = 1
l_chain_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(l_chain)

# Register in calt
for fr in gsub.FeatureList.FeatureRecord:
    if fr.FeatureTag == 'calt':
        fr.Feature.LookupListIndex.append(l_chain_idx)
        fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)

# 7. Configure GDEF with Mark = 3 and preserve MarkGlyphSetsDef for OTS compliance
import copy
if 'GDEF' in src_mono:
    gdef = copy.deepcopy(src_mono['GDEF'])
    table = gdef.table
    valid_glyphs = set(font.getGlyphOrder())
    
    # Filter GlyphClassDef
    classDefs = table.GlyphClassDef.classDefs
    table.GlyphClassDef.classDefs = {gn: cls for gn, cls in classDefs.items() if gn in valid_glyphs}
    
    mark_names = {'uni0305', 'uni0305.wide', 'uni0332', 'uni0332.wide', 'uni0336', 'uni0336.wide'}
    for gn in valid_glyphs:
        if gn in mark_names:
            table.GlyphClassDef.classDefs[gn] = 3
        elif gn not in table.GlyphClassDef.classDefs and gn != '.notdef':
            table.GlyphClassDef.classDefs[gn] = 1
            
    # Filter MarkGlyphSetsDef
    if hasattr(table, 'MarkGlyphSetsDef') and table.MarkGlyphSetsDef:
        for cov in table.MarkGlyphSetsDef.Coverage:
            cov.glyphs = [gn for gn in cov.glyphs if gn in valid_glyphs]
            
    font['GDEF'] = gdef

# 8. Add minimal GPOS table to prevent HarfBuzz fallback mark jumping (keep lines straight & flat)
from fontTools.ttLib.tables.G_P_O_S_ import table_G_P_O_S_
gpos = table_G_P_O_S_()
gpos.table = otTables.GPOS()
gpos.table.Version = 0x00010000
gpos.table.ScriptList = otTables.ScriptList()
gpos.table.ScriptList.ScriptRecord = []
gpos.table.FeatureList = otTables.FeatureList()
gpos.table.FeatureList.FeatureRecord = []
gpos.table.LookupList = otTables.LookupList()
gpos.table.LookupList.Lookup = []

sr = otTables.ScriptRecord()
sr.ScriptTag = 'DFLT'
sr.Script = otTables.Script()
sr.Script.DefaultLangSys = otTables.LangSys()
sr.Script.DefaultLangSys.ReqFeatureIndex = 0xFFFF
sr.Script.DefaultLangSys.FeatureIndex = []
sr.Script.LangSysRecord = []
gpos.table.ScriptList.ScriptRecord.append(sr)

font['GPOS'] = gpos

# Update font family names
name_table = font['name']
for r in name_table.names:
    if r.nameID == 1: # Family
        r.string = "PlaneMono"
    elif r.nameID == 4: # Full Name
        r.string = "PlaneMono Regular"
    elif r.nameID == 6: # PostScript
        r.string = "PlaneMono-Regular"

# 8. Save TTF and WOFF2
print("7. Saving PlaneMono.ttf and PlaneMono.woff2...")
font.flavor = None
font.save('/mnt/c/workspace/planefont/PlaneMono.ttf')

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneMono.woff2')

t_end = time.time()
print(f"Successfully generated PlaneMono fonts in {t_end - t_start:.2f}s!")
