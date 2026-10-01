from fontTools.ttLib import TTFont

font = TTFont('/tmp/noto_mono/NotoSansMonoCJKjp-Regular.otf')
hmtx = font['hmtx']
cmap = font.getBestCmap()

print("UPM:", font['head'].unitsPerEm)
for char in ['H', 'e', 'l', 'o', '1', '平', '均', 'あ', '！']:
    cp = ord(char)
    gn = cmap.get(cp)
    width, lsb = hmtx.metrics.get(gn, (None, None))
    print(f"'{char}' ({gn}): width={width}, lsb={lsb}")
