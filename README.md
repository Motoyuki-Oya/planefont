# PlaneFont (PlaneMono & PlaneSans)

**PlaneFont** は、テキストエディタ「**PlaneText**」向けに開発された、**結合文字（オーバーライン・下線・取り消し線）の完全連続描画** と **プログラミング用合字（リガチャ）** を両立する日本語対応フォントファミリーです。

---

## 💡 開発の背景・解決する課題

通常、Unicode の結合文字（Combining Characters）：
- `U+0305` Combining Overline（上線・オーバーライン）
- `U+0332` Combining Low Line（下線・アンダーライン）
- `U+0336` Combining Long Stroke Overlay（取り消し線・打消線）

をエディタやブラウザでレンダリングすると、以下の課題が発生することがあります：

1. **文字と文字の間に隙間（ギャップ）が生じ、一本の線として繋がらない**
2. **文字の高さ（大文字・小文字・漢字・かな）によって線の高さが上下にガタつく（フォールバック位置調整による段差）**
3. **プログラミング用リガチャ（`=>` や `===` など）の間に結合文字が入ると合字が分解してしまう**
4. **半角文字と全角文字で線の長さが合わず、等幅レイアウト（1:2 比率）が崩れる**

**PlaneFont** は、OpenType テーブル（GSUB, GDEF, GPOS）およびグリフ設計を根本から最適化し、CSS の装飾（`text-decoration`）に依存せず、**フォント単体で完全な直線描画・等幅整列・リガチャ維持** を実現しました。

---

## 🔤 フォントラインナップ

### 1. `PlaneMono` (等幅プログラミングフォント)

- **ファイル**: `PlaneMono.woff2` / `PlaneMono.ttf`
- **等幅比率**: **半角 600 : 全角 1200**（UPM 1000、UDEV Gothic や 白源 (HackGen) と同一の 1:2 標準比率）
- **プログラミング用合字 (Ligatures)**:
  `nanxstats/noto-sans-mono-ligaturized` を統合。
  `=>`, `===`, `!==`, `!=`, `->`, `<-`, `<!--`, `-->`, `::`, `:=`, `>=`, `<=`, `&&`, `||`, `++`, `--` など多数のコード用合字に対応。
- **特製イースターエッグリガチャ (`>-)-` ✈️ & `-(-<` 🛩️)**:
  PlaneFont 独自の遊び心として、`>-)-`（東行き・右向き）または `-(-<`（西行き・左向き）と入力すると、4文字分の幅（600 × 4 = 2400）を保ったまま、文字の並び感を残すスリットと4本推進線が入った **4分割のスタイリッシュな飛行機シルエット** に変形します。結合線（下線・上線等）とも共存可能です。
- **リガチャ × 結合線の両立 (`IgnoreMarks`)**:
  合字ルックアップに `LookupFlag IgnoreMarks` を適用。取り消し線や下線が文字間に挟まれても合字が崩れず、**合字のまま各セルに切れ目なく線が引かれます**（例: `=̶>̶`, `=̶=̶=̶`）。
- **完全水平描画 (`GPOS`)**:
  最小準拠の GPOS テーブルを組み込むことで、レンダリングエンジン（HarfBuzz）による文字高に応じた上下ブレを防止。アセンダ/ディセンダに関わらず**高低差のない完全な水平線**を描画。
- **充実の和文収録数 (27,000文字規模)**:
  Noto Sans Mono CJK JP より、ひらがな・カタカナ・約物・全角英数記号・罫線・ブロック要素に加え、**JIS第1〜第4水準・常用・人名用を含む全漢字ブロック（U+4E00〜U+9FFF: 22,851文字）** をすべて 1200 幅（+100 センタリング）で完全収録。システムフォントへのフォールバックによる幅崩れを防ぎます。
- **ブラウザ規格適合 (`OTS`)**:
  すべての三次ベジェ曲線を `Cu2Qu` により標準二次ベジェ曲線へ変換し、OpenType Sanitizer (OTS) 検査をエラー 0 件でクリア（Firefox / Chrome / Edge / Safari 完全対応）。

---

### 2. `PlaneSans` (プロポーショナル版フォント)

- **ファイル**: `PlaneSans.woff2` / `PlaneSans.ttf`
- **ベース**: Noto Sans CJK JP
- **文字幅適合結合線 (`calt`)**:
  各文字の自然なプロポーショナル幅（W）を事前計測し、文脈置換（GSUB `calt`）によって先行文字の幅にミリ単位で追従する結合マーク（`[-W, 0]`）へ動的置換。プロポーショナル文章でも隙間やはみ出しの一切ない直線を実現。

---

## 📊 1:2 等幅カラム配置の検証例

`PlaneMono` では、半角20文字と全角10文字がピクセル単位で完全に同一定規（カラム）上に揃います：

```text
| 12345678901234567890 |  (半角数字定規 20文字)
| 01234567890123456789 |  (半角数字 20文字)
| abcdefghijklmnopqrst |  (半角小文字 20文字)
| ABCDEFGHIJKLMNOPQRST |  (半角大文字 20文字)
| あいうえおかきくけこ |  (全角ひらがな 10文字)
| 漢字漢文漢字漢文漢字 |  (全角漢字 10文字)
| 平̅均̅値̅下̅線̅削̅除̅済̅み̅テ̅ |  (全角漢字+上線 10文字)
| 平̲均̲値̲下̲線̲削̲除̲済̲み̲テ̲ |  (全角漢字+下線 10文字)
| 平̶均̶値̶下̶線̶削̶除̶済̶み̶テ̶ |  (全角漢字+取消 10文字)
| H̅e̅l̅l̅o̅W̅o̅r̅l̅d̅P̅l̅a̅n̅e̅M̅o̅n̅o̅!̅ |  (半角英字+上線 20文字)
| H̲e̲l̲l̲o̲W̲o̲r̲l̲d̲P̲l̲a̲n̲e̲M̲o̲n̲o̲!̲ |  (半角英字+下線 20文字)
| H̶e̶l̶l̶o̶W̶o̶r̶l̶d̶P̶l̶a̶n̶e̶M̶o̶n̶o̶!̶ |  (半角英字+取消 20文字)
| ==================== |  (区切り線 20文字)
```

---

## 🖥 プレビュー

リポジトリ内の `preview.html` をブラウザで開くことで、以下をインタラクティブにテストできます：

- **PlaneMono / PlaneSans のタブ切り替え**
- **リアルタイムフォントサイズ変更スライダー (14px〜64px)**
- **プログラミング用合字一覧 ＆ JavaScript 実コードスニペット**
- **合字 × 結合線の同時描画テスト**
- **1:2 等幅カラム配置グリッド検証**
- **ブラウザのフォント読み込み状態インジケーター**

---

## 🛠 ビルド方法

WSL または Linux 環境（Python 3.10+）でビルド可能です。

### 必要パッケージのインストール

```bash
pip install fonttools brotli uharfbuzz opentype-sanitizer
```

### ソースフォントの準備

1. `LigaNotoSansMono-Regular.otf`（nanxstats/noto-sans-mono-ligaturized）
2. `NotoSansMonoCJKjp-Regular.otf`（Google Noto CJK Release）
3. `NotoSansJP-Regular.ttf`（PlaneSans ビルド用）

### ビルド実行

```bash
# 等幅版 PlaneMono の生成 (.woff2 / .ttf)
python3 make_planemono.py

# プロポーショナル版 PlaneSans の生成 (.woff2 / .ttf)
python3 make_planesans.py

# プレビューHTMLの生成・更新
python3 build_preview.py
```

---

## 📄 ライセンス

本フォントソフトウェアは **SIL Open Font License, Version 1.1** のもとで配布されています。
詳細は [LICENSE](./LICENSE) をご参照ください。

### 謝辞・ベースプロジェクト
- **Noto Sans CJK / Noto Sans Mono CJK** (c) Adobe Systems Incorporated, Google LLC
- **LigaNotoSansMono** (c) Nan Xiao
- **PlaneFont Modifications** (c) 2026 Motoyuki Oya / PlaneText Project
