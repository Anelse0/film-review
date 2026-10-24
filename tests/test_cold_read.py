"""cold_read.py 的回归测试：三种卡的格式、去掉意图层、遮台词。

运行：python3 -m unittest discover -s tests（在 skill 目录下）
"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import cold_read  # noqa: E402

CARD_NEW = """# s01-clip01 分镜卡〈标题里有意图〉

**版本：v1.0 · 2026-10-20** · 状态：待确认
**场景参数卡**：强度低
- **视觉方案**：只有一次推近，留给峰值。
- **峰值事件**：镜 2。

## 机位设计（S5 §5.1g）

### 空间锚点
方位：门=北

### 机位表
| 镜 | 机位在哪 | 朝哪拍 |
|---|---|---|
| 1 | 门边 | 朝南 |

### 核对
1. 左右：对

## 走位表

| 秒 | 谁 | 从哪 → 到哪 | 面朝 | 手里 | 动线含义 |
|---|---|---|---|---|---|
| 0–2 | A | 原地 | 镜头 | 杯子 | 示弱 |

## 镜头纵览

| 镜 | 时间 | 景别 | 台词（句 · 画内 / 画外整句） | 手法 |
|---|---|---|---|---|
| 1 | 0-2s | 中景 | A "Hello there." · 画内 | **峰值**：推 |

最长连续无台词 | 2 s（用户点头保留）

### 手法分布（导演偏好第五节）
| 手法 | 用在 |
|---|---|
| 推镜 | 镜 2 |

## 镜头 1（0-2s）· 峰值

**A**：让观众先知道他在撒谎。
**表演翻译**：心虚 → 词典行 → 可见：眼睛往下一落
**C**：中景，轻微手持，焦点在 A【变化：景别 中→近｜机位 固定→推｜光 =｜幅度 1→2】
- 台词：A "Hello there."（轻声）
- 光源：窗光从画左

## 贯穿要求
- 人物站直

## E 层
| 项 | 值 |
|---|---|
| 峰值镜 | 1 |

## 执行卡
| # | 项 | 证据 |
|---|---|---|
| 1 | 场景参数卡 | 卡头 |
"""

CARD_EP05 = """# EP05 · 场 03 · clip02 分镜卡

## 剧本锁定（用户给定，逐字）
A: "Line one."

## 纵览

### 场次纵览
| 场次 | 这一条讲什么（一句） |
|---|---|
| 03 | 他在撒谎 |

### 镜头纵览
| 镜 | 时间 | 景别 | 内容 / 台词 |
|---|---|---|---|
| 1 | 0–2 | 近景 | "Line one." |

## clip 头部
- 视觉方案：意图在这里

## 分镜（C 层）

**镜 1（0–2s）**
- A：一开场就是他在上班。
- C：【近景，平视，固定】【变化：景别 中近｜机位 固定｜光 暖｜幅度 2】他抬眼。台词（A）："Line one."

**镜 2（2–4s）**
- A：插入。
- C：【特写，台面上的手】手放下杯子。

## 风险
- 意图泄漏
"""

CARD_EP04 = """# EP04 s01 · clip02 导演分镜

**表演来源**：用户说浪漫

## v1.2 修订（用户；C 层以本节为准）
- 光：篝火是主光。

## 镜头 1（0-3s）
**A**：交代篝火。
**B**：两人坐下。
**C**：中近景双人，固定｜变化：景别 中近双｜机位 固定｜光 篝火侧光｜幅度 2｜事件：两人坐下

## 镜头 2（3-7s）★ 峰值
**A**：发问。
**C**：近景，固定｜事件：他看海｜台词（Rhett）："You ever think about it?"

## 待复核（不改剧本）
- 交用户
"""


def run(text, **kw):
    """返回去掉说明头之后的正文和小节报告。"""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        out, report = cold_read.build(path, **kw)
    finally:
        Path(path).unlink()
    return out.split("\n\n", 2)[2], report


class NewFormat(unittest.TestCase):
    def setUp(self):
        self.text, self.report = run(CARD_NEW)

    def test_keeps_visible_parts(self):
        for s in ("### 机位表", "## 走位表", "## 镜头纵览", "## 镜头 1（0-2s）", "## 贯穿要求", "窗光从画左"):
            self.assertIn(s, self.text)

    def test_drops_intent_layers(self):
        for s in ("只有一次推近", "让观众先知道", "心虚", "峰值", "示弱", "用户点头", "执行卡", "空间锚点", "左右：对", "推镜", "变化："):
            self.assertNotIn(s, self.text, s)

    def test_container_not_unknown(self):
        self.assertEqual(self.report["未识别"], [])


class Ep05Format(unittest.TestCase):
    def setUp(self):
        self.text, self.report = run(CARD_EP05)

    def test_storyboard_shots(self):
        self.assertIn("### 镜 1（0–2s）", self.text)
        self.assertIn("### 镜 2（2–4s）", self.text)
        self.assertIn("手放下杯子", self.text)

    def test_drops_a_layer_and_meta(self):
        for s in ("一开场就是他在上班", "插入。", "意图在这里", "他在撒谎", "意图泄漏", "变化："):
            self.assertNotIn(s, self.text, s)

    def test_no_unknown(self):
        self.assertEqual(self.report["未识别"], [])


class Ep04Format(unittest.TestCase):
    def setUp(self):
        self.text, self.report = run(CARD_EP04)

    def test_revision_and_c(self):
        self.assertIn("修订", self.text)
        self.assertIn("篝火是主光", self.text)
        self.assertIn("事件：两人坐下", self.text)

    def test_drops_ab_and_variation(self):
        for s in ("交代篝火", "两人坐下。", "发问", "★", "浪漫", "交用户", "幅度 2"):
            self.assertNotIn(s, self.text, s)

    def test_heading_label_stripped(self):
        self.assertIn("## 镜头 2（3-7s）\n", self.text)


class Mask(unittest.TestCase):
    def test_mask_dialogue(self):
        text, _ = run(CARD_EP04, mask_dialogue=True)
        self.assertNotIn("You ever think", text)
        self.assertIn("［台词］", text)

    def test_mask_keeps_chinese_quotes(self):
        text, _ = run(CARD_NEW.replace("窗光从画左", '"门在镜头身后"'), mask_dialogue=True)
        self.assertIn('"门在镜头身后"', text)


if __name__ == "__main__":
    unittest.main()
