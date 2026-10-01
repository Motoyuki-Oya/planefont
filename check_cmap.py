from fontTools.ttLib import TTFont

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
cmap = font.getBestCmap()

for char in ['H', 'e', 'l', 'o', '\u0305', '平', '均', '値', 'あ']:
    cp = ord(char)
    gn = cmap.get(cp)
    print(f"'{char}' (U+{cp:04X}): glyph={gn}")
