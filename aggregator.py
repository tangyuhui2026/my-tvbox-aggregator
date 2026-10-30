# -*- coding: utf-8 -*-

import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime


# ==============================
# 基础设置
# ==============================

BASE_DIR = Path(__file__).parent

SOURCES_FILE = BASE_DIR / "sources.txt"

OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "tvbox.json"

TIMEOUT = 30


# 强制使用 UTF-8，避免中文输出报 ASCII 编码错误
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ==============================
# 读取配置源
# ==============================

def fetch_json(url):
    try:
        print(f"\n正在读取: {url}")

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json, */*"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            status = response.status
            content_type = response.headers.get(
                "Content-Type", ""
            )

            raw = response.read()

            print(f"HTTP 状态码: {status}")
            print(f"Content-Type: {content_type}")
            print(f"读取大小: {len(raw)} 字节")

        if not raw:
            print("读取失败：返回内容为空")
            return None

        # 兼容 UTF-8 BOM
        text = raw.decode("utf-8-sig", errors="replace")

        try:
            data = json.loads(text)
            print("JSON 解析成功")
            return data

        except json.JSONDecodeError as e:

            print("JSON 格式错误！")
            print(f"错误行: {e.lineno}")
            print(f"错误列: {e.colno}")
            print(f"错误位置: {e.pos}")

            # 打印错误位置附近的内容，方便定位
            start = max(0, e.pos - 150)
            end = min(len(text), e.pos + 150)

            print("错误位置附近的内容：")
            print(repr(text[start:end]))

            return None

    except urllib.error.HTTPError as e:
        print(f"HTTP 请求失败: {url}")
        print(f"状态码: {e.code}")
        return None

    except urllib.error.URLError as e:
        print(f"网络请求失败: {url}")
        print(f"原因: {e.reason}")
        return None

    except Exception as e:
        print(f"读取失败: {url}")
        print(f"错误信息: {e}")
        return None


# ==============================
# 标准化配置格式
# ==============================

def normalize(data):

    if isinstance(data, list):
        data = {
            "sites": data
        }

    if not isinstance(data, dict):
        print("配置格式错误：JSON 根节点不是对象或数组")
        return None

    # 兼容 data 嵌套格式
    if (
        "sites" not in data
        and isinstance(data.get("data"), dict)
    ):
        data = {
            **data,
            **data["data"]
        }

    # 确保列表字段格式正确
    list_fields = [
        "sites",
        "parses",
        "lives"
    ]

    for field in list_fields:

        value = data.get(field, [])

        if value is None:
            data[field] = []

        elif isinstance(value, list):
            data[field] = value

        else:
            print(f"警告：字段 {field} 不是数组，已忽略")
            data[field] = []

    return data


# ==============================
# 列表去重合并
# ==============================

def merge_items(old_list, new_list, key):

    result = []
    seen = set()

    for item in old_list + new_list:

        if not isinstance(item, dict):
            # 非对象数据也保留，并按内容去重
            identity = json.dumps(
                item,
                ensure_ascii=False,
                sort_keys=True
            )

        else:
            identity = item.get(key)

            if identity is None or identity == "":
                identity = json.dumps(
                    item,
                    ensure_ascii=False,
                    sort_keys=True
                )

        identity = str(identity)

        if identity not in seen:
            seen.add(identity)
            result.append(item)

    return result


# ==============================
# 读取所有来源
# ==============================

def read_sources():

    if not SOURCES_FILE.exists():
        raise FileNotFoundError(
            f"找不到来源文件: {SOURCES_FILE}"
        )

    with open(
        SOURCES_FILE,
        "r",
        encoding="utf-8-sig"
    ) as f:

        urls = [
            line.strip()
            for line in f
            if line.strip()
            and not line.strip().startswith("#")
        ]

    print(f"发现配置源数量: {len(urls)}")

    if not urls:
        raise RuntimeError("sources.txt 中没有有效配置源")

    return urls


# ==============================
# 主程序
# ==============================

def main():

    print("=" * 50)
    print("TVBox 配置聚合器启动")
    print("运行时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    urls = read_sources()

    result = {
        "spider": "",
        "wallpaper": "",
        "sites": [],
        "parses": [],
        "lives": []
    }

    successful = 0
    failed = 0

    for url in urls:

        data = fetch_json(url)

        if data is None:
            failed += 1
            print("跳过这个配置源")
            continue

        data = normalize(data)

        if data is None:
            failed += 1
            print("配置格式不符合要求，跳过")
            continue

        successful += 1

        print("开始合并配置...")

        # 合并 spider
        if not result["spider"] and data.get("spider"):
            result["spider"] = data["spider"]

        # 合并 wallpaper
        if not result["wallpaper"] and data.get("wallpaper"):
            result["wallpaper"] = data["wallpaper"]

        # 合并 sites
        result["sites"] = merge_items(
            result["sites"],
            data["sites"],
            "key"
        )

        # 合并 parses
        result["parses"] = merge_items(
            result["parses"],
            data["parses"],
            "name"
        )

        # 合并 lives
        result["lives"] = merge_items(
            result["lives"],
            data["lives"],
            "name"
        )

    # ==============================
    # 统计结果
    # ==============================

    print("\n" + "=" * 50)
    print("配置读取完成")
    print(f"成功来源: {successful}")
    print(f"失败来源: {failed}")
    print(f"影视站点: {len(result['sites'])}")
    print(f"解析接口: {len(result['parses'])}")
    print(f"直播配置: {len(result['lives'])}")
    print("=" * 50)

    # 所有来源失败时，不覆盖原文件
    if successful == 0:
        raise RuntimeError(
            "所有配置源读取失败，保留原有配置"
        )

    # ==============================
    # 保存文件
    # ==============================

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_file = OUTPUT_DIR / "tvbox.tmp.json"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2
        )

    # 先写临时文件，成功后再替换正式文件
    temp_file.replace(OUTPUT_FILE)

    print("\n配置聚合成功！")
    print(f"输出文件: {OUTPUT_FILE}")


# ==============================
# 程序入口
# ==============================

if __name__ == "__main__":
    main()
