import base64
from fontTools.ttLib import TTFont

font = TTFont('/mnt/c/workspace/planefont/PlaneSans.ttf')

# Drop vertical layout tables that cause OTS rejection if desynchronized
for tag in ['vhea', 'vmtx', 'VVAR', 'BASE', 'STAT', 'avar', 'fvar', 'gasp']:
    if tag in font:
        del font[tag]
        print(f"Dropped {tag}")

# Save clean TTF
font.flavor = None
font.save('/mnt/c/workspace/planefont/PlaneSans.ttf')

# Also save WOFF2
font.flavor = 'woff2'
font.save('/mnt/c/workspace/planefont/PlaneSans.woff2')

with open('/mnt/c/workspace/planefont/PlaneSans.woff2', 'rb') as f:
    woff2_b64 = base64.b64encode(f.read()).decode('ascii')

with open('/mnt/c/workspace/planefont/preview.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
new_src = f"url('data:font/woff2;charset=utf-8;base64,{woff2_b64}') format('woff2')"
html = re.sub(r"url\([^)]+\)\s*format\('[^']+'\)", new_src, html)

with open('/mnt/c/workspace/planefont/preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Cleaned tables and updated preview.html with sanitized WOFF2 Base64!")
