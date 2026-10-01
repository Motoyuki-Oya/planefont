import base64
from fontTools.ttLib import TTFont

# Check if PlaneSans.woff2 passes basic validation
font = TTFont('/mnt/c/workspace/planefont/PlaneSans.woff2')
print("Tables in PlaneSans.woff2:", list(font.keys()))

# Also create a pure uncompressed TTF version to test
font.flavor = None
font.save('/mnt/c/workspace/planefont/PlaneSans.ttf')

with open('/mnt/c/workspace/planefont/PlaneSans.ttf', 'rb') as f:
    ttf_b64 = base64.b64encode(f.read()).decode('ascii')

print("TTF size:", len(ttf_b64), "bytes base64")

# Update preview.html to use TTF base64, and add font loading detection JS
html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>PlaneSans Font Preview</title>
  <style>
    @font-face {{
      font-family: 'PlaneSans';
      src: url('data:font/truetype;charset=utf-8;base64,{ttf_b64}') format('truetype');
      font-weight: normal;
      font-style: normal;
    }}

    body {{
      margin: 40px;
      background-color: #f7f9fa;
      color: #222;
      font-family: 'PlaneSans', monospace;
      font-feature-settings: "mark" 1, "calt" 1, "liga" 1;
      line-height: 2.2;
    }}

    .status {{
      padding: 12px 16px;
      border-radius: 6px;
      margin-bottom: 20px;
      font-weight: bold;
    }}
    .loaded {{ background: #e6ffed; color: #22863a; border: 1px solid #34d058; }}
    .failed {{ background: #ffeef0; color: #cb2431; border: 1px solid #d73a49; }}

    .card {{
      background: white;
      padding: 30px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      max-width: 800px;
      margin: 0 auto;
    }}

    h1 {{
      font-size: 24px;
      border-bottom: 2px solid #e1e4e8;
      padding-bottom: 12px;
    }}

    .sample-box {{
      font-size: 32px;
      background: #fafbfc;
      border: 1px solid #e1e4e8;
      border-radius: 6px;
      padding: 16px 20px;
      margin: 16px 0;
      font-family: 'PlaneSans';
    }}

    .label {{
      font-size: 14px;
      color: #666;
      margin-top: 18px;
      margin-bottom: 4px;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>PlaneSans フォント テストプレビュー</h1>
    <div id="font-status" class="status">フォント読み込み判定中...</div>

    <div class="label">1. オーバーライン (U+0305) - 大文字・小文字混合</div>
    <div class="sample-box">
      H̅e̅l̅l̅o̅ W̅o̅r̅l̅d̅
    </div>

    <div class="label">2. オーバーライン (U+0305) - 日本語 (ひらがな・漢字)</div>
    <div class="sample-box">
      平̅均̅値̅　あ̅い̅う̅え̅お̅
    </div>

    <div class="label">3. 下線 (U+0332)</div>
    <div class="sample-box">
      H̲e̲l̲l̲o̲ W̲o̲r̲l̲d̲　下̲線̲テ̲ス̲ト̲
    </div>

    <div class="label">4. 取り消し線 (U+0336)</div>
    <div class="sample-box">
      H̶e̶l̶l̶o̶ W̶o̶r̶l̶d̶　削̶除̶済̶み̶テ̶キ̶ス̶ト̶
    </div>
  </div>

  <script>
    document.fonts.load("32px 'PlaneSans'").then(function(fonts) {{
      var statusEl = document.getElementById('font-status');
      if (document.fonts.check("32px 'PlaneSans'")) {{
        statusEl.className = 'status loaded';
        statusEl.textContent = '✅ PlaneSans フォントの読み込みに成功しました (適用中)';
      }} else {{
        statusEl.className = 'status failed';
        statusEl.textContent = '❌ PlaneSans フォントの読み込みに失敗しました (システムフォントにフォールバック中)';
      }}
    }}).catch(function(err) {{
      var statusEl = document.getElementById('font-status');
      statusEl.className = 'status failed';
      statusEl.textContent = '❌ フォント読み込みエラー: ' + err;
    }});
  </script>
</body>
</html>
"""

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Updated preview.html with TTF Base64 and font loading status check!")
