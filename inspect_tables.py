from fontTools.ttLib import TTFont

gen = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
hmtx = gen['hmtx']
glyf = gen['glyf']

for name in ['uni0305', 'uni0332', 'uni0336']:
    print(f'{name}: hmtx={hmtx.metrics.get(name)}')
    glyph = glyf[name]
    print(f'  numberOfContours={glyph.numberOfContours}')
    if glyph.numberOfContours > 0:
        print(f'  xMin={glyph.xMin}, yMin={glyph.yMin}, xMax={glyph.xMax}, yMax={glyph.yMax}')
