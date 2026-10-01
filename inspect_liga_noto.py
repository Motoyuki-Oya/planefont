from fontTools.ttLib import TTFont

font = TTFont('/tmp/LigaNotoSansMono-Regular.otf')
upm = font['head'].unitsPerEm
hmtx = font['hmtx']
cmap = font.getBestCmap()
os2 = font['OS/2']

print(f"Format: {'CFF ' in font and 'OTF/CFF' or 'TTF'}")
print(f"UPM: {upm}")
print(f"Ascender: {os2.sTypoAscender}, Descender: {os2.sTypoDescender}")

# Inspect glyph widths
sample_chars = ['a', 'W', 'i', '0', '=', '>', '<', '-', '/']
for c in sample_chars:
    gn = cmap.get(ord(c))
    w, lsb = hmtx.metrics.get(gn, (None, None))
    print(f"'{c}' ({gn}): width={w}")

# Inspect GSUB features (looking for calt, liga)
if 'GSUB' in font:
    features = [fr.FeatureTag for fr in font['GSUB'].table.FeatureList.FeatureRecord]
    print(f"GSUB Features: {set(features)}")
