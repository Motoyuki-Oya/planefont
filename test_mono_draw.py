from fontTools.ttLib import TTFont
from fontTools.misc.psCharStrings import T2CharString
import uharfbuzz as hb

font = TTFont('/tmp/mono_subset.otf')
cff = font['CFF ']
top_dict = cff.cff.topDictIndex[0]
charstrings = top_dict.CharStrings
cmap = font.getBestCmap()
hmtx = font['hmtx']
glyph_order = font.getGlyphOrder()

def make_cff_rect(x_min, y_min, x_max, y_max):
    dx = x_max - x_min
    dy = y_max - y_min
    program = [
        0, # advance width = 0
        x_min, y_min, 'rmoveto',
        dx, 0, 'rlineto',
        0, dy, 'rlineto',
        -dx, 0, 'rlineto',
        'closepath',
        'endchar'
    ]
    cs = T2CharString()
    cs.program = program
    return cs

# Add uni0305 (-500 to 0)
gn_half = 'uni0305'
charstrings.charStrings[gn_half] = make_cff_rect(-500, 880, 0, 930)
hmtx.metrics[gn_half] = (0, -500)
if gn_half not in glyph_order:
    glyph_order.append(gn_half)
    font.setGlyphOrder(glyph_order)

for sub in font['cmap'].tables:
    if sub.isUnicode():
        sub.cmap[0x0305] = gn_half

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneMono-test.woff2')
print("Saved PlaneMono-test.woff2 successfully!")

# Test with uharfbuzz
with open('/mnt/c/workspace/planefont/PlaneMono-test.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
hb_font = hb.Font(face)
buf = hb.Buffer()
buf.add_str("H̅e̅l̅l̅o̅")
buf.guess_segment_properties()
hb.shape(hb_font, buf)

print("\n--- HarfBuzz Shaping: H̅e̅l̅l̅o̅ ---")
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    name = hb_font.glyph_to_string(info.codepoint)
    print(f"cluster={info.cluster} glyph={name:<12} advance=({pos.x_advance}, {pos.y_advance}) offset=({pos.x_offset}, {pos.y_offset})")
