import base64
import re

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('ascii')

with open('/mnt/c/workspace/planefont/preview.html', 'r', encoding='utf-8') as f:
    html = f.read()

new_src = f"url('data:font/woff2;charset=utf-8;base64,{b64}') format('woff2')"
html = re.sub(r"url\([^)]+\)\s*format\('woff2'\)", new_src, html)

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("preview.html updated with inline base64 font!")
