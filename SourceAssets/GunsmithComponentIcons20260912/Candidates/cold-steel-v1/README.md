# 冷钢部件分类图标 · 已采用来源（原候选 V1）

2026-09-12。**当前状态：用户后续要求“整体接入游戏”，九类图标已随改造台接入 UE。** 原始 RGB PNG 保持不变，游戏内使用 `M_CategoryIcon` 近黑背景透明合成材质；这不等同于生成了 RGBA 源图。字体、响应布局与真实渲染验收见 [正式接入记录](../../../../Docs/UI/gunsmith-cold-glass-implementation-20260912.md)。

以下为图标材质与轮廓评审时的历史记录，当时授权为“升级计划＋可视化方案，确定后再改 UE”；分类可用性以运行时枪械目录为准。

九枚图标统一采用银灰拉丝面、石墨凹槽、细倒角和左上柔光，配合上一轮保留原枪械库、外围黑—灰的面板方案。图片中不包含名称、数字、选中标记或禁用文字。

## 候选总览

|  |  |  |
|---|---|---|
| ![瞄具](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/01-optic-candidate-v1.png) | ![枪口](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/02-muzzle-candidate-v1.png) | ![弹匣](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/03-magazine-candidate-v1.png) |
| 瞄具 | 枪口 | 弹匣 |
| ![前握把](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/04-underbarrel-candidate-v1.png) | ![枪管](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/05-barrel-candidate-v1.png) | ![后握把](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/06-reargrip-candidate-v1.png) |
| 前握把 | 枪管 | 后握把 |
| ![枪托](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/07-stock-candidate-v1.png) | ![扳机](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/08-trigger-candidate-v1.png) | ![战术挂件](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/09-tactical-candidate-v1.png) |
| 枪托 | 扳机 | 战术挂件 |

## 分类对应

| 文件 | 类别 | 当前目录用途 |
|---|---|---|
| [01-optic-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/01-optic-candidate-v1.png) | 瞄具 | 现有可用类别 |
| [02-muzzle-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/02-muzzle-candidate-v1.png) | 枪口 | 现有可用类别 |
| [03-magazine-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/03-magazine-candidate-v1.png) | 弹匣 | 现有可用类别 |
| [04-underbarrel-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/04-underbarrel-candidate-v1.png) | 前握把 | 现有可用类别 |
| [05-barrel-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/05-barrel-candidate-v1.png) | 枪管 | 待扩展类别的视觉候选 |
| [06-reargrip-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/06-reargrip-candidate-v1.png) | 后握把 | 待扩展类别的视觉候选 |
| [07-stock-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/07-stock-candidate-v1.png) | 枪托 | 待扩展类别的视觉候选 |
| [08-trigger-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/08-trigger-candidate-v1.png) | 扳机 | 待扩展类别的视觉候选 |
| [09-tactical-candidate-v1.png](D:/FPS3D/FPSGAME/SourceAssets/GunsmithComponentIcons20260912/Candidates/cold-steel-v1/09-tactical-candidate-v1.png) | 战术挂件 | 待扩展类别的视觉候选 |

这些是类别符号，并非已安装配件的精确产品缩略图。例如“弹匣”用弧形盒式弹匣轮廓表示整个类别；当前安装大弹鼓时，应由名称或配件卡展示具体对象。

## 试排建议

- 左栏先以 48px 正方形图标框、完整中文类别名和一行部件状态试排；32px 作为紧凑对照，16px 不适合表达本轮材质。
- 行高约 64–72 逻辑单位，左栏独立滚动，最后一项与主操作均可到达；不为了容纳九枚图标缩小整台 UI。
- 常态保留中性银灰；选中通过 UI 的银白标线、轻背景和文字表达。禁用通过 UI 降低图标不透明度并显示“待扩展”，不烘入 PNG。
- 图标保持锐利；磨砂玻璃属于其后方卡片的渲染效果。

## 候选阶段的历史资源状态

候选交付当时为带深色背景的 RGB PNG，尚无 UE 纹理或实机试排。后续已按页首记录接入 UE：原图保留 RGB，透明显示由材质合成，不宣称另有 RGBA 源图或多尺寸发布包。历史候选状态保留在 manifest，当前状态见其中的 `currentIntegration`。

九张原图均为 1254×1254、RGB PNG。候选阶段曾逐张查看完整图，检查主体、材质、轮廓、留白及无文字；复制后逐项比对 SHA-256 一致。文件尺寸、像素格式和散列记录在 [file-audit.json](file-audit.json)。这些为对应日期的记录，本轮工作流整理不重新进行视觉测试。

源文件保存于本目录，原始生成结果保留在本机 Codex 的 generated_images 目录。PNG 不随本轮文档发布；当前分类可用性读取真实枪械目录，不使用历史候选清单的 `available` 作为运行数据。

## 生成来源

使用当前内置图像生成器，未指定也未声称 image2.5。先生成瞄具作为材质参考，再逐枚生成其余八种部件；每枚各用一次独立生成调用。后八枚只参考瞄具的材质、光照和黑灰色调。

完整提示词、来源路径及历史逐项视觉检查见 [manifest.json](manifest.json)。生成结果为二维图标，不包含 PBR 材质贴图或三维模型。

当前依据：[改造台正式接入](../../../../Docs/UI/gunsmith-cold-glass-implementation-20260912.md) 与 [冷钢 UI 规则](../../../../Docs/UI/ui-cold-steel-design-system.md)。旧候选提案已移入 trash，见 [归档记录](../../../../Docs/UI/panel-workflow-archive-20260913.md)；本目录九张已采用图标继续作为有效源文件保留。
