# Changelog

## 0.1.0 · 2026-10-23

首版。依据：`/Users/sky/Desktop/Film/research/reports/欧美导演工作方法与工具.md`（好莱坞导演档案、导演×摄影指导、经典审阅框架、业内审阅实践四路调研；欧洲导演、美术服装调色、剪辑与声音三路按用户要求中途停掉）。

- 定位：本剧常驻导演 / 摄影指导式的设计审阅，补 film-director 脚本（查有没有、过不过线）与八道审阅（管 Prompt 措辞）之间的设计层。
- 流程五步：加载本剧审阅档案 → 冷读（`scripts/cold_read.py`，可遮台词做静音测试）→ 对照意图 → 七道关十七个维度（`references/rubric.md`）→ 出意见（`templates/review.md`）。
- 本剧审阅档案：项目根目录 `review-profile.md`，从导演偏好文档、剧本规则表、项目记忆、成片证据派生（`references/profile.md`、`templates/review-profile.md`）。
- 审阅不派 subagent（用户 2026-10-19）：冷读是同一审阅者的独立工序。
- 第一轮测试：Offset 已有用户评价的成片回测（`evals/`）。
