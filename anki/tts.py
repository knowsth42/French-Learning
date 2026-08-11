# -*- coding: utf-8 -*-
"""
用 edge-tts（微软 Edge 神经语音）批量生成法语发音。

音频缓存在 media/ 目录并随仓库提交，所以重新生成牌组时
不会重复请求网络——只有新增的词句才会联网合成。

用法（一般不用单独跑，build_decks.py 会自动调用）：
    pip install edge-tts
    python3 tts.py
"""

import asyncio
import hashlib
import os
import re
import sys

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")

# 词条用女声、例句用男声——顺便给听力一点声音多样性
VOICE_WORD = "fr-FR-DeniseNeural"
VOICE_SENTENCE = "fr-FR-HenriNeural"

# 词条稍微放慢，例句用正常语速
RATE_WORD = "-15%"
RATE_SENTENCE = "+0%"


def clean(text):
    """去掉 HTML 标签、挖空标记和中文注释，只留下要朗读的法语。"""
    t = re.sub(r"<[^>]+>", "", text)
    t = t.replace("**", "")
    t = re.sub(r"[（(][^）)]*[一-鿿][^）)]*[）)]", "", t)  # 去掉含中文的括号注释
    t = re.sub(r"[一-鿿]+", "", t)                        # 去掉裸中文
    t = t.replace("·", " ").replace("—", " ")
    t = re.sub(r"\s+", " ", t).strip(" ·-–—/")
    return t


def filename(text, voice):
    h = hashlib.sha1(f"{voice}|{text}".encode("utf-8")).hexdigest()[:14]
    return f"fr-{h}.mp3"


def _needed(items):
    """items: [(text, voice, rate)] → 返回尚未缓存的部分。"""
    todo = []
    for text, voice, rate in items:
        path = os.path.join(MEDIA_DIR, filename(text, voice))
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            todo.append((text, voice, rate, path))
    return todo


async def _one(sem, edge_tts, text, voice, rate, path, proxy):
    async with sem:
        for attempt in range(3):
            try:
                c = edge_tts.Communicate(text, voice, rate=rate, proxy=proxy)
                await c.save(path)
                if os.path.getsize(path) > 0:
                    return True
            except Exception as e:                       # noqa: BLE001
                if attempt == 2:
                    print(f"    ✗ {text[:40]!r}: {e}")
                    if os.path.exists(path) and os.path.getsize(path) == 0:
                        os.remove(path)
                    return False
                await asyncio.sleep(1.5 * (attempt + 1))
        return False


async def _run(todo, proxy):
    import edge_tts
    sem = asyncio.Semaphore(6)
    tasks = [_one(sem, edge_tts, t, v, r, p, proxy) for t, v, r, p in todo]
    done = 0
    results = []
    for coro in asyncio.as_completed(tasks):
        results.append(await coro)
        done += 1
        if done % 25 == 0 or done == len(tasks):
            print(f"    合成中… {done}/{len(tasks)}")
    return results


def synthesize(items):
    """
    items: [(text, kind)]，kind 为 'word' 或 'sentence'。
    返回 {(text, kind): 文件名}；生成失败的条目不会出现在结果里。
    """
    os.makedirs(MEDIA_DIR, exist_ok=True)
    spec = []
    mapping = {}
    for text, kind in items:
        t = clean(text)
        if not t:
            continue
        voice = VOICE_WORD if kind == "word" else VOICE_SENTENCE
        rate = RATE_WORD if kind == "word" else RATE_SENTENCE
        spec.append((t, voice, rate))
        mapping[(text, kind)] = (t, voice)

    spec = list(dict.fromkeys(spec))
    todo = _needed(spec)

    if todo:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            print("  ⚠ 未安装 edge-tts，跳过音频生成（pip install edge-tts）")
            todo = []
        else:
            print(f"  合成音频：需新增 {len(todo)} 条（已缓存 {len(spec) - len(todo)} 条）")
            proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
            asyncio.run(_run(todo, proxy))
    else:
        print(f"  音频全部命中缓存（{len(spec)} 条）")

    out = {}
    for key, (t, voice) in mapping.items():
        fn = filename(t, voice)
        if os.path.exists(os.path.join(MEDIA_DIR, fn)) and os.path.getsize(os.path.join(MEDIA_DIR, fn)) > 0:
            out[key] = fn
    return out


def media_paths(used_filenames):
    return [os.path.join(MEDIA_DIR, fn) for fn in sorted(set(used_filenames))]


if __name__ == "__main__":
    import data
    items = []
    for group in (data.FAUX_AMIS_1, data.FAUX_AMIS_2, data.FAUX_AMIS_3, data.CORE_WORDS):
        for e in group:
            items.append((e["fr"], "word"))
            if e.get("ex"):
                items.append((e["ex"], "sentence"))
    res = synthesize(items)
    print(f"可用音频 {len(res)} 条 → {MEDIA_DIR}")
    sys.exit(0)
