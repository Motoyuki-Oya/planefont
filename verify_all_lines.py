import uharfbuzz as hb

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
font = hb.Font(face)

lines = [
    "H̅e̅l̅l̅o̅ W̅o̅r̅l̅d̅",
    "平̅均̅値̅　あ̅い̅う̅え̅お̅",
    "H̲e̲l̲l̲o̲ W̲o̲r̲l̲d̲　下̲線̲テ̲ス̲ト̲",
    "H̶e̶l̶l̶o̶ W̶o̶r̶l̶d̶　削̶除̶済̶み̶テ̶キ̶ス̶ト̶ー̶"
]

for text in lines:
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"ccmp": True, "liga": True, "calt": True})
    
    print(f"\n--- Line: {text} ---")
    output = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = font.glyph_to_string(info.codepoint)
        output.append(f"{name}({pos.x_advance})")
    print(" ".join(output))
