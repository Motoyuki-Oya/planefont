import io
from fontTools.ttLib import TTFont
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
import uharfbuzz as hb

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')

# Let's inspect the feaLib code generated
# Re-compile GSUB with feature ccmp specifically
fea_code = """
languagesystem DFLT dflt;
languagesystem latn dflt;
languagesystem kana dflt;
languagesystem hani dflt;

feature ccmp {
    lookup OVERLINE_COMP {
        sub H uni0305 by H_overline;
        sub e uni0305 by e_overline;
        sub l uni0305 by l_overline;
        sub o uni0305 by o_overline;
        sub W uni0305 by W_overline;
        sub r uni0305 by r_overline;
        sub d uni0305 by d_overline;
    } OVERLINE_COMP;
} ccmp;
"""

del font['GSUB']
addOpenTypeFeaturesFromString(font, fea_code)

buf = io.BytesIO()
font.save(buf)
buf.seek(0)
fdata = buf.read()

face = hb.Face(fdata)
hb_font = hb.Font(face)
hbuf = hb.Buffer()
hbuf.add_str("H\u0305e\u0305l\u0305l\u0305o\u0305")
hbuf.guess_segment_properties()
hb.shape(hb_font, hbuf, {"ccmp": True})

print("--- Testing ccmp feature ---")
for info, pos in zip(hbuf.glyph_infos, hbuf.glyph_positions):
    print(f"cluster={info.cluster} glyph={hb_font.glyph_to_string(info.codepoint)} adv={pos.x_advance}")
