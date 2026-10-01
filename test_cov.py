import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import otTables

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
gsub = font['GSUB'].table

# Find the LigatureSubst lookup
for l in gsub.LookupList.Lookup:
    if l.LookupType == 4:
        for st in l.SubTable:
            st.Coverage = otTables.Coverage()
            st.Coverage.glyphs = list(st.ligatures.keys())
            print(f"Fixed Coverage with {len(st.Coverage.glyphs)} glyphs: {st.Coverage.glyphs[:5]}")

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneSans-cov.woff2')

with open('/mnt/c/workspace/planefont/PlaneSans-cov.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
hb_font = hb.Font(face)
buf = hb.Buffer()
buf.add_str("H̅e̅l̅l̅o̅")
buf.guess_segment_properties()
hb.shape(hb_font, buf, {"ccmp": True, "liga": True, "calt": True})

print("\n--- Shaping H̅e̅l̅l̅o̅ after Coverage fix ---")
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    print(f"cluster={info.cluster} glyph={hb_font.glyph_to_string(info.codepoint)} advance=({pos.x_advance}, {pos.y_advance})")
