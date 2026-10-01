import io
import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib.tables import otTables

# 1. Load LigaNotoSansMono (OTF with programming ligatures)
font_mono = TTFont('/tmp/LigaNotoSansMono-Regular.otf')

# We can also load NotoSansJP for Japanese characters
font_jp = TTFont('/tmp/NotoSansJP-Regular.ttf')
jp_glyf = font_jp['glyf']
jp_hmtx = font_jp['hmtx']
jp_cmap = font_jp.getBestCmap()

print("LigaNoto format:", 'CFF ' in font_mono and 'CFF' or 'TTF')
print("GSUB in LigaNoto:", 'GSUB' in font_mono)
