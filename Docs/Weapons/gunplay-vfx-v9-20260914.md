# Gunplay V9：手枪火光与连续扩散烟雾

按用户要求缩小手枪火光，保留步枪火光，并将逐发烟团改为一片持续形成、扩散和消散的烟雾。

## 火光范围

运行时通过 `IsPistolWeapon()` 分类，目前包含 M1911 和 Dan Wesson 715。手枪火光尺寸乘数为 `PistolFlashScale=0.45`，同时覆盖 Niagara 与备用火光；步枪乘数仍为 1，火光颜色、层次、寿命、随机焰瓣和 V8 柔边材质均保持原值。消音器及 ADS 的既有缩放继续叠加。烟量不使用这个手枪火光乘数。

`NS_FPS_MuzzleFlashV9` 从 V8 复制，仅移除 `Muzzle_Smoke` 发射器。保留其余火光发射器原样，避免每次开枪附带一团旧式喷烟。

## 团状感的来源与这次修改

V8 的每发烟与停火烟各自启动一次独立 Niagara 系统，使用带完整团状轮廓的烟雾序列图。透明度增大后，每团的出生、边缘与消失更容易被看到。这个问题主要在发射节奏与材质形状，不是单纯的贴图分辨率不足。

V9 使用一个独立、持续运行的烟雾组件。每次开枪只延长供烟窗口，不再重置粒子、重新启动整团动画。Niagara 已移除一次性爆发模块，改用 `User.SpawnRate` 驱动的连续发射，供烟时为每秒 60–80 层，随热量平缓增加，和子弹发射次数解耦。停火后保留约 0.26–0.55 秒供烟窗口，再平滑降到零。

新材质 `M_MuzzleSmokeSheetV9` 使用项目自编的世界空间连续密度噪声和大范围柔边。相邻烟层采样同一个缓慢移动的密度场，不再各自显示一张完整烟团图。采用受光的半透明白烟，多层低透明度叠加形成云状密度，保留深度遮挡与接触淡出。

烟层出生在真实枪口，出生后保持世界空间。初始前冲约 27 cm/s，通过阻力减速，继续向上及侧向飘移。每层在 1.6–2.0 秒内扩大至出生尺寸的约 2.65–2.95 倍，并连续降低透明度。供烟结束后等最后一层消散才停用组件，再次开火时仍存在的烟层继续保留。

实现采用持续重叠的烟层呈现连片扩散，不使用实时流体求解。通常无需添购美术包；后续如需要明显的三维翻卷或体积自遮阴，再考虑专门的体积烟雾资产。是否达到用户希望的连片观感仍需实际游戏反馈。

## 作者源与接入

- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`：手枪乘数、独立烟雾组件、供烟时间、回收及引用。
- `Tools/AssetPipeline/build_gunplay_presentation_v9.py`：复制 V8、移除逐发烟团、改造连续发射系统及制作新材质。
- `SourceAssets/GunplayVFX20260914/ContinuousSmoke.hlsl`：项目原创连续密度材质源码。
- `/Game/Weapons/GunplayFX/NS_FPS_MuzzleFlashV9`、`NS_FPS_MuzzleSmokeStreamV9`、`M_MuzzleSmokeSheetV9`。

恢复时先恢复 V8 及其合法 Epic NiagaraExamples 依赖，再运行 V9 生成器。保留原资产与 V8，不公开分发第三方派生二进制。曳光、枪身抛壳点、转轮手枪射击不抛壳和 LPVO 1–6x 隐藏弹壳规则继续保留。

本轮按用户规则完成开发、资产制作和必要构建；不运行游戏测试、截图或视觉验收，观感由用户测试。

资产制作完成：`Saved/Logs/GunplayV9-Assets-20260914-b.log`，三项资产保存完成，两套 Niagara 编译完成。生成清单为 `Saved/GunplayVFX20260914/created-assets-v9.json`。Python 制作成功；Commandlet 整体退出码 1 来自项目已有的 GameFeatureData 资产管理配置错误，没有改动该无关配置。

普通 Editor 原生构建完成：`Saved/BuildEditor/build-20260914-083917.log`，`Result: Succeeded`。未启动游戏或执行测试。

## 用户反馈后的材质修复

用户反馈游戏中烟雾显示为马赛克。现有运行日志 `Saved/Logs/FPSGAME_2.log` 明确记录 `M_MuzzleSmokeSheetV9 missing usage flag NiagaraSprites! Default Material will be used in game.`：V9 新建材质未显式设置 Niagara Sprite 使用标记，运行时被默认棋盘材质替代。

生成器已补充 `set_base_material_usage(...MATUSAGE_NIAGARA_SPRITES, True)`，同时将材质编译错误作为制作失败处理。专项修复入口为 `Tools/AssetPipeline/repair_gunplay_smoke_material_usage.py`，仅修复、编译并保存当前烟雾材质。该修复不修改连续供烟逻辑、手枪火光尺寸或步枪火光。

修复材质已完成编译并保存：`Saved/Logs/GunplayV9-SmokeUsageRepair-20260914-b.log` 记录 `GUNPLAY_SMOKE_SPRITE_USAGE_REPAIRED`。使用 D3D12 资产编译入口，未加载游戏地图、截图或渲染预览；Python 执行成功，进程退出码 1 仍来自无关的 GameFeatureData 配置错误。首次保存因其他编辑器占用资产失败，等待其退出后完成保存。此次无原生源码改动，不需要再次构建 C++。
