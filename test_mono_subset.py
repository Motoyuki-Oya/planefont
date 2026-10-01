from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

# Let's subset NotoSansMonoCJKjp-Regular.otf for rapid prototyping
font = TTFont('/tmp/noto_mono/NotoSansMonoCJKjp-Regular.otf')

print("Original font format:", 'CFF ' in font and "OTF/CFF" or "TTF")
options = Options()
options.layout_features = ['*']
options.name_IDs = ['*']
subsetter = Subsetter(options=options)

# ASCII + Hiragana + Katakana + Common Kanji sample + Combining marks
test_unicodes = [ord(c) for c in "Hello World平均値あいうえお削除テスト下線"] + [0x0305, 0x0332, 0x0336]
subsetter.populate(unicodes=test_unicodes)
subsetter.subset(font)

font.save('/tmp/mono_subset.otf')
print("Subsetted mono font created!")
