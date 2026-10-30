import json
import os
import urllib.request
import urllib.error
from pathlib import Path

BASE_DIR = Path(file).parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

TIMEOUT = 20

def fetch_json(url):
try:
req = urllib.request.Request(
url,
headers={"User-Agent": "Mozilla/5.0"}
)
with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
return json.loads(response.read().decode("utf-8"))
except Exception as e:
print(f"读取失败: {url} - {e}")
return None

def normalize(data):
if isinstance(data, list):
data = {"sites": data}

if not isinstance(data, dict):
    return None

if "sites" not in data and "data" in data:
    inner = data["data"]
    if isinstance(inner, dict):
        data = inner

return data

def merge_items(target, items, key):
if not isinstance(items, list):
return

existing = {
    str(item.get(key, ""))
    for item in target
    if isinstance(item, dict)
}

for item in items:
    if not isinstance(item, dict):
        continue

    value = str(item.get(key, ""))

    if value and value not in existing:
        target.append(item)
        existing.add(value)

def main():
sources_file = BASE_DIR / "sources.txt"

if not sources_file.exists():
    raise RuntimeError("sources.txt 不存在")

urls = [
    line.strip()
    for line in sources_file.read_text(
        encoding="utf-8"
    ).splitlines()
    if line.strip() and not line.strip().startswith("#")
]

result = {
    "spider": "",
    "wallpaper": "",
    "sites": [],
    "parses": [],
    "lives": []
}

successful = 0

for url in urls:
    print(f"正在读取: {url}")

    raw = fetch_json(url)
    if raw is None:
        continue

    data = normalize(raw)
    if data is None:
        continue

    successful += 1

    merge_items(result["sites"], data.get("sites"), "key")
    merge_items(result["parses"], data.get("parses"), "name")
    merge_items(result["lives"], data.get("lives"), "name")

    if not result["spider"] and data.get("spider"):
        result["spider"] = data["spider"]

    if not result["wallpaper"] and data.get("wallpaper"):
        result["wallpaper"] = data["wallpaper"]

if successful == 0:
    raise RuntimeError("所有配置源读取失败，保留原有配置")

output_file = OUTPUT_DIR / "tvbox.json"
temp_file = OUTPUT_DIR / "tvbox.json.tmp"

temp_file.write_text(
    json.dumps(result, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

temp_file.replace(output_file)

print("聚合完成")
print(f"成功读取配置源: {successful}")
print(f"影视站点: {len(result['sites'])}")
print(f"解析线路: {len(result['parses'])}")
print(f"直播源: {len(result['lives'])}")

if name == "main":
main()
