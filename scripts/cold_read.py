#!/usr/bin/env python3
"""冷读视图：从 film-director 分镜卡里只留下观众看得见、听得见的部分。

保留：镜头纵览（去掉手法 / 用在哪里 / 剧情拍子列和表下的说明行）、走位表（去掉动线含义列）、
机位表、clip 起始 / 结束状态、各镜 C 层、贯穿要求、覆盖各镜的修订小节（老格式的卡）。
去掉：卡头（版本、场景参数卡、视觉方案、观众问题、峰值事件……）、A / B 层、表演翻译、
变化字段、执行卡、E 层、风险、未决、空间锚点、核对与复核、手法分布、场次纵览。

用法：
  python3 cold_read.py <分镜卡.md> [--mask-dialogue] [--list]

  --mask-dialogue  把引号里的英文台词换成［台词］，做静音测试
  --list           在末尾列出保留、去掉和未识别的小节

认得三种格式：1.14 起的卡（## 镜头 N + **A** / **表演翻译** / **C**）、
EP05 式（## 分镜（C 层）里 **镜 N（…）** + "- A：" / "- C："）、EP04 式（## 镜头 N + **A** / **B** / **C**，
外加"修订"小节）。认不出的小节列在"未识别"里，按冷读顺序手动读。
"""

import argparse
import re
import sys
from pathlib import Path

# 小节标题 → 类别。按顺序匹配，先排除后保留。
EXCLUDE_TITLES = [
    "手法分布", "场次纵览", "执行卡", "E 层", "E层", "风险", "未决", "空间锚点", "核对", "复核",
    "剧本锁定", "clip 头部", "待复核", "视觉方案", "场景参数", "表演来源", "资产", "历史",
]
INCLUDE_TITLES = [
    ("镜头纵览", "table"),
    ("走位表", "table"),
    ("机位表", "table"),
    ("clip 起始状态", "plain"),
    ("clip 结束状态", "plain"),
    ("起始状态", "plain"),
    ("结束状态", "plain"),
    ("贯穿要求", "plain"),
    ("分镜（C 层）", "storyboard"),
    ("分镜(C 层)", "storyboard"),
]
SHOT_HEADING = re.compile(r"^(镜头?\s*\d+\s*[（(][^）)]*[）)])")
SHOT_BOLD = re.compile(r"^\*\*(镜头?\s*\d+\s*[（(][^）)]*[）)])[^*]*\*\*\s*$")
REVISION_TITLE = re.compile(r"修订")

DROP_COLUMNS = ["手法", "用在哪里", "动线含义", "剧情拍子"]

# 层标签：**A**： / **A 创作决策**（…）： / - A： / **表演翻译**： / - 表演翻译（…）：
LABEL = re.compile(
    r"^\s*(?:-\s*)?(?:\*\*)?\s*(A|B|C|D|E|表演翻译|表演来源|额外动作|变化)"
    r"(?:\s*(?:创作决策|分镜说明|可观察信息|元数据))?\s*(?:\*\*)?\s*(?:[（(][^）)]*[）)])?\s*[：:]"
)
KEEP_LABELS = {"C"}

VARIATION_BRACKET = re.compile(r"【变化[:：][^】]*】")
VARIATION_INLINE = re.compile(r"｜?\s*变化[:：].*?幅度\s*[0-9→\-–= ]+(?:｜新增[^｜]*)?")
BOLD = re.compile(r"\*\*")
STAR = re.compile(r"[★☆]")
QUOTED = re.compile(r"(“[^”]*”|\"[^\"]*\"|「[^」]*」)")
LATIN = re.compile(r"[A-Za-z]")


CONTAINER_TITLES = ("机位设计", "纵览")  # 只是父标题，内容在子小节里


def classify(title):
    t = title.strip()
    if SHOT_HEADING.match(t):
        return "shot"
    for word in EXCLUDE_TITLES:
        if word in t:
            return "exclude"
    for word, kind in INCLUDE_TITLES:
        if word in t:
            return kind
    if t.startswith(CONTAINER_TITLES):
        return "container"
    if REVISION_TITLE.search(t):
        return "revision"
    return None


def split_sections(lines):
    """按 ## / ### 标题切小节；第一个 ## 之前是卡头。"""
    sections = [{"level": 1, "title": "卡头", "lines": [], "kind": "exclude"}]
    for line in lines:
        m = re.match(r"^(#{2,4})\s+(.*)$", line)
        if m:
            sections.append({"level": len(m.group(1)), "title": m.group(2).strip(), "lines": [], "kind": None})
        else:
            sections[-1]["lines"].append(line)
    # 定类别：自己认得就用自己的；认不得的子小节继承上一级已保留的父小节
    parent_kind = {}
    for sec in sections[1:]:
        kind = classify(sec["title"])
        if kind is None:
            inherited = None
            for lvl in range(sec["level"] - 1, 1, -1):
                if lvl in parent_kind:
                    inherited = parent_kind[lvl]
                    break
            kind = inherited if inherited not in (None, "exclude", "container") else "unknown"
        sec["kind"] = kind
        parent_kind[sec["level"]] = kind
        for lvl in list(parent_kind):
            if lvl > sec["level"]:
                del parent_kind[lvl]
    return sections


def split_row(row):
    protected = row.replace("\\|", "\u0000")
    cells = protected.strip().strip("|").split("|")
    return [c.replace("\u0000", "\\|").strip() for c in cells]


def filter_table(lines):
    """只留表格行，去掉不该冷读看到的列。"""
    out, header, keep = [], None, None
    for line in lines:
        s = line.strip()
        if not s.startswith("|"):
            header, keep = None, None
            continue
        cells = split_row(s)
        if header is None:
            header = cells
            keep = [i for i, h in enumerate(header) if not any(w in h for w in DROP_COLUMNS)]
            out.append("| " + " | ".join(header[i] for i in keep) + " |")
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            out.append("|" + "|".join("---" for _ in keep) + "|")
            continue
        picked = [cells[i] if i < len(cells) else "" for i in keep]
        out.append("| " + " | ".join(clean_inline(c) for c in picked) + " |")
    return out


def clean_inline(text):
    text = VARIATION_BRACKET.sub("", text)
    text = VARIATION_INLINE.sub("", text)
    text = BOLD.sub("", text)
    text = STAR.sub("", text)
    return text.rstrip()


def keep_c_layer(lines):
    """镜内只留 C 层：遇到 A / B / E / 表演翻译 标签就停，遇到 C 标签就开始留。
    一个标签都没有的小节（极老的卡）整段保留，只删明显的设计说明行。"""
    has_label = any(LABEL.match(l) for l in lines)
    out = []
    if not has_label:
        for l in lines:
            if re.match(r"^\s*-?\s*(表演翻译|变化|A 创作决策|B 分镜说明)", l):
                continue
            out.append(clean_inline(l))
        return out
    keeping = False
    for l in lines:
        m = LABEL.match(l)
        if m:
            keeping = m.group(1) in KEEP_LABELS
            if keeping:
                rest = l[m.end():].strip()
                if rest:
                    out.append("- " + clean_inline(rest) if l.lstrip().startswith("-") else clean_inline(rest))
            continue
        if keeping:
            out.append(clean_inline(l))
    return out


def render_storyboard(lines):
    """EP05 式：一个小节里用 **镜 N（…）** 分镜。"""
    out, block = [], []

    def flush():
        if block:
            out.extend(keep_c_layer(block[1:]) if block and SHOT_BOLD.match(block[0].strip()) else keep_c_layer(block))

    for l in lines:
        m = SHOT_BOLD.match(l.strip())
        if m:
            flush()
            block = [l]
            out.append("")
            out.append("### " + m.group(1))
            continue
        block.append(l)
    flush()
    return out


def mask(text):
    return QUOTED.sub(lambda m: "［台词］" if LATIN.search(m.group(0)) else m.group(0), text)


def build(path, mask_dialogue=False):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    sections = split_sections(lines)
    body, report = [], {"保留": [], "去掉": [], "未识别": []}
    for sec in sections:
        kind, title = sec["kind"], sec["title"]
        if kind == "container":
            continue
        if kind == "exclude":
            report["去掉"].append(title)
            continue
        if kind == "unknown":
            report["未识别"].append(title)
            continue
        report["保留"].append(title)
        if kind == "table":
            content = filter_table(sec["lines"])
            heading = title
        elif kind == "shot":
            content = keep_c_layer(sec["lines"])
            heading = SHOT_HEADING.match(title).group(1)
        elif kind == "storyboard":
            content = render_storyboard(sec["lines"])
            heading = "分镜"
        elif kind == "revision":
            content = [clean_inline(l) for l in sec["lines"]]
            heading = "修订（覆盖下方各镜里冲突的写法）"
        else:
            content = [clean_inline(l) for l in sec["lines"]]
            heading = title
        content = [c for c in content]
        while content and not content[-1].strip():
            content.pop()
        while content and not content[0].strip():
            content.pop(0)
        body.append("")
        body.append("#" * max(sec["level"], 2) + " " + heading)
        body.extend(content)
    text = "\n".join(body).strip() + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    if mask_dialogue:
        text = mask(text)
    head = (
        f"# 冷读视图 · {Path(path).name}\n\n"
        "只含观众看得见、听得见的部分；卡头、A / B 层、表演翻译、变化字段、执行卡、E 层已去掉。"
        + ("台词已遮住（静音测试）。" if mask_dialogue else "")
        + "\n"
    )
    return head + "\n" + text, report


def main(argv=None):
    p = argparse.ArgumentParser(description="分镜卡冷读视图")
    p.add_argument("card")
    p.add_argument("--mask-dialogue", action="store_true")
    p.add_argument("--list", action="store_true")
    args = p.parse_args(argv)
    if not Path(args.card).is_file():
        print(f"找不到文件：{args.card}", file=sys.stderr)
        return 2
    text, report = build(args.card, args.mask_dialogue)
    sys.stdout.write(text)
    if args.list or report["未识别"]:
        print("\n---")
        for k in ("保留", "去掉", "未识别"):
            if report[k]:
                print(f"{k}：" + " · ".join(report[k]))
        if report["未识别"]:
            print("未识别的小节没有进冷读视图；按冷读顺序手动读它们（先跳过卡头和 A / B 层）。")
    if not any(k for k in report["保留"]):
        print("没有认出任何可冷读的小节：这张卡的格式不认得，按冷读顺序手动读。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
