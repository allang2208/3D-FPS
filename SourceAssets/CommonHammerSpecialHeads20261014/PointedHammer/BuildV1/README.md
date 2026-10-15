# 双棱尖头锤 BuildV1

> 2026-10-15 整理：本文为制作阶段记录；Before 快照已带散列移入 trash。最终发布状态和恢复入口见[整理说明](../../../../Docs/Publication/WarhammerMods20261015/README.md)。

依据用户确认的 `../ConceptV4/faceted-double-spike-design.png` 制作，2026-10-14。

## 模型与接口

- 选项 `pointed_hammer`，锤头槽 `hammer_heads`，特殊改造；锤类共享设计，首个宿主 `ue_steel_warhammer`。
- 一个模块同时替换左右锤头：双侧笔直收尖、实体纵向棱脊与凹槽，原装连接颈保留。中央锤座、柄部、握点与其余改造沿用现有内容。
- 作者轴 X 为锤头横向、+Z 为柄向；实际原装连接面 X ±0.040 m，保留至 ±0.075 m 的颈部。运行偏移 `[0,0,92.5000011920929]` cm。
- 成对模块 20,174 三角面。运行材质复用 `M_SteelWarhammerSurface` 与 `M_CommonHammerHeadSteel`，保留原装接口 UV 与法线，新增棱面使用 SteelUV 和过渡顶点色。
- 可编辑源 `PointedHammer_Editable.blend`；导出 `Export/SM_CommonHammerHeads_pointed_hammer_V1.fbx`。`prepare_author.py` 从现有锤头作者脚本生成本目录的独立 `author_pointed_hammer.py`，不改写原三款作者脚本。

## 已保存资产与目录

- StaticMesh：`/Game/Weapons/CommonHammerSpecialHeads20261014/PointedHammer/BuildV1/SM_CommonHammerHeads_pointed_hammer_V1`。
- Texture2D：`/Game/ColdSteelData/AttachmentIcons20260913/hammer_heads_pointed_hammer`。
- 共享选项写入 `Content/ColdSteelData/common-hammer-heads.json`；实际锻钢战锤模型映射写入 `warhammer-modules.json`。
- 当前用户数值为：物理伤害 +30%、攻击速度 +5%、攻击体力消耗 +15%、韧性伤害 −25%，攻击附带 15% 物理防御穿透。外形注册保留现有正式数值，数值修改通过独立入口同步；详见 [BalanceV2](../BalanceV2/README.md)。本目录导入与交付回执保留初次建模时的中性数值状态。
- `Source/FPSGAME/Weapons/GunsmithModificationTier.h` 按槽和 ID 识别特殊改造，不绑定单个武器定义。
- `Before/` 保留本次两份目录及品质分类头文件的修改前副本；重放登记只合并本选项，保留其他条目。

## 正式图标

`render_icon_source.py` 从最终模型取负 X 侧锤头，尖端左、连接端右、+Z 向上，用灰阶助手制作独立素材 `IconSources/pointed_hammer.png`，作者场景保存为 `PointedHammer_IconSource.blend`。运行成对模型不被裁切。

内置 image_gen 按 `icon-prompt.txt` 将实际模型素材与 `SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png` 母版合成。最终母图 `Icons/pointed_hammer.png`：厚倒角方框、四角铆钉、银色内环、深灰不透明底板及极窄透明外缘。正式 PNG 同步到 `Content/ColdSteelData/AttachmentIcons20260913/hammer_heads_pointed_hammer.png`。Texture2D 使用 UI 组、Editor Icon 压缩、sRGB、Never Stream 和无 mip。

## 执行记录

后台 Blender 制作、FBX 导出及正式图标制作已完成。`import_background.ps1` 使用既有资产批次互斥，后台 commandlet 实际导入并保存两项新资产，复用材质只读加载。`import_receipt.json` 为 `complete=true`，`commandlet_receipt.json` 为退出码 0，`registration_receipt.json` 记录正式目录登记。

Game Development 构建成功，47.74 秒、5 个动作；见 `game-build-receipt.json` 和 `game-build.log`。既有编辑器会话通过同一批次互斥调用 `CompileLiveCoding` 成功，返回 `Result: Success` 与 `Live coding succeeded`，见 `livecoding-result.txt`。该补丁更新当前会话，未更新普通 Editor 基础 DLL；当前编辑器保持运行，待其关闭后可通过 `build.ps1 -Target FPSGAMEEditor` 完成基础 DLL 构建。本次未为更新该 DLL 关闭或重启编辑器。

没有主动启动编辑器、PIE、游戏、检查或验收渲染。正式 UI 图标是本次制作资产，未运行游戏测试；装配与视觉效果由用户测试。
