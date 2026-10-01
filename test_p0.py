import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
gsub = font['GSUB'].table

# Find the LigatureSubst lookup
lig_idx = None
for i, l in enumerate(gsub.LookupList.Lookup):
    if l.LookupType == 4:
        lig_idx = i
        break

print(f"Found ligature lookup at index {lig_idx}")
our_lookup = gsub.LookupList.Lookup[lig_idx]
our_lookup.LookupFlag = 0

# Set all glyphs to Base in GDEF so HarfBuzz never skips mark
if 'GDEF' in font:
    gdef = font['GDEF'].table
    if not hasattr(gdef, 'GlyphClassDef') or gdef.GlyphClassDef is None:
        gdef.GlyphClassDef = otTables.GlyphClassDef()
        gdef.GlyphClassDef.classDefs = {}
    classes = gdef.GlyphClassDef.classDefs
    for m in ['uni0305', 'uni0332', 'uni0336']:
        classes[m] = 1

# Move our lookup to index 0
gsub.LookupList.Lookup.pop(lig_idx)
gsub.LookupList.Lookup.insert(0, our_lookup)

for fr in gsub.FeatureList.FeatureRecord:
    new_indices = []
    for idx in fr.Feature.LookupListIndex:
        if idx == lig_idx:
            new_indices.append(0)
        elif idx < lig_idx:
            new_indices.append(idx + 1)
        else:
            new_indices.append(idx)
    fr.Feature.LookupListIndex = new_indices

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/test_p0.woff2')

with open('/mnt/c/workspace/planefont/test_p0.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
hb_font = hb.Font(face)
buf = hb.Buffer()
buf.add_str("H̅e̅l̅l̅o̅")
buf.guess_segment_properties()
hb.shape(hb_font, buf, {"ccmp": True, "liga": True, "calt": True})

print("\n--- Shaping H̅e̅l̅l̅o̅ ---")
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    print(f"cluster={info.cluster} glyph={hb_font.glyph_to_string(info.codepoint)} advance=({pos.x_advance}, {pos.y_advance})")
