# 火球图标火红配色（2026-09-14）

## 目的与视觉选择

用户反馈火球辨识度不足，尤其在快捷栏，要求在现有基础上调整为火红色并给出主体／背景取舍。采用主体改色：朱红和橙红焰身、深红凹槽、少量琥珀亮黄球心；保留原六边形银框、石墨暗底、金属浮雕与斜向火球轮廓。暗底用于拉开主体明度，整块红底会削弱红色火焰边缘。该方案属于冷钢系列的火元素身份色。

## 布局、数据与状态

- 沿用 `ColdSteelQuickSlot` 的 48px 居中 ScaleToFit 和技能页 48px 图标区域；宽窄窗口、字号、按键、数量、冷却遮罩及层序均沿用现有控件。
- `Content/ColdSteelData/skills.json` 的 `fireball.icon` 改为 `Skills/fireball_ember_red.png`；快捷栏、技能页及升级提示读取同一配置，拖影复用当前画刷。
- 图标仍为本地 PNG，由现有 UMG／Slate 加载入口管理；无新的输入、事件订阅、存档字段或资源扣除。缺蓝变暗、冷却、完成闪光、失败占位和拖放交换继续由原模型与控件处理。
- 图片和定义在本轮已启动的游戏中可能已缓存；重新进入游戏使现有初始化入口读取新配置。

## 制作、接入与恢复

- 内置 `image_gen` 以 `SourceAssets/Fireball20260914/fireball_cold_steel.png` 为编辑输入，仅按上述设计改变主体颜色／材质表现。
- 新源：`SourceAssets/Fireball20260914/IconEmberRed/fireball_ember_red.png`。同目录保存完整 `prompt.txt` 和 `provenance.json`。
- 运行图：`Content/ColdSteelData/Skills/fireball_ember_red.png`，直接复制生成结果，不额外像素处理。运行 UI 使用 PNG，无需为此新建 Texture uasset 或启动编辑器导入。
- `Tools/UI/prepare_cold_steel_skill_icons.py` 的火球映射已同步到红色源，后续恢复会复制当前版本。该全量恢复脚本本轮未执行，运行图已单独复制。
- `FPSGAME.Build.cs` 原有 `Content/ColdSteelData/...` UFS 依赖覆盖该路径；本次无 C++ 改动，不需要原生编译。
- 旧银灰源图及其历史记录继续作为编辑输入保留，本轮不清理旧资产、不提交或推送 Git。
- 正式 UI 配色规则及个人／工程魔法技能入口同步记录当前火球图源。

## 交付状态

完成图标制作、PNG 复制、技能配置及恢复映射更新。未进行自测、lint、静态检查、游戏启动、截图或实机验收，由用户测试。生成的素材图不代表游戏实机显示结果。
