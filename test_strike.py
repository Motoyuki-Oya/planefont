import uharfbuzz as hb

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
font = hb.Font(face)

text = "削̶除̶済̶み̶テ̶キ̶ス̶ト̶ー̶"
buf = hb.Buffer()
buf.add_str(text)
buf.guess_segment_properties()
hb.shape(font, buf, {"calt": True, "ccmp": True})

print(f"--- Shaping: {text} ---")
for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
    name = font.glyph_to_string(info.codepoint)
    print(f"cluster={info.cluster:2} glyph={name:<15} adv=({pos.x_advance:4}, {pos.y_advance:4}) off=({pos.x_offset:5}, {pos.y_offset:5})")
