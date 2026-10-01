import base64

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    sans_b64 = base64.b64encode(f.read()).decode('ascii')

with open('/mnt/c/workspace/planefont/PlaneMono.woff2', 'rb') as f:
    mono_b64 = base64.b64encode(f.read()).decode('ascii')

html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <title>PlaneText フォント プレビュー (PlaneSans & PlaneMono)</title>
  <style>
    @font-face {{
      font-family: 'PlaneSans';
      src: url('data:font/woff2;charset=utf-8;base64,{sans_b64}') format('woff2');
      font-weight: normal;
      font-style: normal;
    }}

    @font-face {{
      font-family: 'PlaneMono';
      src: url('data:font/woff2;charset=utf-8;base64,{mono_b64}') format('woff2');
      font-weight: normal;
      font-style: normal;
    }}

    body {{
      margin: 0;
      padding: 30px;
      background-color: #f0f2f5;
      color: #1a1a1a;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      line-height: 1.8;
    }}

    .container {{
      max-width: 960px;
      margin: 0 auto;
    }}

    .header-card {{
      background: white;
      padding: 24px 30px;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
      margin-bottom: 24px;
    }}

    h1 {{
      margin: 0 0 10px 0;
      font-size: 26px;
      color: #0f172a;
    }}

    .subtitle {{
      color: #64748b;
      font-size: 14px;
      margin-bottom: 20px;
    }}

    .tab-bar {{
      display: flex;
      gap: 12px;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 8px;
    }}

    .tab-btn {{
      padding: 10px 20px;
      font-size: 15px;
      font-weight: 600;
      border: none;
      background: none;
      color: #64748b;
      cursor: pointer;
      border-radius: 6px;
      transition: all 0.2s;
    }}

    .tab-btn:hover {{
      background: #f1f5f9;
      color: #0f172a;
    }}

    .tab-btn.active {{
      background: #2563eb;
      color: white;
    }}

    .control-panel {{
      margin-top: 18px;
      padding: 14px 20px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 16px;
    }}

    .status-badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: bold;
      margin-left: 10px;
    }}
    .loaded {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
    .failed {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}

    .section-card {{
      background: white;
      padding: 28px 32px;
      border-radius: 12px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.06);
      margin-bottom: 24px;
    }}

    h2 {{
      font-size: 18px;
      margin: 0 0 16px 0;
      color: #1e293b;
      display: flex;
      align-items: center;
    }}

    .sample-box {{
      font-size: 28px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 18px 24px;
      margin: 12px 0 20px 0;
      white-space: pre-wrap;
      word-break: break-all;
    }}

    .font-mono {{
      font-family: 'PlaneMono', monospace;
      font-feature-settings: "calt" 1, "liga" 1, "mark" 1;
    }}

    .font-sans {{
      font-family: 'PlaneSans', sans-serif;
      font-feature-settings: "calt" 1, "liga" 1, "mark" 1;
    }}

    .code-grid {{
      background: #0f172a;
      color: #f8fafc;
      border-radius: 8px;
      padding: 20px 24px;
      font-size: 20px;
      line-height: 1.7;
      margin: 12px 0 20px 0;
      white-space: pre;
      overflow-x: auto;
    }}

    .label {{
      font-size: 13px;
      font-weight: 600;
      color: #475569;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-top: 14px;
      margin-bottom: 4px;
    }}

    .tag {{
      display: inline-block;
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 3px;
      background: #e2e8f0;
      color: #475569;
      margin-left: 8px;
      vertical-align: middle;
      text-transform: none;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header-card">
      <h1>PlaneText フォント プレビュー</h1>
      <div class="subtitle">
        結合文字（オーバーライン・下線・取り消し線）の完全連続描画 ＆ プログラミング用リガチャ
      </div>

      <div class="tab-bar">
        <button class="tab-btn active" onclick="switchTab('mono')">PlaneMono (等幅・リガチャ)</button>
        <button class="tab-btn" onclick="switchTab('sans')">PlaneSans (プロポーショナル)</button>
      </div>

      <div class="control-panel">
        <label for="size-slider" style="font-weight: 600; font-size: 14px; color: #334155;">フォントサイズ:</label>
        <input type="range" id="size-slider" min="14" max="64" value="28" style="flex: 1; cursor: pointer;">
        <span id="size-label" style="font-weight: 700; font-size: 15px; color: #0f172a; min-width: 45px;">28px</span>
        <span id="status-mono" class="status-badge">PlaneMono: 読込確認中</span>
        <span id="status-sans" class="status-badge">PlaneSans: 読込確認中</span>
      </div>
    </div>

    <!-- TAB 1: PlaneMono -->
    <div id="tab-mono">
      <div class="section-card">
        <h2>1. プログラミング用リガチャ (Programming Ligatures)<span class="tag">Fira Code / LigaNoto</span></h2>
        <div class="label">アロー・等価演算子・比較演算子・論理演算子</div>
        <div class="sample-box font-mono sample-target">
=&gt;  -&gt;  &lt;-  &lt;=  &gt;=  ===  !==  !=  ==  &lt;!--  --&gt;  ::  :=  ++  --  &amp;&amp;  ||
        </div>

        <div class="label">実際のコードスニペット表示</div>
        <div class="code-grid font-mono sample-code-target">
const processItems = async (items) =&gt; {{
  if (items.length !== 0 &amp;&amp; status === "READY") {{
    return items.filter(x =&gt; x != null);
  }}
  // &lt;!-- 処理完了 --&gt;
  return null;
}};
        </div>
      </div>

      <div class="section-card">
        <h2>2. リガチャ × 結合線 (Ligatures + Continuous Combining Lines)<span class="tag">同時適用</span></h2>
        <div class="label">取り消し線 (U+0336) とリガチャの共存</div>
        <div class="sample-box font-mono sample-target">
=&#x0336;&gt;&#x0336;   =&#x0336;=&#x0336;=&#x0336;   !&#x0336;=&#x0336;=&#x0336;   !&#x0336;=&#x0336;   -&#x0336;&gt;&#x0336;   &lt;&#x0336;=&#x0336;   &gt;&#x0336;=&#x0336;
fn = () =&#x0336;&gt;&#x0336; {{ return x =&#x0336;=&#x0336;=&#x0336; y; }}
        </div>

        <div class="label">下線 (U+0332) とリガチャの共存</div>
        <div class="sample-box font-mono sample-target">
=&#x0332;&gt;&#x0332;   =&#x0332;=&#x0332;=&#x0332;   !&#x0332;=&#x0332;   i&#x0332;+&#x0332;+&#x0332;   c&#x0332;o&#x0332;n&#x0332;s&#x0332;t&#x0332;
        </div>
      </div>

      <div class="section-card">
        <h2>3. 結合線（オーバーライン・下線・取り消し線）連続性テスト<span class="tag">半角600 / 全角1200 自動切替</span></h2>
        <div class="label">オーバーライン (U+0305) - 英数・記号・日本語</div>
        <div class="sample-box font-mono sample-target">
H&#x0305;e&#x0305;l&#x0305;l&#x0305;o&#x0305; W&#x0305;o&#x0305;r&#x0305;l&#x0305;d&#x0305; 平&#x0305;均&#x0305;値&#x0305; あ&#x0305;い&#x0305;う&#x0305;え&#x0305;お&#x0305;
        </div>

        <div class="label">下線 (U+0332) - 英数・記号・日本語</div>
        <div class="sample-box font-mono sample-target">
H&#x0332;e&#x0332;l&#x0332;l&#x0332;o&#x0332; W&#x0332;o&#x0332;r&#x0332;l&#x0332;d&#x0332; 下&#x0332;線&#x0332;テ&#x0332;ス&#x0332;ト&#x0332;
        </div>

        <div class="label">取り消し線 (U+0336) - 隙間のない完全な直線</div>
        <div class="sample-box font-mono sample-target">
H&#x0336;e&#x0336;l&#x0336;l&#x0336;o&#x0336; W&#x0336;o&#x0336;r&#x0336;l&#x0336;d&#x0336; 削&#x0336;除&#x0336;済&#x0336;み&#x0336;テ&#x0336;キ&#x0336;ス&#x0336;ト&#x0336;ー&#x0336;
        </div>
      </div>

      <div class="section-card">
        <h2>4. 等幅 1:2 カラム配置検証 (Monospace Alignment Grid)<span class="tag">半角2文字 = 全角1文字</span></h2>
        <div class="label">上下のカラムが完全に一致するか検証</div>
        <div class="sample-box font-mono" style="font-size: 20px; line-height: 1.7;">
| 12345678901234567890 |
| 01234567890123456789 |
| abcdefghijklmnopqrst |
| ABCDEFGHIJKLMNOPQRST |
| あいうえおかきくけこ |
| 漢字漢文漢字漢文漢字 |
| 平̅均̅値̅下̅線̅削̅除̅済̅み̅テ̅ |
| 平̲均̲値̲下̲線̲削̲除̲済̲み̲テ̲ |
| 平̶均̶値̶下̶線̶削̶除̶済̶み̶テ̶ |
| H̅e̅l̅l̅o̅W̅o̅r̅l̅d̅P̅l̅a̅n̅e̅M̅o̅n̅o̅!̅ |
| H̲e̲l̲l̲o̲W̲o̲r̲l̲d̲P̲l̲a̲n̲e̲M̲o̲n̲o̲!̲ |
| H̶e̶l̶l̶o̶W̶o̶r̶l̶d̶P̶l̶a̶n̶e̶M̶o̶n̶o̶!̶ |
| ==================== |
        </div>
      </div>
    </div>

    <!-- TAB 2: PlaneSans -->
    <div id="tab-sans" style="display: none;">
      <div class="section-card">
        <h2>PlaneSans (プロポーショナル版)<span class="tag">文字幅適合結合線</span></h2>

        <div class="label">オーバーライン (U+0305)</div>
        <div class="sample-box font-sans sample-target">
H&#x0305;e&#x0305;l&#x0305;l&#x0305;o&#x0305; W&#x0305;o&#x0305;r&#x0305;l&#x0305;d&#x0305; 平&#x0305;均&#x0305;値&#x0305; あ&#x0305;い&#x0305;う&#x0305;え&#x0305;お&#x0305;
        </div>

        <div class="label">下線 (U+0332)</div>
        <div class="sample-box font-sans sample-target">
H&#x0332;e&#x0332;l&#x0332;l&#x0332;o&#x0332; W&#x0332;o&#x0332;r&#x0332;l&#x0332;d&#x0332; 下&#x0332;線&#x0332;テ&#x0332;ス&#x0332;ト&#x0332;
        </div>

        <div class="label">取り消し線 (U+0336)</div>
        <div class="sample-box font-sans sample-target">
H&#x0336;e&#x0336;l&#x0336;l&#x0336;o&#x0336; W&#x0336;o&#x0336;r&#x0336;l&#x0336;d&#x0336; 削&#x0336;除&#x0336;済&#x0336;み&#x0336;テ&#x0336;キ&#x0336;ス&#x0336;ト&#x0336;ー&#x0336;
        </div>
      </div>
    </div>
  </div>

  <script>
    function switchTab(name) {{
      var tabMono = document.getElementById('tab-mono');
      var tabSans = document.getElementById('tab-sans');
      var btns = document.querySelectorAll('.tab-btn');
      if (name === 'mono') {{
        tabMono.style.display = 'block';
        tabSans.style.display = 'none';
        btns[0].classList.add('active');
        btns[1].classList.remove('active');
      }} else {{
        tabMono.style.display = 'none';
        tabSans.style.display = 'block';
        btns[0].classList.remove('active');
        btns[1].classList.add('active');
      }}
    }}

    var slider = document.getElementById('size-slider');
    var label = document.getElementById('size-label');
    var targets = document.querySelectorAll('.sample-target');

    slider.addEventListener('input', function() {{
      var sz = this.value + 'px';
      label.textContent = sz;
      targets.forEach(function(el) {{
        el.style.fontSize = sz;
      }});
    }});

    // Font loading verification
    Promise.all([
      document.fonts.load('24px PlaneMono', '=>あ'),
      document.fonts.load('24px PlaneSans', 'Helloあ')
    ]).then(function() {{
      var monoLoaded = document.fonts.check('24px PlaneMono', '=>');
      var sansLoaded = document.fonts.check('24px PlaneSans', 'Hello');

      var elMono = document.getElementById('status-mono');
      if (monoLoaded) {{
        elMono.textContent = 'PlaneMono: 正常読込 (OK)';
        elMono.className = 'status-badge loaded';
      }} else {{
        elMono.textContent = 'PlaneMono: 読込失敗';
        elMono.className = 'status-badge failed';
      }}

      var elSans = document.getElementById('status-sans');
      if (sansLoaded) {{
        elSans.textContent = 'PlaneSans: 正常読込 (OK)';
        elSans.className = 'status-badge loaded';
      }} else {{
        elSans.textContent = 'PlaneSans: 読込失敗';
        elSans.className = 'status-badge failed';
      }}
    }}).catch(function(err) {{
      console.error('Font load error:', err);
    }});
  </script>
</body>
</html>
"""

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print("preview.html updated successfully!")
