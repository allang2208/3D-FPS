# 符文长剑剑身Ⅱ：语义图标

用户否定上一版符文主体方案后，本轮依据改造效果的语义重新生成图标。内置 image_gen 分别生成 5 张原创插画，同步替换剑身Ⅱ的 5 个选项及 1 个分类入口。分类入口复用中性的原装核心图。

| 选项 | 图标语义 |
| --- | --- |
| 原装剑身Ⅱ | 银灰金属核心，表示尚未附加改造 |
| 共鸣符文 | 青色核心与同心波环，表现魔力共鸣 |
| 侵蚀符文 | 紫色能量裂解金属，表现侵蚀及附加魔法伤害 |
| 导魔符文 | 右侧多股蓝色能量汇聚为向左的束流，表现导魔与增强 |
| 金色符文强化 | 金色沙漏、回转箭头和命中闪光，表现命中缩减冷却 |

风格统一为冷钢银色倒角、深色金属凹部、克制的魔法发光和清晰的立体轮廓。所有图标采用正面视角、左上主光和统一留白；有明确流动方向的元素向左。游戏交付文件为 1024×1024 RGBA 透明 PNG，不带文字、卡片底板或外框。

## 制作文件

- `prompts.json`：完整通用风格及各张图标的生成提示词；生成方式为内置 image_gen。
- `generated_sources.json`、`Generated/`：生成来源路径及项目内原始图片副本。
- `package_icons.py`：保留原色、比例和透明度，只将主体等比缩放并居中到统一画布。
- `Icons/`、`packaging_receipt.json`：6 张交付 PNG 及制作回执。
- `semantic_icons.jpg`：五张选项图的可查看总览；深色背景与中文名称仅用于这张总览。
- `Before/`、`baseline.json`、`options_snapshot.json`：替换前图标与选项记录。

## 接入

通过现有互斥桥 `Tools/AssetPipeline/mcp_call_codex.ps1` 执行 `deploy.py`，已保存 6 个 PNG 和对应 UE Texture。目标仅限 `Content/ColdSteelData/AttachmentIcons20260913/ue_rune_sword_blade_2_*` 及 `ue_rune_sword_category_blade_2`。UE 贴图采用 UI、sRGB、无 mip；保存记录见 `deploy_receipt.json` 和 `deploy-result.txt`。

本轮不修改符文属性或游戏内效果，不需要 C++ 构建。未启动游戏或运行测试；重新打开改造栏后由用户自行测试显示效果。
