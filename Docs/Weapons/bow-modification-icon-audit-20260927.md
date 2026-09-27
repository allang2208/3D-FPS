# 弓改造栏图标审计与灰阶替换（2026-09-27）

用户要求审计弓改造栏全部图标，统一无彩色配色、重制替换，并更新 skill。已完成正式 PNG 替换及对应 21 个 UE Texture2D 的导入保存。未运行游戏测试；用户自行确认游戏内展示。

## 覆盖范围与问题

从 `BowGunsmith.cpp::LoadBowCatalog` 和 `bow-gunsmith.json` 枚举弓的五槽；该分支自行生成每槽 `false` 原装选项，不合并枪械 `common_options`。由 `M4GunsmithLayout.cpp` 确定武器专属 PNG 优先、共享图回退和实际缓存键。

| 槽位 | 分类入口 | 原装 | 改造选项 | 图标数 |
|---|---:|---:|---:|---:|
| 弓体 riser | 1 | 1 | 4 | 6 |
| 握把缠带 grip | 1 | 1 | 4 | 6 |
| 弓弦 string | 1 | 1 | 1 | 3 |
| 箭台 arrow_rest | 1 | 1 | 1 | 3 |
| 瞄具 sight | 1 | 1 | 1 | 3 |
| 合计 | 5 | 5 | 11 | 21 |

旧图均存在武器专属 PNG，没有缺图；主要问题如下：

- 木色、绿色绳圈、棕色皮革等未采用统一无彩色配色。
- 原装缠带图仍来自旧模块源，未跟随 GripContactV22 贴合后的模型。
- 瞄具图仍为早期雕刻木瞄具，与实际 WoodBracketV19 圆环木瞄具不符。
- `bow_dark_sight_no_sight.png` 曾复制 `optic_false.png`，实际内容为枪械照门，不能表示拆除弓瞄具。
- 弓弦按真实直径整根渲染，缩到 48／64 像素后接近不可见。
- 原规则只明确中性照明与实际材质，缺少统一无彩色条款；现已按用户本次要求更新。

## 制作结果

21 张全部替换；保留 0 张、缺图补齐 0 张。15 次独立内容渲染，5 张分类图复用对应原装图，强拉力弓胎作为数值调校复用原装弓体图，不虚构新外观。

- 四款弓体：`BowSurfaceRepair20260927/Bow_ElasticBodies_Outward.blend` 中当前 ElasticV15 对应对象。
- 原装／蜡麻缠带：`BowGripContact20260927/Bow_GripContact.blend` 的 `SM_Bow_GripWrap_Fitted`，蜡麻使用其实际材质覆盖的灰阶版本。
- 三款独立握把：`BowGripSeries20260927/Bow_GripSeries.blend` 中 GripSeriesV20 对应对象。
- 两款箭台：`BowModular20260926/Bow_ModularParts.blend`，恢复实际 UE 雕刻木材质的纹理、粗糙度和法线后再去色；不使用源场景的简单占位材质。
- 瞄具：`BowWoodBracket20260927/Bow_WoodBracketSight.blend`，相机保持水平并转向 35°，呈现圆环、竖杠和完整安装座。
- 弓弦：当前目录锚点与两段中心线，真实半径 0.09／0.065 cm；仅图标渲染使用 64 像素下 1.2／1.0 像素最小线宽。
- 拆除：透明底中性圆圈减号。未修改共享 `optic_false.png`，其他武器不受本轮影响。

全部为 1024×1024 RGBA 透明 PNG，主体占幅约 84%，中性灰阶光照与纹理明暗。图标场景独立覆盖基色，保留法线、粗糙度和几何结构；未修改游戏材质、装备栏图标、改造数值、动作及存档。

## 图标审计与落盘证据

已逐张查看前后总览，并查看最终 48／64 像素缩略图；查看编织握把全分辨率以确认纹理起伏。最终图标无明显彩色，孔洞透明、主体未裁切，最小画布边距 77 像素。无缺图。21 张 PNG 的 SHA256 与对应 Texture2D 导入回执逐项一致。

导入使用当前已运行编辑器的共享 MCP 批次桥。因初次处于 PIE 导致保存前置条件不满足，结束该次游玩后完成 21 个 Texture2D 保存，编辑器保留，未重新启动游戏。纹理设置为 UI 组、sRGB、EditorIcon 压缩、无 mipmaps，并登记本轮来源元数据。纯资源与文档更新，不需要原生编译。

工作目录：`SourceAssets/BowIconAudit20260927/`。

- `before-audit.json`、`before-contact-sheet.png`：首次清单、哈希及旧图基线。
- `source-inspection.json`：实际模型对象、材质与纹理来源。
- `render_icons.py`、`Bow_MonochromeAttachmentIcons.blend`、`render-receipt.json`：可重建作者源及渲染参数。
- `icon-install-receipt.json`：首次 PNG 部署回执，保留不覆盖。
- `icon-install-final-receipt.json`：恢复箭台当前材质后的最终 PNG 回执。
- `icon-import-receipt.json`：21 个成功保存的 Texture2D 路径及源图哈希。
- `after-audit.json`、`after-contact-sheet.png`：正式安装图及缩略图总览。
- 变更前 PNG／uasset 备份：`Saved/BowIconAudit20260927/Before/`。

## 技能规则更新

个人目录与项目内 `ue5-weapon-workflow/references/attachment-icons.md` 已同步本轮规则，内容一致；两份 `SKILL.md` 的图标路由条目同步更新。新增统一灰阶的适用范围、保留结构细节、真实模型版本、分类图复用、拆除符号、圆环瞄具视角例外和细线可辨性规则。此处审计只覆盖弓，未宣称其他武器图标已完成改版。
