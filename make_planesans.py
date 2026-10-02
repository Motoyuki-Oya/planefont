import io
import time
import base64
import urllib.request
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.ttLib.tables import otTables

t_start = time.time()
print("1. Preparing NotoSansJP source font...")
src_path = Path('/tmp/NotoSansJP-wght.ttf')
if not src_path.exists():
    print("Downloading NotoSansJP[wght].ttf from Google Fonts...")
    url = 'https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf'
    urllib.request.urlretrieve(url, str(src_path))

print("2. Instantiating static Regular (wght=400)...")
var_font = TTFont(str(src_path))
font = instantiateVariableFont(var_font, {'wght': 400})

# Remove variable font specific tables to ensure pure static TrueType font
for tag in ['gvar', 'HVAR', 'VVAR', 'MVAR', 'vhea', 'vmtx', 'BASE', 'STAT', 'avar', 'fvar', 'gasp']:
    if tag in font:
        del font[tag]

# Re-serialize to clean internal structures
buf = io.BytesIO()
font.save(buf)
buf.seek(0)
font = TTFont(buf)

glyf = font['glyf']
hmtx = font['hmtx']
cmap = font.getBestCmap()
glyph_order = list(font.getGlyphOrder())
os2 = font['OS/2']

ascender = os2.sTypoAscender       # 880
strikeout = os2.yStrikeoutPosition # 325
underline = font['post'].underlinePosition if 'post' in font else -125 # -125
thickness = 50

print(f"Loaded {len(glyph_order)} glyphs ({len(cmap)} cmap entries).")

# 3. Analyze character widths across all base glyphs
print("3. Analyzing character widths across all glyphs...")
base_glyphs = {}
unique_widths = set()

for gn in glyph_order:
    if gn == '.notdef':
        continue
    w, lsb = hmtx.metrics.get(gn, (1000, 0))
    if w > 0:
        base_glyphs[gn] = w
        unique_widths.add(w)

sorted_widths = sorted(unique_widths)
print(f"Found {len(sorted_widths)} unique character widths: min={sorted_widths[0]}, max={sorted_widths[-1]}")

# 4. Generate width-fitted combining marks
print("4. Generating width-fitted combining marks (Overline, Underline, Strikeout)...")
mark_types = [
    (0x0305, 'uni0305', ascender, 'overline'),
    (0x0332, 'uni0332', underline, 'underline'),
    (0x0336, 'uni0336', strikeout, 'strike'),
]

created_mark_names = set()

for w in sorted_widths:
    for cp, default_name, y_pos, tag in mark_types:
        if w == 1000:
            m_name = default_name
        else:
            m_name = f"{default_name}.w{w}"
        
        pen = TTGlyphPen(None)
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

# 5. Build OpenType GSUB contextual substitution
print("5. Configuring GSUB contextual substitutions for exact width matching...")
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

# Create SingleSubst lookup for each width != 1000
width_to_lookup_idx = {}

for w in sorted_widths:
    if w == 1000:
        continue
    
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

# Group base glyphs by width
glyphs_by_width = {}
for gn, w in base_glyphs.items():
    glyphs_by_width.setdefault(w, []).append(gn)

chain_subtables = []
glyph_to_id = {gn: i for i, gn in enumerate(glyph_order)}

for w in sorted_widths:
    if w == 1000:
        continue
    b_glyphs = glyphs_by_width.get(w, [])
    if not b_glyphs:
        continue
    l_idx = width_to_lookup_idx[w]
    
    chain = otTables.ChainContextSubst()
    chain.Format = 3
    chain.BacktrackCoverage = [otTables.Coverage()]
    chain.BacktrackCoverage[0].glyphs = sorted(b_glyphs, key=lambda gn: glyph_to_id.get(gn, 0))
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

# Register main_chain_idx in calt and ccmp
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

# 6. GDEF configuration
print("6. Configuring GDEF table...")
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

# 7. Update Name table to PlaneSans Regular
print("7. Updating font metadata to PlaneSans Regular...")
name_table = font['name']
for r in name_table.names:
    if r.nameID == 1: # Family
        r.string = "PlaneSans"
    elif r.nameID == 2: # Subfamily
        r.string = "Regular"
    elif r.nameID == 4: # Full Name
        r.string = "PlaneSans Regular"
    elif r.nameID == 6: # PostScript Name
        r.string = "PlaneSans-Regular"

# 8. Save TTF and WOFF2
print("8. Saving PlaneSans.ttf and PlaneSans.woff2...")
out_ttf = Path('/mnt/c/workspace/planefont/PlaneSans.ttf')
out_woff2 = Path('/mnt/c/workspace/planefont/PlaneSans.woff2')

font.flavor = None
font.save(str(out_ttf))

font.flavor = 'woff2'
font.save(str(out_woff2))

t_end = time.time()
print(f"Successfully generated PlaneSans (Full Japanese Regular) in {t_end - t_start:.2f}s!")
