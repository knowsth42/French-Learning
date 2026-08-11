#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 DELF B2 一年计划配套 Anki 牌组。

用法:
    pip install genanki
    python3 build_decks.py

输出:
    dist/French-DELF-B2.apkg     ← 双击导入 Anki
    dist/csv/*.csv               ← 备用（Anki「文件 → 导入」也可读）
"""

import csv
import os
import re
import html

import genanki

import data

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
CSV_DIR = os.path.join(OUT_DIR, "csv")

# ---------------------------------------------------------------------------
# 样式：同时适配 Anki 浅色与夜间模式
# ---------------------------------------------------------------------------
CSS = """
.card {
  font-family: -apple-system, "Segoe UI", "PingFang SC", "Hiragino Sans GB",
               "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  font-size: 20px;
  line-height: 1.65;
  text-align: center;
  color: #171B24;
  background: #FFFFFF;
  padding: 18px 14px;
}
.nightMode.card, .night_mode .card { color: #E7EBF3; background: #1A1E27; }

.fr {
  font-family: "Iowan Old Style", Palatino, Georgia, serif;
  font-size: 30px;
  line-height: 1.3;
  font-weight: 600;
}
.prompt { font-size: 15px; color: #6B7488; margin-bottom: 10px; }
.nightMode .prompt, .night_mode .prompt { color: #8791A6; }

hr#answer { border: none; border-top: 1px solid #D7DDE9; margin: 16px 0; }
.nightMode hr#answer, .night_mode hr#answer { border-top-color: #2B3448; }

.zh   { font-size: 22px; font-weight: 600; margin: 6px 0; }
.en   { font-size: 17px; color: #2A4BA0; font-style: italic; }
.nightMode .en, .night_mode .en { color: #8CA6F0; }

.ex   { font-size: 17px; margin-top: 14px; line-height: 1.7; }
.ex b { color: #2A4BA0; font-weight: 700; }
.nightMode .ex b, .night_mode .ex b { color: #8CA6F0; }
.ex .zhx { display:block; font-size: 14px; color: #6B7488; margin-top: 3px; }
.nightMode .ex .zhx, .night_mode .ex .zhx { color: #8791A6; }

.blank { color: #2A4BA0; font-weight: 700; letter-spacing: 1px; }
.nightMode .blank, .night_mode .blank { color: #8CA6F0; }

/* 阴阳性颜色编码：阳性蓝 / 阴性红 */
.m { color: #2A4BA0; }
.f { color: #B03050; }
.nightMode .m, .night_mode .m { color: #8CA6F0; }
.nightMode .f, .night_mode .f { color: #E88396; }

.tag {
  display: inline-block; font-size: 12px; letter-spacing: .08em;
  padding: 2px 9px; border-radius: 99px; margin-bottom: 10px;
  text-transform: uppercase;
}
.t-trap { background: #F8E3E1; color: #9A2E2E; }
.t-ok   { background: #DFF0E7; color: #22694D; }
.t-info { background: #E3EAF8; color: #2A4BA0; }
.nightMode .t-trap, .night_mode .t-trap { background: #2C1917; color: #E28179; }
.nightMode .t-ok,   .night_mode .t-ok   { background: #16281F; color: #6BC195; }
.nightMode .t-info, .night_mode .t-info { background: #1A2340; color: #A6BAF6; }

.wrong { color: #9A2E2E; text-decoration: line-through; }
.right { color: #22694D; font-weight: 600; }
.nightMode .wrong, .night_mode .wrong { color: #E28179; }
.nightMode .right, .night_mode .right { color: #6BC195; }

.note { font-size: 14px; color: #6B7488; margin-top: 12px; }
.nightMode .note, .night_mode .note { color: #8791A6; }
"""


# ---------------------------------------------------------------------------
# 工具：把 **目标词** 转成挖空版 / 高亮版
# ---------------------------------------------------------------------------
def split_example(sentence):
    """'Il **reste** du pain.' -> (挖空版, 高亮版)"""
    blanked = re.sub(r"\*\*(.+?)\*\*",
                     lambda m: '<span class="blank">%s</span>' % ("_" * max(4, len(m.group(1)))),
                     sentence)
    marked = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", sentence)
    return blanked, marked


def gender_span(word):
    """给带冠词的词加阴阳性颜色。"""
    w = word.strip()
    if re.match(r"^(un |le |du |au )", w):
        return '<span class="m">%s</span>' % w
    if re.match(r"^(une |la |de la )", w):
        return '<span class="f">%s</span>' % w
    return w


# ---------------------------------------------------------------------------
# note types
# ---------------------------------------------------------------------------
M_FAUX = genanki.Model(
    1607392311, "法语·假朋友",
    fields=[{"name": "法语"}, {"name": "英语陷阱词"}, {"name": "实际意思"},
            {"name": "正确说法"}, {"name": "例句"}, {"name": "例句中文"}],
    templates=[
        {
            "name": "识义 法→义",
            "qfmt": '<div class="tag t-trap">faux ami</div>'
                    '<div class="fr">{{法语}}</div>'
                    '<div class="prompt">它到底是什么意思？</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="zh">{{实际意思}}</div>'
                    '<div class="note">⚠️ 不是英语的 <b>{{英语陷阱词}}</b>'
                    '{{#正确说法}}　·　英语原意该用 <i>{{正确说法}}</i>{{/正确说法}}</div>'
                    '{{#例句}}<div class="ex">{{例句}}<span class="zhx">{{例句中文}}</span></div>{{/例句}}',
        },
        {
            "name": "反查 英→法",
            "qfmt": '<div class="tag t-info">反向检查</div>'
                    '<div class="fr">{{英语陷阱词}}</div>'
                    '<div class="prompt">英语的这个意思，法语怎么说？<br>'
                    '（提示：<b>不是</b> {{法语}}）</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="zh right">{{正确说法}}</div>'
                    '<div class="note">而 <b>{{法语}}</b> 其实是「{{实际意思}}」</div>',
        },
    ],
    css=CSS,
)

M_FAUX_SIMPLE = genanki.Model(
    1607392312, "法语·假朋友（简）",
    fields=[{"name": "法语"}, {"name": "陷阱"}, {"name": "实际意思"}],
    templates=[{
        "name": "识义",
        "qfmt": '<div class="tag t-trap">faux ami</div>'
                '<div class="fr">{{法语}}</div>'
                '<div class="prompt">它到底是什么意思？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="zh">{{实际意思}}</div>'
                '<div class="note">{{陷阱}}</div>',
    }],
    css=CSS,
)

M_SYNTAX = genanki.Model(
    1607392313, "法语·句法假朋友",
    fields=[{"name": "英语"}, {"name": "错误法语"}, {"name": "正确法语"}, {"name": "说明"}],
    templates=[{
        "name": "英→法",
        "qfmt": '<div class="tag t-trap">句法陷阱</div>'
                '<div class="zh">{{英语}}</div>'
                '<div class="prompt">用法语怎么说？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="fr right">{{正确法语}}</div>'
                '<div class="note wrong" style="margin-top:8px;">{{错误法语}}</div>'
                '<div class="note">{{说明}}</div>',
    }],
    css=CSS,
)

M_PREP = genanki.Model(
    1607392314, "法语·介词搭配",
    fields=[{"name": "法语搭配"}, {"name": "英语对照"}, {"name": "例句"}, {"name": "例句中文"}],
    templates=[{
        "name": "填介词",
        "qfmt": '<div class="tag t-info">介词搭配</div>'
                '<div class="ex">{{例句}}</div>'
                '<div class="prompt">填入正确的介词</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="fr">{{法语搭配}}</div>'
                '<div class="ex" style="margin-top:10px;">{{例句中文}}</div>'
                '<div class="note">英语对照：{{英语对照}}</div>',
    }],
    css=CSS,
)

M_RULE = genanki.Model(
    1607392315, "法语·规则公式",
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
    1607392316, "法语·拼写侦探",
    fields=[{"name": "法语"}, {"name": "英语"}, {"name": "规则"}],
    templates=[{
        "name": "法→英",
        "qfmt": '<div class="tag t-info">拼写侦探</div>'
                '<div class="fr">{{法语}}</div>'
                '<div class="prompt">对应哪个英语词？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="zh">{{英语}}</div>'
                '<div class="note">规则：{{规则}}</div>',
    }],
    css=CSS,
)

M_GENDER = genanki.Model(
    1607392317, "法语·阴阳性词尾",
    fields=[{"name": "词尾"}, {"name": "性别"}, {"name": "可靠度"},
            {"name": "例词"}, {"name": "例外"}],
    templates=[{
        "name": "判性别",
        "qfmt": '<div class="tag t-info">阴阳性</div>'
                '<div class="fr">{{词尾}}</div>'
                '<div class="prompt">阳性 ♂ 还是阴性 ♀？</div>',
        "afmt": '{{FrontSide}}<hr id="answer">'
                '<div class="zh">{{性别}}　<span style="font-size:15px;color:#6B7488;">{{可靠度}}</span></div>'
                '<div class="ex">{{例词}}</div>'
                '{{#例外}}<div class="note">⚠️ 例外：{{例外}}</div>{{/例外}}',
    }],
    css=CSS,
)

M_VOCAB = genanki.Model(
    1607392318, "法语·核心词汇",
    fields=[{"name": "法语"}, {"name": "词性"}, {"name": "英文释义"}, {"name": "中文释义"},
            {"name": "例句挖空"}, {"name": "例句"}, {"name": "例句中文"}],
    templates=[
        {
            "name": "例句填空（主卡）",
            "qfmt": '<div class="prompt">填入缺失的词</div>'
                    '<div class="ex">{{例句挖空}}<span class="zhx">{{例句中文}}</span></div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="fr">{{法语}}</div>'
                    '<div class="en">{{英文释义}}</div>'
                    '<div class="note">{{中文释义}}　·　{{词性}}</div>'
                    '<div class="ex">{{例句}}</div>',
        },
        {
            "name": "认词 法→义",
            "qfmt": '<div class="fr">{{法语}}</div>',
            "afmt": '{{FrontSide}}<hr id="answer">'
                    '<div class="en">{{英文释义}}</div>'
                    '<div class="zh">{{中文释义}}</div>'
                    '<div class="ex">{{例句}}<span class="zhx">{{例句中文}}</span></div>',
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


def add(deck_no, model, fields, tags, csv_key, csv_header):
    D[deck_no].add_note(genanki.Note(model=model, fields=fields, tags=tags))
    csv_rows.setdefault(csv_key, (csv_header, []))[1].append(
        [re.sub(r"<[^>]+>", "", html.unescape(f)) for f in fields])


def build():
    seen = set()

    # 01 一级假朋友
    for fr, trap, mean, correct, ex, exzh in data.FAUX_AMIS_1:
        _, marked = split_example(ex)
        add(1, M_FAUX, [gender_span(fr), trap, mean, correct, marked, exzh],
            ["fauxami", "niveau1"], "01_faux_amis_1",
            ["法语", "英语陷阱词", "实际意思", "正确说法", "例句", "例句中文"])
        seen.add(fr)

    # 02 二级假朋友
    for fr, trap, mean, correct in data.FAUX_AMIS_2:
        add(2, M_FAUX, [gender_span(fr), trap, mean, correct, "", ""],
            ["fauxami", "niveau2"], "02_faux_amis_2",
            ["法语", "英语陷阱词", "实际意思", "正确说法", "例句", "例句中文"])
        seen.add(fr)

    # 03 三级假朋友（跳过已在一级出现过的词）
    for fr, trap, mean in data.FAUX_AMIS_3:
        if fr in seen:
            continue
        add(3, M_FAUX_SIMPLE, [gender_span(fr), trap, mean],
            ["fauxami", "niveau3"], "03_faux_amis_3", ["法语", "陷阱", "实际意思"])
        seen.add(fr)

    # 04 句法假朋友
    for en, wrong, right, note in data.SYNTAX:
        add(4, M_SYNTAX, [en, "✗ " + wrong, right, note],
            ["syntaxe", "anglicisme"], "04_syntaxe", ["英语", "错误法语", "正确法语", "说明"])

    # 05 介词搭配
    for coll, en, ex, exzh in data.PREPOSITIONS:
        blanked, marked = split_example(ex)
        add(5, M_PREP, [coll, en, blanked, marked + "　" + exzh],
            ["preposition"], "05_prepositions", ["法语搭配", "英语对照", "例句挖空", "例句"])

    # 06 后缀换算
    for front, back, ex in data.SUFFIX_RULES:
        add(6, M_RULE, [front, back, ex], ["suffixe", "transfert"],
            "06_suffixes", ["正面", "背面", "例子"])

    # 07 拼写侦探
    for fr, en, rule in data.SPELLING_RULES:
        add(7, M_SPELL, [fr, en, rule], ["orthographe", "transfert"],
            "07_orthographe", ["法语", "英语", "规则"])

    # 08 阴阳性词尾
    for ending, g, rel, examples, exc in data.GENDER_RULES:
        label = '<span class="m">阳性 ♂ masculin</span>' if g == "m" \
            else '<span class="f">阴性 ♀ féminin</span>'
        add(8, M_GENDER, [ending, label, rel, examples, exc],
            ["genre"], "08_genre", ["词尾", "性别", "可靠度", "例词", "例外"])

    # 09 高频核心词
    core_seen = set()
    for fr, pos, en, zh, ex, exzh in data.CORE_WORDS:
        if fr in core_seen:
            continue
        core_seen.add(fr)
        blanked, marked = split_example(ex)
        add(9, M_VOCAB, [gender_span(fr), pos, en, zh, blanked, marked, exzh],
            ["vocabulaire", "noncognat"], "09_core_words",
            ["法语", "词性", "英文释义", "中文释义", "例句挖空", "例句", "例句中文"])


def export():
    os.makedirs(CSV_DIR, exist_ok=True)

    pkg = genanki.Package(list(decks.values()))
    apkg = os.path.join(OUT_DIR, "French-DELF-B2.apkg")
    pkg.write_to_file(apkg)

    for key, (header, rows) in csv_rows.items():
        with open(os.path.join(CSV_DIR, key + ".csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)

    total = 0
    print(f"\n  ✓ {apkg}\n")
    for did, name in DECK_SPECS:
        n = len(decks[name].notes)
        total += n
        print(f"    {name.split('::')[1]:<34} {n:>4} 张笔记")
    print(f"    {'合计':<34} {total:>4} 张笔记")
    print(f"\n  ✓ CSV 备份：{CSV_DIR}\n")


if __name__ == "__main__":
    build()
    export()
