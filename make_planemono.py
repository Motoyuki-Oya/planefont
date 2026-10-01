import io
import time
import base64
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib.tables._g_l_y_f import table__g_l_y_f
from fontTools.ttLib.tables._h_m_t_x import table__h_m_t_x
from fontTools.ttLib.tables._l_o_c_a import table__l_o_c_a
from fontTools.ttLib.tables._m_a_x_p import table__m_a_x_p
from fontTools.ttLib.tables.G_D_E_F_ import table_G_D_E_F_
from fontTools.ttLib.tables import otTables

t_start = time.time()
print("1. Loading LigaNotoSansMono (Programming ligatures)...")
src_mono = TTFont('/tmp/LigaNotoSansMono-Regular.otf')
mono_set = src_mono.getGlyphSet()
mono_hmtx = src_mono['hmtx']
mono_cmap = src_mono.getBestCmap()
mono_order = src_mono.getGlyphOrder()

print("2. Loading NotoSansMonoCJKjp (Japanese Monospace)...")
src_cjk = TTFont('/tmp/noto_mono/NotoSansMonoCJKjp-Regular.otf')
cjk_set = src_cjk.getGlyphSet()
cjk_hmtx = src_cjk['hmtx']
cjk_cmap = src_cjk.getBestCmap()

# Create target TrueType font based on LigaNoto (keeps OS/2, name, GSUB programming ligatures)
font = TTFont()
font.sfntVersion = '\x00\x01\x00\x00'
for tag in ['head', 'hhea', 'OS/2', 'post', 'cmap', 'name', 'GSUB']:
    if tag in src_mono:
        font[tag] = src_mono[tag]

# Initialize maxp table for TrueType format
maxp = table__m_a_x_p()
maxp.tableVersion = 0x00010000
for attr in ['maxPoints', 'maxContours', 'maxCompositePoints', 'maxCompositeContours',
             'maxZones', 'maxTwilightPoints', 'maxStorage', 'maxFunctionDefs',
             'maxInstructionDefs', 'maxStackElements', 'maxSizeOfInstructions',
             'maxComponentElements', 'maxComponentDepth']:
    setattr(maxp, attr, 0)
maxp.maxZones = 1
font['maxp'] = maxp

# Initialize glyf, hmtx, loca
glyf = table__g_l_y_f()
glyf.glyphs = {}
font['glyf'] = glyf

hmtx = table__h_m_t_x()
hmtx.metrics = {}
font['hmtx'] = hmtx

font['loca'] = table__l_o_c_a()

glyph_order = []

from fontTools.pens.cu2quPen import Cu2QuPen

# Copy all glyphs from LigaNotoSansMono (Latin + Programming Ligatures)
print("3. Converting LigaNoto glyphs to TrueType (cu2qu quadratic)...")
for gn in mono_order:
    pen = TTGlyphPen(None)
    cu2qu = Cu2QuPen(pen, max_err=1.0)
    mono_set[gn].draw(cu2qu)
    glyf.glyphs[gn] = pen.glyph()
    w, lsb = mono_hmtx.metrics.get(gn, (600, 0))
    hmtx.metrics[gn] = (w, lsb)
    glyph_order.append(gn)

# Merge Japanese characters from NotoSansMonoCJKjp
# Select comprehensive set: Hiragana, Katakana, Punctuation, Fullwidth symbols,
# Box drawing, Block elements, and common Kanji (covering all sample text + common CJK)
sample_jp_text = "Hello World 平均値あいうえお下線テスト削除済みテキストー、。！？（）「」"
extra_cps = set(ord(c) for c in sample_jp_text)

selected_cps = set()
for cp in cjk_cmap:
    if cp < 0x80:
        continue  # Keep all ASCII from LigaNotoSansMono for programming ligatures!
    if (0x3000 <= cp <= 0x33FF or 
        0xFF00 <= cp <= 0xFFEF or 
        0x2000 <= cp <= 0x27FF or
        0x4E00 <= cp <= 0x9FFF):
        selected_cps.add(cp)
    elif cp in extra_cps:
        selected_cps.add(cp)

print(f"4. Merging {len(selected_cps)} Japanese glyphs from NotoSansMonoCJKjp (Fullwidth 1200, cu2qu)...")

cjk_to_target = {}
for cp in selected_cps:
    cjk_gn = cjk_cmap[cp]
    if cjk_gn not in cjk_to_target:
        target_gn = f"jp_{cp:04X}"
        cjk_to_target[cjk_gn] = target_gn
        
        # Scale/center from 1000 to 1200 fullwidth:
        # Width 1200 = 600 * 2 (1:2 monospace ratio).
        # Source is 1000 wide, offset by +100 to center in 1200 box:
        orig_w, orig_lsb = cjk_hmtx.metrics.get(cjk_gn, (1000, 0))
        pen1200 = TTGlyphPen(None)
        cu2qu = Cu2QuPen(pen1200, max_err=1.0)
        tpen = TransformPen(cu2qu, (1, 0, 0, 1, 100, 0))
        cjk_set[cjk_gn].draw(tpen)
        
        glyf.glyphs[target_gn] = pen1200.glyph()
        hmtx.metrics[target_gn] = (1200, orig_lsb + 100)
        glyph_order.append(target_gn)
    else:
        target_gn = cjk_to_target[cjk_gn]
    
    # Register in cmap
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = target_gn

# 5. Add combining marks:
# Halfwidth line: [-600, 0] for Latin / code ligatures
# Fullwidth line: [-1200, 0] for Japanese
print("5. Adding continuous combining marks (Halfwidth 600 & Fullwidth 1200)...")
ascender = 880
strikeout = 325
underline = -125
thickness = 50

mark_configs = [
    (0x0305, 'uni0305', 'uni0305.wide', ascender),
    (0x0332, 'uni0332', 'uni0332.wide', underline),
    (0x0336, 'uni0336', 'uni0336.wide', strikeout),
]

fullwidth_glyphs = [gn for gn in glyph_order if hmtx.metrics.get(gn, (0, 0))[0] >= 1000 and not gn.startswith('uni03')]

for cp, name_half, name_wide, y_pos in mark_configs:
    # Halfwidth mark: [-600, 0]
    pen = TTGlyphPen(None)
    pen.moveTo((-600, y_pos))
    pen.lineTo((0, y_pos))
    pen.lineTo((0, y_pos + thickness))
    pen.lineTo((-600, y_pos + thickness))
    pen.closePath()
    glyf.glyphs[name_half] = pen.glyph()
    hmtx.metrics[name_half] = (0, -600)
    if name_half not in glyph_order:
        glyph_order.append(name_half)

    # Fullwidth mark: [-1200, 0]
    pen_w = TTGlyphPen(None)
    pen_w.moveTo((-1200, y_pos))
    pen_w.lineTo((0, y_pos))
    pen_w.lineTo((0, y_pos + thickness))
    pen_w.lineTo((-1200, y_pos + thickness))
    pen_w.closePath()
    glyf.glyphs[name_wide] = pen_w.glyph()
    hmtx.metrics[name_wide] = (0, -1200)
    if name_wide not in glyph_order:
        glyph_order.append(name_wide)

    # Map Unicode to default halfwidth mark
    for sub in font['cmap'].tables:
        if sub.isUnicode():
            sub.cmap[cp] = name_half

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# 5b. 特製イースターエッグ合字: 飛行機シルエット (>-)-)
# 4文字の等幅グリッド (半角600幅 × 4 = 2400) に美しく収まる4分割型ジェット機グリフ。
# 各セクション (尾翼, 胴体, 主翼, 機首) は50ユニットの平行スリットで区切られ、
# 後方には超音速飛行を表現する4本の流線形推進線 (太さ50ユニット, 均一間隔220) を配置。
#
# 【各グリフの役割と座標系 (全幅 2400)】
#  - plane.tail (入力 '>'): セル [0, 600] / 原点 0
#      後方推進線 (尾翼側2本: x=100..642, yc=405, 135) + 60度開き角の尾翼フィン (頂点 x=1087, 垂直カット高さ90)
#  - plane.body (入力 '-'): セル [600, 1200] / 原点 600
#      キャビン胴体セグメント (太さ90, 長さ260, 前端凸円弧)
#  - plane.wing (入力 ')'): セル [1200, 1800] / 原点 1200
#      後方推進線 (主翼側2本: world x=100..970, yc=675, -135) + 三日月型主翼 (弦長120..90, 全高900)
#  - plane.nose (入力 '-'): セル [1800, 2400] / 原点 1800
#      流線形レドーム機首 (長さ650, 先端 x=2280)
#
# 【設計仕様】
#  - 機体ストローク太さ: 90ユニット (y=225..315, 中心線 y=270)
#  - 推進線: 太さ50ユニット, 後端ノーズ型テーパー, 上下等間隔220ユニット
#  - 機首と胴体の長さ比率: 5 : 2 (機首長 650 : 胴体長 260)
#  - セクション間スリット: 50.0ユニット平行

print("5b. Adding segmented airplane ligature glyphs (plane.tail, plane.body, plane.wing, plane.nose)...")

y_bot = 225
y_top = 315

def add_tapered_line(pen, x0, x1, yc, th=50, taper_len=120):
    """後端（左端）がノーズ型に滑らかに収束する推進線を描画"""
    half = th // 2
    y_bot = yc - half
    y_top = yc + half
    x_taper_end = x0 + taper_len
    x_ctrl = x0 + int(taper_len * 0.4)
    pen.moveTo((x0, yc))
    pen.qCurveTo((x_ctrl, y_bot), (x_taper_end, y_bot))
    pen.lineTo((x1, y_bot))
    pen.lineTo((x1, y_top))
    pen.lineTo((x_taper_end, y_top))
    pen.qCurveTo((x_ctrl, y_top), (x0, yc))
    pen.closePath()

# 1. 尾翼: 基準角60度 (合計開き角120度)、胴体接続部垂直カット (太さ90)、小型ノズル + 尾翼推進線2本
def draw_plane_tail():
    pen = TTGlyphPen(None)
    # 尾翼推進線 (上下対称2本: 太さ50, 機体間隔240, 後方テーパー)
    add_tapered_line(pen, 100, 642, 405, th=50)
    add_tapered_line(pen, 100, 642, 135, th=50)

    # 尾翼本体 (時計回り)
    # ノズル: フィン根元(983)から後方へ突き出たラウンドキャップ
    pen.moveTo((983, 225))
    pen.qCurveTo((958, 225), (958, 270))
    pen.qCurveTo((958, 315), (983, 315))
    # 上翼後縁 (60度傾斜, 直交厚さ90)
    pen.lineTo((882, 490))
    # 上翼端: 気流に沿った水平カット (幅104 -> 直交厚さ90)
    pen.lineTo((986, 490))
    # 上翼前縁 (60度傾斜)
    pen.lineTo((1087, 315))
    # 胴体接続側頂点の垂直カット面 (高さ90ユニット: y=225..315)
    pen.lineTo((1087, 225))
    # 下翼前縁 (60度傾斜)
    pen.lineTo((986, 50))
    # 下翼端: 水平カット (幅104)
    pen.lineTo((882, 50))
    # 下翼後縁 (60度傾斜, 直交厚さ90)
    pen.lineTo((983, 225))
    pen.closePath()
    return pen.glyph()

# 2. 胴体: 尾翼の垂直カットに対向するフラット垂直面 (太さ90, 長さ260, スリット50均一)
def draw_plane_body():
    pen = TTGlyphPen(None)
    # 後部対向面: フラットな垂直カット (高さ90ユニット: y=225..315)
    pen.moveTo((537, 315))
    pen.lineTo((537, 225))
    # テーパーなしのストレート下端 (長さ260)
    pen.lineTo((809, 225))
    # 前部接続面: 主翼の曲率に沿った前凸の円弧
    pen.qCurveTo((811, 270), (809, 315))
    pen.closePath()
    return pen.glyph()

# 3. 主翼: 単一C1三日月翼 (根元弦長120, 翼端弦長90) + 主翼推進線2本
def draw_plane_wing():
    pen = TTGlyphPen(None)
    # 主翼推進線 (上下対称2本: 太さ50, 機体間隔360, 後方テーパー)
    add_tapered_line(pen, -1100, -230, 675, th=50)
    add_tapered_line(pen, -1100, -230, -135, th=50)

    # 主翼本体 (時計回り, 凹みなしの滑らかな単一円滑曲線)
    # 後縁: 下翼端から中央頂点を経て上翼端へ
    pen.moveTo((130, -180))
    pen.qCurveTo((260, 20), (260, 270))
    pen.qCurveTo((260, 520), (130, 720))
    # 上翼端: 水平カット (弦長90)
    pen.lineTo((220, 720))
    # 前縁: 上翼端から中央頂点を経て下翼端へ
    pen.qCurveTo((380, 520), (380, 270))
    pen.qCurveTo((380, 20), (220, -180))
    # 下翼端: 水平カット (弦長90)
    pen.lineTo((130, -180))
    pen.closePath()
    return pen.glyph()

# 4. 機首: ストレート胴体 (太さ90) + 先端レドーム (長さ650, 4文字目セル内に480ユニット突出)
def draw_plane_nose():
    pen = TTGlyphPen(None)
    # 後部接続面: 主翼前縁に沿った受容円弧 (スリット50均一)
    pen.moveTo((-171, 315))
    pen.qCurveTo((-169, 270), (-171, 225))
    # テーパーなしのストレート下端
    pen.lineTo((300, 225))
    # 先端レドーム: 細身で丸みを帯びた流線形ノーズチップ
    pen.qCurveTo((410, 225), (480, 270))
    pen.qCurveTo((410, 315), (300, 315))
    # テーパーなしのストレート上端
    pen.lineTo((-171, 315))
    pen.closePath()
    return pen.glyph()

# -------------------------------------------------------------------------
# 左向き飛行機合字: -(-< 用グリフ群 (右向きグリフの X=1200 軸完全反転)
# -------------------------------------------------------------------------
def add_right_tapered_line(pen, x0, x1, yc, th=50, taper_len=120):
    """後端（右端）がノーズ型に滑らかに収束する推進線を描画"""
    half = th // 2
    y_bot = yc - half
    y_top = yc + half
    x_taper_start = x1 - taper_len
    x_ctrl = x1 - int(taper_len * 0.4)
    # 時計回り (CW)
    pen.moveTo((x0, y_top))
    pen.lineTo((x_taper_start, y_top))
    pen.qCurveTo((x_ctrl, y_top), (x1, yc))
    pen.qCurveTo((x_ctrl, y_bot), (x_taper_start, y_bot))
    pen.lineTo((x0, y_bot))
    pen.lineTo((x0, y_top))
    pen.closePath()

# 1. 機首 (入力 '-'): 左向きノーズ (セル [0, 600] / 原点 0, 先端 x=120)
def draw_plane_left_nose():
    pen = TTGlyphPen(None)
    pen.moveTo((120, 270))
    pen.qCurveTo((190, 315), (300, 315))
    pen.lineTo((771, 315))
    pen.qCurveTo((769, 270), (771, 225))
    pen.lineTo((300, 225))
    pen.qCurveTo((190, 225), (120, 270))
    pen.closePath()
    return pen.glyph()

# 2. 主翼 (入力 '('): 左向き三日月翼 (セル [600, 1200] / 原点 600) + 推進線2本
def draw_plane_left_wing():
    pen = TTGlyphPen(None)
    # 主翼推進線 (上下対称2本: 太さ50, 機体間隔360, 後方テーパー, world 1430..2300 -> local 830..1700)
    add_right_tapered_line(pen, 830, 1700, 675, th=50)
    add_right_tapered_line(pen, 830, 1700, -135, th=50)

    # 主翼本体 (world 820..1070 -> local 220..470, CW)
    pen.moveTo((380, -180))
    pen.qCurveTo((220, 20), (220, 270))
    pen.qCurveTo((220, 520), (380, 720))
    pen.lineTo((470, 720))
    pen.qCurveTo((340, 520), (340, 270))
    pen.qCurveTo((340, 20), (470, -180))
    pen.lineTo((380, -180))
    pen.closePath()
    return pen.glyph()

# 3. 胴体 (入力 '-'): キャビン胴体 (セル [1200, 1800] / 原点 1200)
def draw_plane_left_body():
    pen = TTGlyphPen(None)
    # 後部対向面: 尾翼に対向するフラット垂直面 (高さ90ユニット: y=225..315)
    pen.moveTo((63, 315))
    pen.lineTo((63, 225))
    # テーパーなしのストレート下端 (長さ260)
    pen.lineTo((-209, 225))
    # 前部接続面: 主翼の曲率に沿った前凸の円弧 (スリット50均一)
    pen.qCurveTo((-211, 270), (-209, 315))
    pen.lineTo((63, 315))
    pen.closePath()
    return pen.glyph()

# 4. 尾翼 (入力 '<'): 左向き尾翼フィン (セル [1800, 2400] / 原点 1800) + 推進線2本
def draw_plane_left_tail():
    pen = TTGlyphPen(None)
    # 尾翼推進線 (上下対称2本: 太さ50, 機体間隔240, 後方テーパー, world 1758..2300 -> local -42..500)
    add_right_tapered_line(pen, -42, 500, 405, th=50)
    add_right_tapered_line(pen, -42, 500, 135, th=50)

    # 尾翼本体 (world 1313..1518 -> local -487..-282, CW)
    pen.moveTo((-383, 225))
    pen.lineTo((-282, 50))
    pen.lineTo((-386, 50))
    pen.lineTo((-487, 225))
    pen.lineTo((-487, 315))
    pen.lineTo((-386, 490))
    pen.lineTo((-282, 490))
    pen.lineTo((-383, 315))
    pen.qCurveTo((-358, 315), (-358, 270))
    pen.qCurveTo((-358, 225), (-383, 225))
    pen.closePath()
    return pen.glyph()

plane_glyphs = {
    # 右向き (>-)-)
    'plane.tail': (draw_plane_tail(), 100),
    'plane.body': (draw_plane_body(), 537),
    'plane.wing': (draw_plane_wing(), -1100),
    'plane.nose': (draw_plane_nose(), -171),
    # 左向き (-(-<)
    'plane.left_nose': (draw_plane_left_nose(), 120),
    'plane.left_wing': (draw_plane_left_wing(), 220),
    'plane.left_body': (draw_plane_left_body(), -211),
    'plane.left_tail': (draw_plane_left_tail(), -487),
}

for gn, (gl, lsb) in plane_glyphs.items():
    glyf.glyphs[gn] = gl
    hmtx.metrics[gn] = (600, lsb)
    if gn not in glyph_order:
        glyph_order.append(gn)

font.setGlyphOrder(glyph_order)
glyf.glyphOrder = list(glyph_order)

# 6. Configuring GSUB
print("6. Configuring GSUB (IgnoreMarks, >-)- airplane ligature, and fullwidth mark switching)...")
gsub = font['GSUB'].table

# OpenType GSUB: Prepend >-)- segmented airplane ligature lookups so they take priority
def make_single_subst(mapping):
    st = otTables.SingleSubst()
    st.mapping = mapping
    l = otTables.Lookup()
    l.LookupType = 1
    l.LookupFlag = 0
    l.SubTable = [st]
    l.SubTableCount = 1
    return l

# 右向き (>-)-)
l_tail = make_single_subst({'greater': 'plane.tail'})
l_body = make_single_subst({'hyphen': 'plane.body'})
l_wing = make_single_subst({'parenright': 'plane.wing'})
l_nose = make_single_subst({'hyphen': 'plane.nose'})

chain_plane = otTables.ChainContextSubst()
chain_plane.Format = 3
chain_plane.BacktrackCoverage = []
chain_plane.BacktrackGlyphCount = 0

cov_g = otTables.Coverage()
cov_g.glyphs = ['greater']
cov_h = otTables.Coverage()
cov_h.glyphs = ['hyphen']
cov_p = otTables.Coverage()
cov_p.glyphs = ['parenright']

chain_plane.InputCoverage = [cov_g, cov_h, cov_p, cov_h]
chain_plane.InputGlyphCount = 4
chain_plane.LookAheadCoverage = []
chain_plane.LookAheadGlyphCount = 0

plane_recs = []
for seq_idx, l_idx in [(0, 0), (1, 1), (2, 2), (3, 3)]:
    r = otTables.SubstLookupRecord()
    r.SequenceIndex = seq_idx
    r.LookupListIndex = l_idx
    plane_recs.append(r)

chain_plane.SubstLookupRecord = plane_recs
chain_plane.SubstCount = len(plane_recs)

l_chain_plane = otTables.Lookup()
l_chain_plane.LookupType = 6
l_chain_plane.LookupFlag = 0
l_chain_plane.SubTable = [chain_plane]
l_chain_plane.SubTableCount = 1

# 左向き (-(-<)
l_l_nose = make_single_subst({'hyphen': 'plane.left_nose'})
l_l_wing = make_single_subst({'parenleft': 'plane.left_wing'})
l_l_body = make_single_subst({'hyphen': 'plane.left_body'})
l_l_tail = make_single_subst({'less': 'plane.left_tail'})

chain_plane_left = otTables.ChainContextSubst()
chain_plane_left.Format = 3
chain_plane_left.BacktrackCoverage = []
chain_plane_left.BacktrackGlyphCount = 0

cov_pl = otTables.Coverage()
cov_pl.glyphs = ['parenleft']
cov_l = otTables.Coverage()
cov_l.glyphs = ['less']

chain_plane_left.InputCoverage = [cov_h, cov_pl, cov_h, cov_l]
chain_plane_left.InputGlyphCount = 4
chain_plane_left.LookAheadCoverage = []
chain_plane_left.LookAheadGlyphCount = 0

plane_left_recs = []
for seq_idx, l_idx in [(0, 5), (1, 6), (2, 7), (3, 8)]:
    r = otTables.SubstLookupRecord()
    r.SequenceIndex = seq_idx
    r.LookupListIndex = l_idx
    plane_left_recs.append(r)

chain_plane_left.SubstLookupRecord = plane_left_recs
chain_plane_left.SubstCount = len(plane_left_recs)

l_chain_plane_left = otTables.Lookup()
l_chain_plane_left.LookupType = 6
l_chain_plane_left.LookupFlag = 0
l_chain_plane_left.SubTable = [chain_plane_left]
l_chain_plane_left.SubTableCount = 1

new_plane_lookups = [
    l_tail, l_body, l_wing, l_nose, l_chain_plane,
    l_l_nose, l_l_wing, l_l_body, l_l_tail, l_chain_plane_left
]
shift = len(new_plane_lookups)

# Shift all existing LookupListIndex references
for fr in gsub.FeatureList.FeatureRecord:
    fr.Feature.LookupListIndex = [idx + shift for idx in fr.Feature.LookupListIndex]

for l in gsub.LookupList.Lookup:
    for st in l.SubTable:
        if hasattr(st, 'SubstLookupRecord'):
            for r in st.SubstLookupRecord:
                r.LookupListIndex += shift
        if hasattr(st, 'ChainSubRuleSet'):
            for srs in st.ChainSubRuleSet:
                if srs:
                    for rule in srs.ChainSubRule:
                        for r in rule.SubstLookupRecord:
                            r.LookupListIndex += shift
        if hasattr(st, 'ChainSubClassSet'):
            for scs in st.ChainSubClassSet:
                if scs:
                    for rule in scs.ChainSubClassRule:
                        for r in rule.SubstLookupRecord:
                            r.LookupListIndex += shift
        if hasattr(st, 'SubRuleSet'):
            for srs in st.SubRuleSet:
                if srs:
                    for rule in srs.SubRule:
                        for r in rule.SubstLookupRecord:
                            r.LookupListIndex += shift
        if hasattr(st, 'SubClassSet'):
            for scs in st.SubClassSet:
                if scs:
                    for rule in scs.SubClassRule:
                        for r in rule.SubstLookupRecord:
                            r.LookupListIndex += shift

# Prepend new plane lookups
gsub.LookupList.Lookup = new_plane_lookups + gsub.LookupList.Lookup

# Register chain rules (index 4 for >-)- and index 9 for -(-<) in calt and liga
for fr in gsub.FeatureList.FeatureRecord:
    if fr.FeatureTag in ('calt', 'liga'):
        fr.Feature.LookupListIndex.insert(0, 9)
        fr.Feature.LookupListIndex.insert(0, 4)
        fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)


# Set IgnoreMarks (flag 8) on ligature lookups (avoiding conflict with UseMarkFilteringSet 0x0010)
for l in gsub.LookupList.Lookup:
    if not (l.LookupFlag & 0x0010):
        l.LookupFlag |= 8

# SingleSubst for wide marks
sub_table = otTables.SingleSubst()
sub_table.mapping = {
    'uni0305': 'uni0305.wide',
    'uni0332': 'uni0332.wide',
    'uni0336': 'uni0336.wide',
}
l_wide = otTables.Lookup()
l_wide.LookupType = 1
l_wide.LookupFlag = 0
l_wide.SubTable = [sub_table]
l_wide.SubTableCount = 1
l_wide_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(l_wide)

# Contextual: when preceded by fullwidth glyph, switch to .wide
chain = otTables.ChainContextSubst()
chain.Format = 3
chain.BacktrackCoverage = [otTables.Coverage()]
glyph_to_id = {gn: i for i, gn in enumerate(glyph_order)}
chain.BacktrackCoverage[0].glyphs = sorted(fullwidth_glyphs, key=lambda gn: glyph_to_id[gn])
chain.BacktrackGlyphCount = 1

chain.InputCoverage = [otTables.Coverage()]
chain.InputCoverage[0].glyphs = sorted(['uni0305', 'uni0332', 'uni0336'], key=lambda gn: glyph_to_id[gn])
chain.InputGlyphCount = 1

chain.LookAheadCoverage = []
chain.LookAheadGlyphCount = 0

rec = otTables.SubstLookupRecord()
rec.SequenceIndex = 0
rec.LookupListIndex = l_wide_idx
chain.SubstLookupRecord = [rec]
chain.SubstCount = 1

l_chain = otTables.Lookup()
l_chain.LookupType = 6
l_chain.LookupFlag = 0
l_chain.SubTable = [chain]
l_chain.SubTableCount = 1
l_chain_idx = len(gsub.LookupList.Lookup)
gsub.LookupList.Lookup.append(l_chain)

# Register in calt
for fr in gsub.FeatureList.FeatureRecord:
    if fr.FeatureTag == 'calt':
        fr.Feature.LookupListIndex.append(l_chain_idx)
        fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)

# 7. Configure GDEF with Mark = 3 and preserve MarkGlyphSetsDef for OTS compliance
import copy
if 'GDEF' in src_mono:
    gdef = copy.deepcopy(src_mono['GDEF'])
    table = gdef.table
    valid_glyphs = set(font.getGlyphOrder())
    
    # Filter GlyphClassDef
    classDefs = table.GlyphClassDef.classDefs
    table.GlyphClassDef.classDefs = {gn: cls for gn, cls in classDefs.items() if gn in valid_glyphs}
    
    mark_names = {'uni0305', 'uni0305.wide', 'uni0332', 'uni0332.wide', 'uni0336', 'uni0336.wide'}
    for gn in valid_glyphs:
        if gn in mark_names:
            table.GlyphClassDef.classDefs[gn] = 3
        elif gn not in table.GlyphClassDef.classDefs and gn != '.notdef':
            table.GlyphClassDef.classDefs[gn] = 1
            
    # Filter MarkGlyphSetsDef
    if hasattr(table, 'MarkGlyphSetsDef') and table.MarkGlyphSetsDef:
        for cov in table.MarkGlyphSetsDef.Coverage:
            cov.glyphs = [gn for gn in cov.glyphs if gn in valid_glyphs]
            
    font['GDEF'] = gdef

# 8. Add minimal GPOS table to prevent HarfBuzz fallback mark jumping (keep lines straight & flat)
from fontTools.ttLib.tables.G_P_O_S_ import table_G_P_O_S_
gpos = table_G_P_O_S_()
gpos.table = otTables.GPOS()
gpos.table.Version = 0x00010000
gpos.table.ScriptList = otTables.ScriptList()
gpos.table.ScriptList.ScriptRecord = []
gpos.table.FeatureList = otTables.FeatureList()
gpos.table.FeatureList.FeatureRecord = []
gpos.table.LookupList = otTables.LookupList()
gpos.table.LookupList.Lookup = []

sr = otTables.ScriptRecord()
sr.ScriptTag = 'DFLT'
sr.Script = otTables.Script()
sr.Script.DefaultLangSys = otTables.LangSys()
sr.Script.DefaultLangSys.ReqFeatureIndex = 0xFFFF
sr.Script.DefaultLangSys.FeatureIndex = []
sr.Script.LangSysRecord = []
gpos.table.ScriptList.ScriptRecord.append(sr)

font['GPOS'] = gpos

# Update font family names
name_table = font['name']
for r in name_table.names:
    if r.nameID == 1: # Family
        r.string = "PlaneMono"
    elif r.nameID == 4: # Full Name
        r.string = "PlaneMono Regular"
    elif r.nameID == 6: # PostScript
        r.string = "PlaneMono-Regular"

# 8. Save TTF and WOFF2
print("7. Saving PlaneMono.ttf and PlaneMono.woff2...")
font.flavor = None
font.save('/mnt/c/workspace/planefont/PlaneMono.ttf')

font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneMono.woff2')

t_end = time.time()
print(f"Successfully generated PlaneMono fonts in {t_end - t_start:.2f}s!")
