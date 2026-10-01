import uharfbuzz as hb

with open('/tmp/LigaNotoSansMono-Regular.otf', 'rb') as f:
    fdata = f.read()

face = hb.Face(fdata)
font = hb.Font(face)

test_ligs = ["=>", "===", "!=", "->", "<=", ">=", "<!--", "fn()"]

for s in test_ligs:
    buf = hb.Buffer()
    buf.add_str(s)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"calt": True, "liga": True})
    
    names = [font.glyph_to_string(info.codepoint) for info in buf.glyph_infos]
    advs = [pos.x_advance for pos in buf.glyph_positions]
    print(f"'{s}': glyphs={names} advances={advs}")
