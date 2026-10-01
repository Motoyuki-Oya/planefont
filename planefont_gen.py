#!/usr/bin/env python3
"""
PlaneFont Generator

Noto Sans CJK フォントに連続結合線を追加して PlaneText 用フォントを生成します。

対象の結合文字:
  - U+0305 COMBINING OVERLINE      (上線)
  - U+0332 COMBINING LOW LINE      (下線)
  - U+0336 COMBINING LONG STROKE OVERLAY (取り消し線)

処理内容:
  1. 各結合文字のグリフを「固定位置の全幅水平線」に置き換え
  2. GPOS mark-to-base positioning を追加し、全ベースグリフに対して
     結合文字が固定 Y 座標に配置されるようにする
     （レンダリングエンジンのヒューリスティック配置を上書き）

Requirements:
    pip install fonttools brotli  # brotli は WOFF2 出力に必要

Usage:
    # プロポーショナル版
    python planefont_gen.py NotoSansCJKjp-Regular.ttf PlaneSans-Regular.ttf \\
        --family-name "PlaneSans"

    # 等幅版
    python planefont_gen.py NotoSansMonoCJKjp-Regular.ttf PlaneMono-Regular.ttf \\
        --family-name "PlaneMono"

    # WOFF2 出力（拡張子で自動判定）
    python planefont_gen.py input.ttf output.woff2 --family-name "PlaneSans"

    # サブセット化 + WOFF2（使用文字を限定して軽量化）
    python planefont_gen.py input.ttf output.woff2 --family-name "PlaneSans" \\
        --subset-text-file chars.txt
"""

import argparse
import sys
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.misc.psCharStrings import T2CharString
    from fontTools.ttLib.tables import otTables
except ImportError as err:
    print(f"Error: 依存パッケージのインポートに失敗しました: {err}")
    print("  pip install fonttools")
    sys.exit(1)


# ============================================================
# 定数
# ============================================================

COMBINING_MARKS = {
    0x0305: "COMBINING OVERLINE",
    0x0332: "COMBINING LOW LINE",
    0x0336: "COMBINING LONG STROKE OVERLAY",
}


# ============================================================
# フォントメトリクス
# ============================================================

def get_font_metrics(font):
    """フォントのメトリクス情報を取得する"""
    upm = font['head'].unitsPerEm
    os2 = font['OS/2']
    post = font['post']

    cap_height = getattr(os2, 'sCapHeight', 0) or int(upm * 0.7)
    x_height = getattr(os2, 'sxHeight', 0) or int(upm * 0.5)

    return {
        'upm': upm,
        'ascender': os2.sTypoAscender,
        'descender': os2.sTypoDescender,
        'cap_height': cap_height,
        'x_height': x_height,
        'strikeout_position': os2.yStrikeoutPosition,
        'strikeout_size': os2.yStrikeoutSize,
        'underline_position': post.underlinePosition,
        'underline_thickness': post.underlineThickness,
    }


def calculate_line_params(metrics, overline_offset=0, thickness_scale=1.0):
    """各結合文字の線の位置と太さを計算する"""
    upm = metrics['upm']

    base_thickness = metrics['strikeout_size'] or max(int(upm * 0.05), 20)
    thickness = max(int(base_thickness * thickness_scale), 10)

    overline_y = metrics['ascender'] + overline_offset
    strikethrough_y = metrics['strikeout_position']
    underline_y = metrics['underline_position']

    return {
        0x0305: {'y': overline_y, 'thickness': thickness, 'name': 'overline'},
        0x0332: {'y': underline_y, 'thickness': thickness, 'name': 'underline'},
        0x0336: {'y': strikethrough_y, 'thickness': thickness, 'name': 'strikethrough'},
    }


# ============================================================
# グリフ描画
# ============================================================

def draw_line_glyph_ttf(font, glyph_name, x_min, y_min, x_max, y_max):
    """
    TTF フォントのグリフを水平線の矩形に置き換える

    GPOS mark-to-base によりマーク原点がベースグリフの原点に移動するため、
    線は x=0 から x=upm の範囲で描画する（ベースグリフ全体をカバー）。
    """
    glyf_table = font['glyf']

    pen = TTGlyphPen(None)
    pen.moveTo((x_min, y_min))
    pen.lineTo((x_max, y_min))
    pen.lineTo((x_max, y_max))
    pen.lineTo((x_min, y_max))
    pen.closePath()

    glyf_table[glyph_name] = pen.glyph()
    font['hmtx'].metrics[glyph_name] = (0, x_min)


def draw_line_glyph_cff(font, glyph_name, x_min, y_min, x_max, y_max):
    """CFF (OTF) フォントのグリフを水平線の矩形に置き換える"""
    cff = font['CFF ']
    top_dict = cff.cff.topDictIndex[0]
    charstrings = top_dict.CharStrings
    private = top_dict.Private

    nominal_width = getattr(private, 'nominalWidthX', 0)
    default_width = getattr(private, 'defaultWidthX', 0)
    desired_width = 0  # 結合文字

    dx = x_max - x_min
    dy = y_max - y_min
    program = []

    if desired_width != default_width:
        program.append(desired_width - nominal_width)

    program.extend([
        x_min, y_min, 'rmoveto',
        dx, 0, 'rlineto',
        0, dy, 'rlineto',
        -dx, 0, 'rlineto',
        'closepath',
        'endchar',
    ])

    charstring = T2CharString()
    charstring.program = program
    charstrings.charStrings[glyph_name] = charstring
    font['hmtx'].metrics[glyph_name] = (0, x_min)


def _ensure_mark_glyph(font, codepoint, default_name, is_cff=False):
    """フォント内に指定コードポイントのグリフが存在しない場合、新規作成して cmap に登録する"""
    cmap = font.getBestCmap()
    glyph_name = cmap.get(codepoint)
    if glyph_name:
        return glyph_name

    # 新しいユニークなグリフ名を決定
    glyph_order = font.getGlyphOrder()
    existing_set = set(glyph_order)
    candidate = default_name
    idx = 1
    while candidate in existing_set:
        candidate = f"{default_name}.{idx}"
        idx += 1
    glyph_name = candidate

    # glyf / CFF テーブルに空グリフを追加
    if is_cff:
        cff = font['CFF ']
        top_dict = cff.cff.topDictIndex[0]
        charstring = T2CharString()
        charstring.program = ['endchar']
        top_dict.CharStrings.charStrings[glyph_name] = charstring
    else:
        from fontTools.ttLib.tables._g_l_y_f import Glyph
        glyf_table = font['glyf']
        glyf_table.glyphs[glyph_name] = Glyph()

    # hmtx に幅0として登録
    font['hmtx'].metrics[glyph_name] = (0, 0)

    # glyphOrder を更新 (font と glyf の両方を同期)
    glyph_order.append(glyph_name)
    font.setGlyphOrder(glyph_order)
    if not is_cff and hasattr(font['glyf'], 'glyphOrder'):
        font['glyf'].glyphOrder = list(glyph_order)

    # 全ての Unicode cmap サブテーブルにマッピングを追加
    for subtable in font['cmap'].tables:
        if subtable.isUnicode():
            subtable.cmap[codepoint] = glyph_name

    return glyph_name


def modify_combining_marks(font, line_params, is_cff=False):
    """全対象結合文字のグリフを修正（無ければ作成）する"""
    upm = font['head'].unitsPerEm

    x_min = 0
    x_max = upm

    results = {}
    default_glyph_names = {
        0x0305: "overlinecomb",
        0x0332: "lowlinecomb",
        0x0336: "longstrokedoverlaycomb",
    }

    for codepoint, params in line_params.items():
        mark_name = COMBINING_MARKS[codepoint]
        def_name = default_glyph_names.get(codepoint, f"uni{codepoint:04X}")

        # グリフが存在しない場合は新規作成
        glyph_name = _ensure_mark_glyph(font, codepoint, def_name, is_cff=is_cff)

        y_min = params['y']
        y_max = params['y'] + params['thickness']

        print(f"  [PROC] U+{codepoint:04X} {mark_name}")
        print(f"         glyph: {glyph_name}")
        print(f"         rect: x=[{x_min}, {x_max}] y=[{y_min}, {y_max}]")

        try:
            if is_cff:
                draw_line_glyph_cff(font, glyph_name, x_min, y_min, x_max, y_max)
            else:
                draw_line_glyph_ttf(font, glyph_name, x_min, y_min, x_max, y_max)
            print(f"         Done ✓")
            results[codepoint] = True
        except Exception as e:
            print(f"         Failed ✗: {e}")
            results[codepoint] = False

    return results


# ============================================================
# GPOS mark-to-base positioning
# ============================================================

def _build_anchor(x, y):
    """OpenType Anchor を生成"""
    anchor = otTables.Anchor()
    anchor.Format = 1
    anchor.XCoordinate = x
    anchor.YCoordinate = y
    return anchor


def _build_mark_base_pos_subtable(mark_glyph_names, base_glyph_names, num_classes):
    """
    MarkBasePos (Format 1) サブテーブルを構築する

    全マークアンカー・全ベースアンカーを (0, 0) に設定する。
    これにより、マークグリフはベースグリフの原点に配置され、
    レンダリングエンジンのヒューリスティック配置が無効化される。
    マークグリフ自体が正しい Y 座標に線を描画しているため、
    追加の位置調整は不要。
    """
    subtable = otTables.MarkBasePos()
    subtable.Format = 1

    # Mark Coverage
    subtable.MarkCoverage = otTables.Coverage()
    subtable.MarkCoverage.glyphs = list(mark_glyph_names)

    # Base Coverage
    subtable.BaseCoverage = otTables.Coverage()
    subtable.BaseCoverage.glyphs = list(base_glyph_names)

    # Class count
    subtable.ClassCount = num_classes

    # Mark Array: 各マークに (class_id, anchor(0,0)) を設定
    subtable.MarkArray = otTables.MarkArray()
    subtable.MarkArray.MarkRecord = []
    for class_id in range(num_classes):
        record = otTables.MarkRecord()
        record.Class = class_id
        record.MarkAnchor = _build_anchor(0, 0)
        subtable.MarkArray.MarkRecord.append(record)
    subtable.MarkArray.MarkCount = num_classes

    # Base Array: 各ベースグリフに全クラス分の anchor(0,0) を設定
    subtable.BaseArray = otTables.BaseArray()
    subtable.BaseArray.BaseRecord = []
    for _ in base_glyph_names:
        record = otTables.BaseRecord()
        record.BaseAnchor = [_build_anchor(0, 0) for _ in range(num_classes)]
        subtable.BaseArray.BaseRecord.append(record)
    subtable.BaseArray.BaseCount = len(base_glyph_names)

    return subtable


def _build_lookup(subtable):
    """MarkBasePos Lookup (LookupType 4) を構築する"""
    lookup = otTables.Lookup()
    lookup.LookupType = 4  # MarkBasePos
    lookup.LookupFlag = 0
    lookup.SubTable = [subtable]
    lookup.SubTableCount = 1
    return lookup


def _ensure_gpos_table(font):
    """GPOS テーブルが存在しなければ新規作成する"""
    if 'GPOS' in font:
        return font['GPOS'].table

    from fontTools.ttLib.tables.G_P_O_S_ import table_G_P_O_S_

    gpos_wrapper = table_G_P_O_S_()
    gpos_tbl = otTables.GPOS()
    gpos_tbl.Version = 0x00010000

    # 空の Lookup List
    gpos_tbl.LookupList = otTables.LookupList()
    gpos_tbl.LookupList.Lookup = []

    # 空の Feature List
    gpos_tbl.FeatureList = otTables.FeatureList()
    gpos_tbl.FeatureList.FeatureRecord = []

    # DFLT Script
    langsys = otTables.LangSys()
    langsys.ReqFeatureIndex = 0xFFFF
    langsys.FeatureIndex = []
    langsys.FeatureCount = 0

    script = otTables.Script()
    script.DefaultLangSys = langsys
    script.LangSysRecord = []
    script.LangSysCount = 0

    sr = otTables.ScriptRecord()
    sr.ScriptTag = 'DFLT'
    sr.Script = script

    gpos_tbl.ScriptList = otTables.ScriptList()
    gpos_tbl.ScriptList.ScriptRecord = [sr]

    gpos_wrapper.table = gpos_tbl
    font['GPOS'] = gpos_wrapper

    return gpos_tbl


def _register_lookup_in_feature(gpos_tbl, lookup_index, feature_tag='mark'):
    """Lookup を feature に登録し、全 Script の LangSys に紐づける"""

    # 既存の 'mark' feature を探す
    found_feature_index = None
    if gpos_tbl.FeatureList and gpos_tbl.FeatureList.FeatureRecord:
        for i, fr in enumerate(gpos_tbl.FeatureList.FeatureRecord):
            if fr.FeatureTag == feature_tag:
                fr.Feature.LookupListIndex.append(lookup_index)
                fr.Feature.LookupCount = len(fr.Feature.LookupListIndex)
                found_feature_index = i
                break

    # なければ新規作成
    if found_feature_index is None:
        feature = otTables.Feature()
        feature.FeatureParams = None
        feature.LookupListIndex = [lookup_index]
        feature.LookupCount = 1

        fr = otTables.FeatureRecord()
        fr.FeatureTag = feature_tag
        fr.Feature = feature

        found_feature_index = len(gpos_tbl.FeatureList.FeatureRecord)
        gpos_tbl.FeatureList.FeatureRecord.append(fr)

        # 全 Script の DefaultLangSys と LangSysRecord に登録
        if gpos_tbl.ScriptList:
            for sr in gpos_tbl.ScriptList.ScriptRecord:
                if sr.Script.DefaultLangSys:
                    dls = sr.Script.DefaultLangSys
                    if dls.FeatureIndex is None:
                        dls.FeatureIndex = []
                    dls.FeatureIndex.append(found_feature_index)
                    dls.FeatureCount = len(dls.FeatureIndex)

                for lsr in (sr.Script.LangSysRecord or []):
                    ls = lsr.LangSys
                    if ls.FeatureIndex is None:
                        ls.FeatureIndex = []
                    ls.FeatureIndex.append(found_feature_index)
                    ls.FeatureCount = len(ls.FeatureIndex)


def add_gpos_mark_positioning(font, line_params):
    """
    GPOS mark-to-base positioning を追加する

    全ベースグリフに対して、結合文字がベースの原点(0,0)に配置されるよう
    MarkBasePos lookup を構築する。これにより：

    1. レンダリングエンジンのヒューリスティック配置（各文字の上端に追従）が
       無効化される
    2. マークグリフが描画した線が、指定した固定 Y 座標にそのまま表示される
    3. 大文字・小文字・漢字を問わず、同じ高さに線が引かれる
    """
    cmap = font.getBestCmap()
    glyph_order = font.getGlyphOrder()

    # マークグリフの特定
    mark_cps = [0x0305, 0x0332, 0x0336]
    mark_glyph_names = []
    for cp in mark_cps:
        gn = cmap.get(cp)
        if gn:
            mark_glyph_names.append(gn)

    if not mark_glyph_names:
        print("  マークグリフが見つかりません。GPOS 追加をスキップ")
        return

    num_classes = len(mark_glyph_names)

    # ベースグリフの特定（マークと .notdef 以外の全グリフ）
    mark_set = set(mark_glyph_names)
    base_glyph_names = [
        gn for gn in glyph_order
        if gn and gn not in mark_set and gn != '.notdef'
    ]

    print(f"  マークグリフ数: {num_classes}")
    print(f"  ベースグリフ数: {len(base_glyph_names)}")

    # MarkBasePos サブテーブル構築
    print(f"  MarkBasePos サブテーブルを構築中...")
    subtable = _build_mark_base_pos_subtable(
        mark_glyph_names, base_glyph_names, num_classes
    )

    # Lookup 構築
    lookup = _build_lookup(subtable)

    # GPOS テーブルに追加
    gpos_tbl = _ensure_gpos_table(font)

    lookup_index = len(gpos_tbl.LookupList.Lookup)
    gpos_tbl.LookupList.Lookup.append(lookup)

    # 'mark' feature に登録
    _register_lookup_in_feature(gpos_tbl, lookup_index, 'mark')

    print(f"  GPOS mark feature 追加完了 (lookup index: {lookup_index})")


# ============================================================
# フォント名更新
# ============================================================

def update_font_names(font, new_family_name):
    """フォントファミリー名を更新する (OFL 要件)"""
    name_table = font['name']

    for record in name_table.names:
        try:
            old_name = record.toUnicode()
        except UnicodeDecodeError:
            continue

        new_name = None

        if record.nameID == 1:  # Font Family
            new_name = new_family_name
        elif record.nameID == 4:  # Full Name
            parts = old_name.split()
            weights = ['Thin', 'Light', 'DemiLight', 'Regular', 'Medium',
                       'Bold', 'Black', 'Mono']
            style_parts = [p for p in parts if p in weights]
            if style_parts:
                new_name = f"{new_family_name} {' '.join(style_parts)}"
            else:
                new_name = new_family_name
        elif record.nameID == 6:  # PostScript Name
            if '-' in old_name:
                suffix = old_name.split('-')[-1]
                new_name = f"{new_family_name.replace(' ', '')}-{suffix}"
            else:
                new_name = new_family_name.replace(' ', '')

        if new_name:
            if record.platformID == 3:  # Windows
                record.string = new_name
            elif record.platformID == 1:  # Mac
                record.string = new_name


# ============================================================
# WOFF2 変換・サブセット化
# ============================================================

def convert_to_woff2(font, output_path):
    """フォントを WOFF2 形式で保存する"""
    try:
        import brotli  # noqa: F401 - fonttools が内部で使用
    except ImportError:
        print("  Error: WOFF2 出力には brotli が必要です")
        print("    pip install brotli")
        sys.exit(1)

    font.flavor = 'woff2'
    font.save(output_path)


def convert_to_woff(font, output_path):
    """フォントを WOFF 形式で保存する"""
    font.flavor = 'woff'
    font.save(output_path)


def subset_font(font, text=None, text_file=None, unicodes=None):
    """
    フォントをサブセット化する（使用文字だけを残す）

    CJK フォントは 15MB+ になるため、Web 用途では
    必要な文字だけに絞ることでファイルサイズを大幅に削減できる。
    """
    try:
        from fontTools.subset import Subsetter, Options
    except ImportError:
        print("  Error: サブセット化には fonttools の subset モジュールが必要です")
        sys.exit(1)

    options = Options()
    options.layout_features = ['*']  # 全 OpenType feature を保持
    options.name_IDs = ['*']         # 全 name record を保持
    options.notdef_outline = True

    subsetter = Subsetter(options=options)

    # サブセット対象の文字を収集
    codepoints = set()

    if text:
        codepoints.update(ord(c) for c in text)

    if text_file:
        text_path = Path(text_file)
        if text_path.exists():
            content = text_path.read_text(encoding='utf-8')
            codepoints.update(ord(c) for c in content)
        else:
            print(f"  Warning: テキストファイルが見つかりません: {text_file}")

    if unicodes:
        # "U+0000-007F,U+3000-30FF" のような形式をパース
        for part in unicodes.split(','):
            part = part.strip().replace('U+', '').replace('u+', '')
            if '-' in part:
                start, end = part.split('-')
                codepoints.update(range(int(start, 16), int(end, 16) + 1))
            else:
                codepoints.add(int(part, 16))

    # 結合文字は必ず含める
    codepoints.update([0x0305, 0x0332, 0x0336])

    if codepoints:
        subsetter.populate(unicodes=codepoints)
        subsetter.subset(font)
        print(f"  サブセット化完了: {len(codepoints)} コードポイント")
    else:
        print("  Warning: サブセット対象が空です。全グリフを保持します")


def detect_output_format(output_path):
    """出力ファイルの拡張子からフォーマットを判定する"""
    suffix = Path(output_path).suffix.lower()
    return {
        '.woff2': 'woff2',
        '.woff': 'woff',
        '.ttf': 'ttf',
        '.otf': 'otf',
    }.get(suffix, 'ttf')


def save_font(font, output_path):
    """出力形式を自動判定してフォントを保存する"""
    fmt = detect_output_format(output_path)

    if fmt == 'woff2':
        print(f"  Format: WOFF2")
        convert_to_woff2(font, output_path)
    elif fmt == 'woff':
        print(f"  Format: WOFF")
        convert_to_woff(font, output_path)
    else:
        print(f"  Format: {fmt.upper()}")
        font.save(output_path)

    # ファイルサイズを表示
    size = Path(output_path).stat().st_size
    if size > 1024 * 1024:
        print(f"  Size: {size / 1024 / 1024:.1f} MB")
    else:
        print(f"  Size: {size / 1024:.0f} KB")


# ============================================================
# メイン処理
# ============================================================

def process_font(input_path, output_path, family_name=None,
                 overline_offset=0, thickness_scale=1.0,
                 subset_text_file=None, subset_unicodes=None):
    """フォントを処理するメイン関数"""
    print("=" * 60)
    print("PlaneFont Generator")
    print("=" * 60)
    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print()

    # フォント読み込み
    print("Loading font...")
    font = TTFont(input_path)

    # フォーマット検出
    if 'CFF ' in font:
        is_cff = True
        print("  Format: OTF (CFF)")
    elif 'glyf' in font:
        is_cff = False
        print("  Format: TTF")
    else:
        print("  Error: 未対応のフォント形式です")
        sys.exit(1)

    # メトリクス取得
    metrics = get_font_metrics(font)
    print(f"  Units per Em:  {metrics['upm']}")
    print(f"  Ascender:      {metrics['ascender']}")
    print(f"  Descender:     {metrics['descender']}")
    print(f"  Cap Height:    {metrics['cap_height']}")
    print(f"  x-Height:      {metrics['x_height']}")
    print()

    # 線パラメータ計算
    line_params = calculate_line_params(metrics, overline_offset, thickness_scale)
    print("Line parameters:")
    for cp, p in line_params.items():
        print(f"  {p['name']:15s}: y={p['y']}, thickness={p['thickness']}")
    print()

    # Step 1: サブセット化（指定があれば先に行ってグリフ数を絞る）
    if subset_text_file or subset_unicodes:
        print("Step 1: Subsetting font")
        subset_font(font, text_file=subset_text_file, unicodes=subset_unicodes)
        print()

    # 静的グリフ追加に伴う Variable Font テーブルの不整合を防ぐ
    for var_tag in ['gvar', 'HVAR', 'VVAR', 'MVAR']:
        if var_tag in font:
            del font[var_tag]

    # サブセット適用後に一度シリアライズして再読み込みし、クリーンなテーブル状態を確立
    import io
    _buf = io.BytesIO()
    font.save(_buf)
    _buf.seek(0)
    font = TTFont(_buf)

    # メトリクス再取得
    metrics = get_font_metrics(font)
    line_params = calculate_line_params(metrics, overline_offset, thickness_scale)

    # Step 2: 結合文字グリフの置き換え・新規作成
    print("Step 2: Modifying combining mark glyphs")
    results = modify_combining_marks(font, line_params, is_cff)
    print()

    # Step 3: GPOS mark-to-base positioning 追加
    print("Step 3: Adding GPOS mark-to-base positioning")
    add_gpos_mark_positioning(font, line_params)
    print()

    # Step 4: フォント名更新
    if family_name:
        print(f"Step 4: Updating font name to '{family_name}'")
        update_font_names(font, family_name)
        print()

    # 保存（拡張子で形式を自動判定）
    print(f"Saving to: {output_path}")
    save_font(font, output_path)

    success = sum(1 for v in results.values() if v)
    total = len(results)
    print()
    print(f"Complete! ({success}/{total} glyphs modified, GPOS added)")
    print("=" * 60)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='PlaneFont Generator - フォントに連続結合線と GPOS を追加',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # プロポーショナル版を生成
  python planefont_gen.py NotoSansCJKjp-Regular.ttf PlaneSans-Regular.ttf \\
      --family-name "PlaneSans"

  # 等幅版を生成
  python planefont_gen.py NotoSansMonoCJKjp-Regular.ttf PlaneMono-Regular.ttf \\
      --family-name "PlaneMono"

  # WOFF2 出力（拡張子で自動判定）
  python planefont_gen.py input.ttf PlaneSans.woff2 --family-name "PlaneSans"

  # サブセット化 + WOFF2（使用文字を限定して軽量化）
  python planefont_gen.py input.ttf PlaneSans.woff2 --family-name "PlaneSans" \\
      --subset-text-file my_chars.txt

  # Unicode 範囲指定でサブセット化
  python planefont_gen.py input.ttf PlaneSans.woff2 --family-name "PlaneSans" \\
      --subset-unicodes "U+0000-007F,U+3000-30FF,U+4E00-9FFF"

  # overline を少し高くして線を細めに
  python planefont_gen.py input.ttf output.ttf \\
      --family-name "PlaneSans" \\
      --overline-offset 30 \\
      --thickness-scale 0.8
        """
    )

    parser.add_argument('input', help='入力フォントファイル (.ttf / .otf)')
    parser.add_argument('output',
                        help='出力フォントファイル (.ttf / .otf / .woff / .woff2)')
    parser.add_argument('--family-name', required=True,
                        help='新しいフォントファミリー名 (OFL 要件)')
    parser.add_argument('--overline-offset', type=int, default=0,
                        help='overline の Y 位置調整 (正=上, デフォルト: 0)')
    parser.add_argument('--thickness-scale', type=float, default=1.0,
                        help='線の太さ倍率 (デフォルト: 1.0)')
    parser.add_argument('--subset-text-file',
                        help='サブセット化: この文字列ファイルに含まれる文字だけを残す')
    parser.add_argument('--subset-unicodes',
                        help='サブセット化: Unicode 範囲指定 (例: "U+0000-007F,U+3000-30FF")')

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: 入力ファイルが見つかりません: {args.input}")
        sys.exit(1)

    process_font(
        args.input,
        args.output,
        family_name=args.family_name,
        overline_offset=args.overline_offset,
        thickness_scale=args.thickness_scale,
        subset_text_file=args.subset_text_file,
        subset_unicodes=args.subset_unicodes,
    )


if __name__ == '__main__':
    main()
