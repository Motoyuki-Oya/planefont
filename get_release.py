import urllib.request
import json

url = 'https://api.github.com/repos/nanxstats/noto-sans-mono-ligaturized/contents/fonts'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        for item in data:
            print(item['name'], item.get('download_url'))
except Exception as e:
    print(e)
