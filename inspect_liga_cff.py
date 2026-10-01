import io
import base64
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options
from fontTools.ttLib.tables import otTables
from fontTools.pens.ttGlyphPen import TTGlyphPen
import uharfbuzz as hb

# Load LigaNotoSansMono
font = TTFont('/tmp/LigaNotoSansMono-Regular.otf')

# Let's inspect its CFF and font details
cff = font['CFF ']
top_dict = cff.cff.topDictIndex[0]
charstrings = top_dict.CharStrings
hmtx = font['hmtx']
cmap = font.getBestCmap()
os2 = font['OS/2']

print(f"CharStrings count: {len(charstrings)}")
print(f"Ascender: {os2.sTypoAscender}, Descender: {os2.sTypoDescender}")

# In LigaNotoSansMono, width = 600
# For CFF, we can add combining mark CharStrings for:
# 1. Halfwidth line: [-600, 0] at ascender (y=1069)
# Let's check where the top of capital letters is:
print("CapHeight:", os2.sCapHeight) # usually ~700-800
