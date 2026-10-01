from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
import io

src = TTFont('/tmp/LigaNotoSansMono-Regular.otf')
glyph_set = src.getGlyphSet()

# Test drawing an arbitrary CFF glyph into TTGlyphPen
pen = TTGlyphPen(None)
glyph_set['W'].draw(pen)
tt_glyph = pen.glyph()

print("Successfully converted CFF glyph 'W' to TTGlyph! numContours:", tt_glyph.numberOfContours)
