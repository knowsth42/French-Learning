#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把真实的笔记模板渲染成一张 HTML 预览页，用来检查卡片外观。

    python3 preview.py     →  dist/preview.html

注意：Anki 的 {{Field}} <b>不</b>转义字段里的 HTML，而 mustache 会。
这里把 {{X}} 改写成 {{{X}}} 以还原 Anki 的真实行为。
"""

import os
import re

import chevron

import build_decks as B
import data

HERE = os.path.dirname(os.path.abspath(__file__))


def unescaped(t):
    return re.sub(r"\{\{(?![#/^{])([^}]+)\}\}", r"{{{\1}}}", t)


def render(model, fields, i=0):
    f = dict(zip([x["name"] for x in model.fields], fields))
    t = model.templates[i]
    q = chevron.render(unescaped(t["qfmt"]), f)
    a = chevron.render(unescaped(t["afmt"]).replace("{{{FrontSide}}}", q), f)
    # 预览里把 [sound:x.mp3] 显示成一个可见的喇叭标记
    tag = '<div class="snd">🔊 发音</div>'
    return (re.sub(r"\[sound:[^\]]+\]", tag, q),
            re.sub(r"\[sound:[^\]]+\]", tag, a))


def faux_fields(e):
    _, marked = B.split_example(e["ex"])
    return [B.gender_span(e["fr"]), B.pos_badge(e["pos"]), B.gram_block(e["gram"]),
            e["trap"], e["zh"], e["en"], e.get("correct", ""),
            marked, e["exzh"], "[sound:x.mp3]", "[sound:y.mp3]"]


def vocab_fields(e):
    bl, mk = B.split_example(e["ex"])
    return [B.gender_span(e["fr"]), B.pos_badge(e["pos"]), B.gram_block(e["gram"]),
            e["en"], e["zh"], bl, mk, e["exzh"], "[sound:x.mp3]", "[sound:y.mp3]"]


def pick(group, needle):
    return next(e for e in group if needle in e["fr"])


def main():
    S = []
    S.append(("01 假朋友 · 识义卡（法 → 义）", render(B.M_FAUX, faux_fields(data.FAUX_AMIS_1[0]), 0)))
    S.append(("01 假朋友 · 反查卡（英 → 法）", render(B.M_FAUX, faux_fields(data.FAUX_AMIS_1[0]), 1)))
    S.append(("01 假朋友 · 听音卡（新增）", render(B.M_FAUX, faux_fields(data.FAUX_AMIS_1[0]), 2)))
    S.append(("02 假朋友 · 阴性名词（词性标签为红）",
              render(B.M_FAUX, faux_fields(pick(data.FAUX_AMIS_2, "veste")), 0)))
    S.append(("02 假朋友 · 阳性名词 + 不规则复数",
              render(B.M_FAUX, faux_fields(pick(data.FAUX_AMIS_2, "journal")), 0)))
    S.append(("04 句法假朋友",
              render(B.M_SYNTAX, ["I've lived here for 3 years.",
                                  "✗ J'ai habité ici pour 3 ans.",
                                  "J'habite ici depuis 3 ans.",
                                  "「自……以来」用<b>现在时 + depuis</b>，不是复合过去时。",
                                  "[sound:x.mp3]"])))
    coll, en, ex, exzh = data.PREPOSITIONS[1]
    bl, mk = B.split_example(ex)
    S.append(("05 介词搭配", render(B.M_PREP, [coll, en, bl, mk, exzh, "[sound:x.mp3]"])))
    S.append(("06 后缀换算", render(B.M_RULE, list(data.SUFFIX_RULES[1]))))
    fr, en2, rule, gram = data.SPELLING_RULES[1]
    S.append(("07 拼写侦探", render(B.M_SPELL, [B.gender_span(fr), en2, rule, gram, "[sound:x.mp3]"])))
    e, g, rel, exw, exc = data.GENDER_RULES[10]
    S.append(("08 阴阳性词尾",
              render(B.M_GENDER, [e, B.pos_badge("n.m." if g == "m" else "n.f."), rel, exw, exc])))
    S.append(("09 核心词 · 例句填空（主卡）· 动词助动词为 être",
              render(B.M_VOCAB, vocab_fields(pick(data.CORE_WORDS, "rester")), 0)))
    S.append(("09 核心词 · 认词卡 · 第3组不规则动词",
              render(B.M_VOCAB, vocab_fields(pick(data.CORE_WORDS, "éteindre")), 1)))
    S.append(("09 核心词 · 听音写词卡（新增）",
              render(B.M_VOCAB, vocab_fields(pick(data.CORE_WORDS, "néanmoins")), 2)))
    S.append(("09 核心词 · 形容词（含阴性形式）",
              render(B.M_VOCAB, vocab_fields(pick(data.CORE_WORDS, "doux")), 1)))
    S.append(("09 核心词 · 阳性名词（含不规则复数）",
              render(B.M_VOCAB, vocab_fields(pick(data.CORE_WORDS, "milieu")), 1)))

    page = ["<title>Anki 卡片预览 · 法语 DELF B2</title>",
            "<style>%s</style>" % B.CSS,
            """<style>
body{background:#EEF1F6;margin:0;padding:32px 22px 64px;
     font-family:-apple-system,'PingFang SC','Noto Sans CJK SC',sans-serif;}
h1{max-width:1040px;margin:0 auto 6px;font:600 23px/1.3 'Iowan Old Style',Georgia,serif;color:#171B24;}
p.i{max-width:1040px;margin:0 auto 32px;font-size:13.5px;color:#5C6373;line-height:1.7;}
.pair{max-width:1040px;margin:0 auto 32px;}
.lbl{font:600 12px/1.4 -apple-system,sans-serif;letter-spacing:.07em;color:#2A4BA0;margin-bottom:9px;}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start;}
@media(max-width:780px){.two{grid-template-columns:1fr;}}
/* 注意：这里必须保持 display:block —— Anki 的 .card 就是普通块级元素。
   若改成 flex，子元素会被拉伸，词性/标签的胶囊背景会错误地占满整行。 */
.card{border:1px solid #D7DDE9;border-radius:8px;min-height:150px;
      display:block;box-shadow:0 1px 3px rgba(21,26,38,.05);}
.side{font:600 10.5px/1 ui-monospace,monospace;color:#8791A6;margin-bottom:6px;letter-spacing:.08em;}
.snd{display:inline-block;font-size:12.5px;color:#2A4BA0;background:#E3EAF8;
     border-radius:99px;padding:3px 12px;margin:8px 0 2px;}
</style>""",
            "<h1>Anki 卡片预览</h1>",
            "<p class='i'>每组左为正面、右为背面。实际卡片在 Anki 中同时适配浅色与夜间模式。"
            "词性标签按阴阳性着色：<span style='background:#E3EAF8;color:#2A4BA0;padding:1px 8px;"
            "border-radius:99px;font-size:12px;'>名词 · 阳性 ♂</span> "
            "<span style='background:#FBE4EA;color:#A62E4C;padding:1px 8px;border-radius:99px;"
            "font-size:12px;'>名词 · 阴性 ♀</span> "
            "<span style='background:#ECEFF4;color:#4B5464;padding:1px 8px;border-radius:99px;"
            "font-size:12px;'>动词 / 形容词 / 副词…</span><br>"
            "🔊 处在 Anki 里是可播放的法语发音（词条为女声，例句为男声）。</p>"]

    for label, (q, a) in S:
        page.append(f'<div class="pair"><div class="lbl">{label}</div><div class="two">'
                    f'<div><div class="side">正面 FRONT</div><div class="card">{q}</div></div>'
                    f'<div><div class="side">背面 BACK</div><div class="card">{a}</div></div>'
                    f'</div></div>')

    out = os.path.join(HERE, "dist", "preview.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(page))

    txt = open(out, encoding="utf-8").read()
    assert "&lt;b&gt;" not in txt, "字段 HTML 被转义了"
    assert 'class="pos pos-f"' in txt and 'class="pos pos-m"' in txt, "词性标签着色缺失"
    assert 'class="gram"' in txt, "语法块缺失"
    assert 'class="blank"' in txt, "挖空缺失"
    print(f"✓ {out}（{len(S)} 组卡片，渲染与着色检查通过）")


if __name__ == "__main__":
    main()
