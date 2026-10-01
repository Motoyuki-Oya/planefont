import zipfile
import os

with zipfile.ZipFile('/tmp/11_NotoSansMonoCJKjp.zip') as z:
    z.extractall('/tmp/noto_mono')

for f in os.listdir('/tmp/noto_mono'):
    path = os.path.join('/tmp/noto_mono', f)
    print(f, os.path.getsize(path))
