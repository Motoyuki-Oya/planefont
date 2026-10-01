from fontTools.ttLib import TTFont

font = TTFont('/tmp/NotoSansJP-Regular.ttf')
print("getGlyphOrder len:", len(font.getGlyphOrder()))
order = font.getGlyphOrder()
order.append('test_glyph')
font.setGlyphOrder(order)
print("after setGlyphOrder, 'test_glyph' in getGlyphOrder:", 'test_glyph' in font.getGlyphOrder())

from fontTools.feaLib.builder import Builder
builder = Builder(font, None)
print("'test_glyph' in builder.glyphMap:", 'test_glyph' in builder.glyphMap)
