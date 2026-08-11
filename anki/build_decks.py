#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 DELF B2 一年计划配套 Anki 牌组（含法语发音）。

用法:
    pip install genanki edge-tts
    python3 build_decks.py

输出:
    dist/French-DELF-B2.apkg     ← 双击导入 Anki
    dist/csv/*.csv               ← 备用
    media/*.mp3                  ← 音频缓存（随仓库提交，重建时不必联网）
"""

import csv
import html
import os
import re

import genanki

import data
import tts

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "dist")
CSV_DIR = os.path.join(OUT_DIR, "csv")

# ---------------------------------------------------------------------------
# 词性 → 显示标签 + 阴阳性着色
# ---------------------------------------------------------------------------
POS_LABEL = {
    "n.m.":         ("名词 · 阳性 ♂", "m"),
    "n.f.":         ("名词 · 阴性 ♀", "f"),
    "v.":           ("动词", ""),
    "v.pron.":      ("代动词", ""),
    "v.imp.":       ("无人称动词", ""),
    "adj.":         ("形容词", ""),
    "adv.":         ("副词", ""),
    "conj.":        ("连词", ""),
    "prép.":        ("介词", ""),
    "loc.":         ("固定短语", ""),
    "expr.":        ("惯用表达", ""),
    "pron.":        ("代词", ""),
    "conj. / n.m.": ("连词 / 名词 · 阳性 ♂", "m"),
    "adj. / pron.": ("形容词 / 代词", ""),
}


def pos_badge(pos):
    """把词性代码渲染成带颜色的标签。"""
    label, gender = POS_LABEL.get(pos, (pos, ""))
    cls = {"m": "pos-m", "f": "pos-f"}.get(gender, "pos-n")
    return f'<span class="pos {cls}">{label}</span>'


# ---------------------------------------------------------------------------
# 样式：同时适配 Anki 浅色与夜间模式
# ---------------------------------------------------------------------------
CSS = """
.card {
  font-family: -apple-system, "Segoe UI", "PingFang SC", "Hiragino Sans GB",
               "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  font-size: 19px;
  line-height: 1.6;
  text-align: center;
  color: #171B24;
  background: #FFFFFF;
  padding: 20px 16px;
}
.nightMode.card, .night_mode .card { color: #E7EBF3; background: #1A1E27; }

.fr {
  font-family: "Iowan Old Style", Palatino, Georgia, serif;
  font-size: 30px; line-height: 1.3; font-weight: 600;
}
.prompt { font-size: 14.5px; color: #6B7488; margin-top: 8px; }
.nightMode .prompt, .night_mode .prompt { color: #8791A6; }

hr#answer { border: none; border-top: 1px solid #D7DDE9; margin: 16px 0; }
.nightMode hr#answer, .night_mode hr#answer { border-top-color: #2B3448; }

.zh { font-size: 22px; font-weight: 600; margin: 6px 0; }
.en { font-size: 16.5px; color: #2A4BA0; font-style: italic; }
.nightMode .en, .night_mode .en { color: #8CA6F0; }

/* 词性标签 */
.pos {
  display: inline-block; font-size: 12.5px; font-weight: 600;
  padding: 2px 11px; border-radius: 99px; margin: 0 0 6px;
  letter-spacing: .03em;
}
.pos-m { background: #E3EAF8; color: #2A4BA0; }
.pos-f { background: #FBE4EA; color: #A62E4C; }
.pos-n { background: #ECEFF4; color: #4B5464; }
.nightMode .pos-m, .night_mode .pos-m { background: #1A2340; color: #A6BAF6; }
.nightMode .pos-f, .night_mode .pos-f { background: #331C25; color: #F0A0B4; }
.nightMode .pos-n, .night_mode .pos-n { background: #262D3B; color: #AEB7C6; }

/* 语法细节块 */
.gram {
  font-size: 13.5px; line-height: 1.65; color: #4B5464;
  background: #F5F7FA; border: 1px solid #E4E9F0; border-radius: 6px;
  padding: 9px 13px; margin: 12px auto 0; max-width: 480px; text-align: left;
}
.nightMode .gram, .night_mode .gram {
  color: #AEB7C6; background: #20263300; border-color: #2B3448; background: #202633;
}
.gram b { color: #2A4BA0; }
.nightMode .gram b, .night_mode .gram b { color: #8CA6F0; }
.gram-t {
  display: block; font-size: 10.5px; letter-spacing: .1em; text-transform: uppercase;
  color: #8791A6; margin-bottom: 4px; font-weight: 600;
}

.ex { font-size: 17px; margin-top: 14px; line-height: 1.7; }
.ex b { color: #2A4BA0; font-weight: 700; }
.nightMode .ex b, .night_mode .ex b { color: #8CA6F0; }
.zhx { display: block; font-size: 13.5px; color: #6B7488; margin-top: 3px; }
.nightMode .zhx, .night_mode .zhx { color: #8791A6; }

.blank { color: #2A4BA0; font-weight: 700; letter-spacing: 1px; }
.nightMode .blank, .night_mode .blank { color: #8CA6F0; }

.m { color: #2A4BA0; }
.f { color: #A62E4C; }
.nightMode .m, .night_mode .m { color: #8CA6F0; }
.nightMode .f, .night_mode .f { color: #F0A0B4; }

.tag {
  display: inline-block; font-size: 11.5px; letter-spacing: .08em;
  padding: 2px 10px; border-radius: 99px; margin-bottom: 10px; text-transform: uppercase;
}
.t-trap { background: #F8E3E1; color: #9A2E2E; }
.t-info { background: #E3EAF8; color: #2A4BA0; }
.nightMode .t-trap, .night_mode .t-trap { background: #2C1917; color: #E28179; }
.nightMode .t-info, .night_mode .t-info { background: #1A2340; color: #A6BAF6; }

.wrong { color: #9A2E2E; text-decoration: line-through; }
.right { color: #22694D; font-weight: 600; }
.nightMode .wrong, .night_mode .wrong { color: #E28179; }
.nightMode .right, .night_mode .right { color: #6BC195; }

.note { font-size: 13.5px; color: #6B7488; margin-top: 12px; }
.nightMode .note, .night_mode .note { color: #8791A6; }
.audio { margin-top: 10px; }
"""


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def split_example(sentence):
    """'Il **reste** du pain.' -> (挖空版, 高亮版)"""
    blanked = re.sub(r"\*\*(.+?)\*\*",
                     lambda m: '<span class="blank">%s</span>' % ("_" * max(4, len(m.group(1)))),
                     sentence)
    marked = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", sentence)
    return blanked, marked


def gender_span(word):
    w = word.strip()
    if re.match(r"^(un |le |du |au |l')", w):
        return '<span class="m">%s</span>' % w
    if re.match(r"^(une |la |de la )", w):
        return '<span class="f">%s</span>' % w
    return w


def gram_block(text):
    if not text:
        return ""
    return f'<div class="gram"><span class="gram-t">语法</span>{text}</div>'


def snd(fn):
    return f"[sound:{fn}]" if fn else ""


# ---------------------------------------------------------------------------
# note types
# ---------------------------------------------------------------------------
M_FAUX = genanki.Model(
    1607392321, "法语·假朋友",
    fields=[{"name": "法语"}, {"name": "词性"}, {"name": "语法"}, {"name": "英语陷阱词"},
            {"name": "实际意思"}, {"name": "英文释义"}, {"name": "正确说法"},
            {"name": "例句"}, {"name": "例句中文"}, {"name": "词音频"}, {"name": "句音频"}],
    templates=[
        {
            "name": "识义 法→义",
            "qfmt": '<div class="tag t-trap">faux ami</div>'
                    '<div class="fr">{{法语}}</div>'
                    '<div class="audio">{{词音频}}</div>'
                    '<div class="prompt">词性是什么？意思是什么？</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '{{词性}}'
                    '<div class="zh">{{实际意思}}</div>'
                    '<div class="en">{{英文释义}}</div>'
                    '<div class="note">⚠️ 不是英语的 <b>{{英语陷阱词}}</b>'
                    '{{#正确说法}}　·　英语原意该用 <i>{{正确说法}}</i>{{/正确说法}}</div>'
                    '{{语法}}'
                    '{{#例句}}<div class="ex">{{例句}}<span class="zhx">{{例句中文}}</span></div>'
                    '<div class="audio">{{句音频}}</div>{{/例句}}',
        },
        {
            "name": "反查 英→法",
            "qfmt": '<div class="tag t-info">反向检查</div>'
                    '<div class="fr">{{英语陷阱词}}</div>'
                    '<div class="prompt">这个英语意思，法语怎么说？<br>'
                    '（提示：<b>不是</b> {{法语}}）</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="fr right">{{正确说法}}</div>'
                    '<div class="note">而 <b>{{法语}}</b> 其实是「{{实际意思}}」</div>',
        },
        {
            "name": "听音 音→词",
            "qfmt": '<div class="tag t-info">听力</div>'
                    '<div class="audio">{{词音频}}</div>'
                    '<div class="prompt">听到的是哪个词？拼写 + 词性 + 意思</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="fr">{{法语}}</div>'
                    '{{词性}}'
                    '<div class="zh">{{实际意思}}</div>'
                    '{{语法}}',
        },
    ],
    css=CSS,
)

M_SYNTAX = genanki.Model(
    1607392322, "法语·句法假朋友",
    fields=[{"name": "英语"}, {"name": "错误法语"}, {"name": "正确法语"},
            {"name": "说明"}, {"name": "句音频"}],
    templates=[{
        "name": "英→法",
        "qfmt": '<div class="tag t-trap">句法陷阱</div>'
                '<div class="zh">{{英语}}</div>'
                '<div class="prompt">用法语怎么说？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="fr right">{{正确法语}}</div>'
                '<div class="audio">{{句音频}}</div>'
                '<div class="note wrong" style="margin-top:8px;">{{错误法语}}</div>'
                '<div class="gram"><span class="gram-t">为什么</span>{{说明}}</div>',
    }],
    css=CSS,
)

M_PREP = genanki.Model(
    1607392323, "法语·介词搭配",
    fields=[{"name": "法语搭配"}, {"name": "英语对照"}, {"name": "例句挖空"},
            {"name": "例句"}, {"name": "例句中文"}, {"name": "句音频"}],
    templates=[{
        "name": "填介词",
        "qfmt": '<div class="tag t-info">介词搭配</div>'
                '<div class="ex">{{例句挖空}}</div>'
                '<div class="prompt">填入正确的介词</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="fr">{{法语搭配}}</div>'
                '<div class="ex">{{例句}}<span class="zhx">{{例句中文}}</span></div>'
                '<div class="audio">{{句音频}}</div>'
                '<div class="note">英语对照：{{英语对照}}</div>',
    }],
    css=CSS,
)

M_RULE = genanki.Model(
    1607392324, "法语·规则公式",
    fields=[{"name": "正面"}, {"name": "背面"}, {"name": "例子"}],
    templates=[{
        "name": "规则",
        "qfmt": '<div class="tag t-info">换算公式</div><div class="zh">{{正面}}</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="fr">{{背面}}</div>'
                '<div class="ex">{{例子}}</div>',
    }],
    css=CSS,
)

M_SPELL = genanki.Model(
    1607392325, "法语·拼写侦探",
    fields=[{"name": "法语"}, {"name": "英语"}, {"name": "规则"},
            {"name": "语法"}, {"name": "词音频"}],
    templates=[{
        "name": "法→英",
        "qfmt": '<div class="tag t-info">拼写侦探</div>'
                '<div class="fr">{{法语}}</div>'
                '<div class="audio">{{词音频}}</div>'
                '<div class="prompt">对应哪个英语词？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="zh">{{英语}}</div>'
                '<div class="gram"><span class="gram-t">规则</span>{{规则}}<br>{{语法}}</div>',
    }],
    css=CSS,
)

M_GENDER = genanki.Model(
    1607392326, "法语·阴阳性词尾",
    fields=[{"name": "词尾"}, {"name": "性别"}, {"name": "可靠度"},
            {"name": "例词"}, {"name": "例外"}],
    templates=[{
        "name": "判性别",
        "qfmt": '<div class="tag t-info">阴阳性</div>'
                '<div class="fr">{{词尾}}</div>'
                '<div class="prompt">阳性 ♂ 还是阴性 ♀？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '{{性别}}'
                '<div class="note" style="margin-top:2px;">可靠度 {{可靠度}}</div>'
                '<div class="ex">{{例词}}</div>'
                '{{#例外}}<div class="gram"><span class="gram-t">例外</span>⚠️ {{例外}}</div>{{/例外}}',
    }],
    css=CSS,
)

M_VOCAB = genanki.Model(
    1607392327, "法语·核心词汇",
    fields=[{"name": "法语"}, {"name": "词性"}, {"name": "语法"},
            {"name": "英文释义"}, {"name": "中文释义"},
            {"name": "例句挖空"}, {"name": "例句"}, {"name": "例句中文"},
            {"name": "词音频"}, {"name": "句音频"}],
    templates=[
        {
            "name": "例句填空（主卡）",
            "qfmt": '<div class="prompt">填入缺失的词</div>'
                    '<div class="ex">{{例句挖空}}<span class="zhx">{{例句中文}}</span></div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="fr">{{法语}}</div>'
                    '<div class="audio">{{词音频}}</div>'
                    '{{词性}}'
                    '<div class="en">{{英文释义}}</div>'
                    '<div class="note" style="margin-top:2px;">{{中文释义}}</div>'
                    '{{语法}}'
                    '<div class="ex">{{例句}}</div>'
                    '<div class="audio">{{句音频}}</div>',
        },
        {
            "name": "认词 法→义",
            "qfmt": '<div class="fr">{{法语}}</div>'
                    '<div class="audio">{{词音频}}</div>'
                    '<div class="prompt">词性？意思？</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '{{词性}}'
                    '<div class="en">{{英文释义}}</div>'
                    '<div class="zh">{{中文释义}}</div>'
                    '{{语法}}'
                    '<div class="ex">{{例句}}<span class="zhx">{{例句中文}}</span></div>'
                    '<div class="audio">{{句音频}}</div>',
        },
        {
            "name": "听音写词",
            "qfmt": '<div class="tag t-info">听力</div>'
                    '<div class="audio">{{词音频}}</div>'
                    '<div class="prompt">听到的是哪个词？<br>写出拼写、词性和意思</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="fr">{{法语}}</div>'
                    '{{词性}}'
                    '<div class="zh">{{中文释义}}</div>'
                    '{{语法}}',
        },
    ],
    css=CSS,
)

# ---------------------------------------------------------------------------
# decks
# ---------------------------------------------------------------------------
PARENT = "法语 · DELF B2 一年计划"
DECK_SPECS = [
    (2059400110, f"{PARENT}::01 · 假朋友 一级警报"),
    (2059400111, f"{PARENT}::02 · 假朋友 二级"),
    (2059400112, f"{PARENT}::03 · 假朋友 三级"),
    (2059400113, f"{PARENT}::04 · 句法假朋友"),
    (2059400114, f"{PARENT}::05 · 介词搭配"),
    (2059400115, f"{PARENT}::06 · 英法后缀换算"),
    (2059400116, f"{PARENT}::07 · 拼写侦探规则"),
    (2059400117, f"{PARENT}::08 · 阴阳性词尾"),
    (2059400118, f"{PARENT}::09 · 高频核心词（无英语同源）"),
]
decks = {name: genanki.Deck(did, name) for did, name in DECK_SPECS}
D = {i + 1: decks[name] for i, (_, name) in enumerate(DECK_SPECS)}

csv_rows = {}
used_media = []


def add(deck_no, model, fields, tags, csv_key, csv_header):
    D[deck_no].add_note(genanki.Note(model=model, fields=fields, tags=tags))
    csv_rows.setdefault(csv_key, (csv_header, []))[1].append(
        [re.sub(r"<[^>]+>", "", html.unescape(f)) for f in fields])


# ---------------------------------------------------------------------------
def collect_audio_jobs():
    jobs = []
    for group in (data.FAUX_AMIS_1, data.FAUX_AMIS_2, data.FAUX_AMIS_3, data.CORE_WORDS):
        for e in group:
            jobs.append((e["fr"], "word"))
            if e.get("ex"):
                jobs.append((e["ex"], "sentence"))
    for _en, _wrong, right, _note in data.SYNTAX:
        jobs.append((right, "sentence"))
    for _c, _e, ex, _z in data.PREPOSITIONS:
        jobs.append((ex, "sentence"))
    for fr, _en, _rule, _gram in data.SPELLING_RULES:
        jobs.append((fr, "word"))
    return jobs


def build(audio):
    def a_word(t):
        fn = audio.get((t, "word"))
        if fn:
            used_media.append(fn)
        return snd(fn)

    def a_sent(t):
        fn = audio.get((t, "sentence"))
        if fn:
            used_media.append(fn)
        return snd(fn)

    fa_header = ["法语", "词性", "语法", "英语陷阱词", "实际意思", "英文释义",
                 "正确说法", "例句", "例句中文", "词音频", "句音频"]

    for deck_no, group, tag in ((1, data.FAUX_AMIS_1, "niveau1"),
                                (2, data.FAUX_AMIS_2, "niveau2"),
                                (3, data.FAUX_AMIS_3, "niveau3")):
        for e in group:
            _, marked = split_example(e["ex"])
            add(deck_no, M_FAUX,
                [gender_span(e["fr"]), pos_badge(e["pos"]), gram_block(e["gram"]),
                 e["trap"], e["zh"], e["en"], e.get("correct", ""),
                 marked, e["exzh"], a_word(e["fr"]), a_sent(e["ex"])],
                ["fauxami", tag], f"0{deck_no}_faux_amis_{tag[-1]}", fa_header)

    for en, wrong, right, note in data.SYNTAX:
        add(4, M_SYNTAX, [en, "✗ " + wrong, right, note, a_sent(right)],
            ["syntaxe", "anglicisme"], "04_syntaxe",
            ["英语", "错误法语", "正确法语", "说明", "句音频"])

    for coll, en, ex, exzh in data.PREPOSITIONS:
        blanked, marked = split_example(ex)
        add(5, M_PREP, [coll, en, blanked, marked, exzh, a_sent(ex)],
            ["preposition"], "05_prepositions",
            ["法语搭配", "英语对照", "例句挖空", "例句", "例句中文", "句音频"])

    for front, back, ex in data.SUFFIX_RULES:
        add(6, M_RULE, [front, back, ex], ["suffixe", "transfert"],
            "06_suffixes", ["正面", "背面", "例子"])

    for fr, en, rule, gram in data.SPELLING_RULES:
        add(7, M_SPELL, [gender_span(fr), en, rule, gram, a_word(fr)],
            ["orthographe", "transfert"], "07_orthographe",
            ["法语", "英语", "规则", "语法", "词音频"])

    for ending, g, rel, examples, exc in data.GENDER_RULES:
        label = pos_badge("n.m.") if g == "m" else pos_badge("n.f.")
        add(8, M_GENDER, [ending, label, rel, examples, exc],
            ["genre"], "08_genre", ["词尾", "性别", "可靠度", "例词", "例外"])

    for e in data.CORE_WORDS:
        blanked, marked = split_example(e["ex"])
        add(9, M_VOCAB,
            [gender_span(e["fr"]), pos_badge(e["pos"]), gram_block(e["gram"]),
             e["en"], e["zh"], blanked, marked, e["exzh"],
             a_word(e["fr"]), a_sent(e["ex"])],
            ["vocabulaire", "noncognat"], "09_core_words",
            ["法语", "词性", "语法", "英文释义", "中文释义",
             "例句挖空", "例句", "例句中文", "词音频", "句音频"])


def export():
    os.makedirs(CSV_DIR, exist_ok=True)
    pkg = genanki.Package(list(decks.values()))
    pkg.media_files = tts.media_paths(used_media)
    apkg = os.path.join(OUT_DIR, "French-DELF-B2.apkg")
    pkg.write_to_file(apkg)

    for key, (header, rows) in csv_rows.items():
        with open(os.path.join(CSV_DIR, key + ".csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    total_n = total_c = 0
    print(f"\n  ✓ {apkg}")
    print(f"  ✓ 音频 {len(set(used_media))} 条已打包\n")
    print(f"    {'牌组':<32}{'笔记':>6}{'卡片':>6}")
    print(f"    {'-' * 44}")
    for _did, name in DECK_SPECS:
        d = decks[name]
        n = len(d.notes)
        c = sum(len(note.cards) for note in d.notes)
        total_n += n
        total_c += c
        print(f"    {name.split('::')[1]:<32}{n:>6}{c:>6}")
    print(f"    {'-' * 44}")
    print(f"    {'合计':<32}{total_n:>6}{total_c:>6}")
    print(f"\n  ✓ CSV：{CSV_DIR}\n")


if __name__ == "__main__":
    print("\n▸ 生成音频")
    audio = tts.synthesize(collect_audio_jobs())
    print("\n▸ 生成牌组")
    build(audio)
    export()
