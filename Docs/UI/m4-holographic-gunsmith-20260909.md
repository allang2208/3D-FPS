# M4A1 全息镜改造接入

## 机械瞄具折叠接入

原模型的瞄具几何合并在 M4 Body 和当前使用的 Kmode 护木中，未自带折叠骨骼或动作。本次从最新空仓换弹枪机版本提取后照门 420 个顶点、前准星 561 个顶点，保留底座，作为独立组件连接 WPN_root。新增默认模型 `/Game/Weapons/M4FoldingSights/SK_M4_FoldingSights`，共享原骨架；原始模型和空仓换弹动画仍保留。

选择全息镜时，前后瞄具在 0.18 秒内绕各自支点转动 90 度；卸下时恢复。此收放是游戏表现，没有新增手部操作动画。源几何、支点记录和可编辑 Blender 文件见 `SourceAssets/M4FoldingSights20260909/PROVENANCE.md`。

截图复查还发现每五秒自动保存会重新应用已安装配件，覆盖未提交的预览。`ApplyColdSteelProfile` 现在对当前正在改造的同一实例保留草稿外观，关闭时恢复已安装状态，草稿不会写入存档。

正式模块 `UnrealEditor-FPSGAME-2026090992.dll` 编译成功。1280×720 独立游戏进程写入 41 项、重启读档 38 项，共 79 项通过、0 失败、两进程退出 0。包括前后折叠/复位、取消、切枪、换弹跟随、自动保存期间保留机械瞄具预览且不提交草稿。全息镜 ADS 侧倾 0.0000°，导轨误差 0.0508°，准心误差 0.0000 px。

日志：`Saved/M4GunsmithAudit/folding-final-1280-write.log`、`folding-final-1280-reload.log`。已实际查看全息 ADS、换弹与恢复机械瞄具截图。此前 candidate 检查不能代替本轮自动保存预览回归。

![全息镜与折下的机械瞄具](../../Saved/M4GunsmithAudit/folding-final-1280-reload-m4-holographic-ads.png)

![卸下全息后恢复机械瞄具](../../Saved/M4GunsmithAudit/folding-final-1280-reload-m4-iron-restored.png)

当前已打开的 UE 编辑器需要保存工作并重启，才能加载新 C++ 模块。验证使用隔离存档，没有修改玩家正式存档。

## 歪斜复查与修复

用户反馈全息镜歪斜后，读取原 M4 骨架绑定姿态和 `M4_aim` 动作，测得旧安装框架与导轨法线相差 5.0003°，旧瞄准姿态中的镜体侧倾约 5.0000°。源数据记录在 `SourceAssets/M4Holographic20260909/roll-source.json`。

原因是安装框架使用组件 Z 轴替代导轨法线，并且 ADS 只对齐前向轴，未约束侧倾。修复改用原枪 `WPN_RearSight` 坐标系的上方向作为导轨法线，同时以完整的前向/上方向框架校正 ADS。镜体与原枪仍刚性连接，手部、射击和换弹动作源文件未修改。

补充验证读取实际运行组件的镜体朝向和枪身骨骼朝向，并将镜体上方向投影到画面检查侧倾；同时检查换弹中的导轨对齐。先前 106 项检查包含准心位置，但没有检查镜框侧倾，不能作为镜体水平的证明。

修复后 1280×720 写入 32 项、独立进程读档 29 项均通过，进程退出 0。两阶段均测得 ADS 侧倾 0.0000°、导轨法线误差 0.0508°、准心位置误差 0.0000 px。已查看修复后的持枪与 ADS 截图。证据：`Saved/M4GunsmithAudit/rollfix-1280-write.log`、`rollfix-1280-reload.log`；编辑器模块 `UnrealEditor-FPSGAME-2026090971.dll` 编译成功。

![修正后水平的全息镜](../../Saved/M4GunsmithAudit/rollfix-1280-write-m4-holographic-ads.png)

本次修改前备份：`trash/M4HoloRoll-before-20260909`。

## 迁移检查

检查时 `UGunsmithSystem` 保留实例配件、草稿、属性合计、保存事务；`gunsmith.json` 武器数组为空，原枪匠界面已移除。当前原生 `ue_m4a1` 没有改造入口。历史六把 Godot 武器继续保持退役。

## 当前功能

- 持枪时按 J 打开当前 M4；背包中选中 M4 后点击“改造 · J”打开指定实例。
- 可选原厂机械瞄具、项目已有全息瞄准镜。支持持枪/瞄准预览、应用保存、撤销预览、Esc 关闭。
- 草稿只改变当前持枪的临时外观；关闭恢复已安装配置。未装备的 M4 可编辑保存，装备后显示对应配置。
- 配件存储在该物品实例 `gunsmith_parts.optic = holographic`。两把 M4 各自保存配置；存档版本沿用现有实例格式。
- 实体镜体挂接 `WPN_root`，继承持枪、后坐力和换弹动作。使用全息分划中心校准 ADS，并在开镜射击时沿实际分划位置计算射线。卸下后恢复原机械瞄具。
- 全息镜保持原枪属性，开镜 240 ms；射击间隔显示包含角色攻速的实际结果。即时命中武器的浮窗不再显示虚假的 0 m/s 弹速。
- 修正了底层改造系统只检查装备槽 6 的忙碌状态问题；活动武器槽 9 在装备过程中也拒绝提交改造。

## 验证

`Tools/UI/run_m4_gunsmith_acceptance.ps1` 启动独立游戏进程，使用专用 `ColdSteelProfile=M4GunsmithAudit_*`。不改正式玩家存档。

1280×720：写入阶段 28 项、重新启动读档阶段 25 项，均 0 失败，进程退出 0。检查包括非法配件拒绝、保存失败回滚、预览撤销、装卸保存、活动副武器槽保护、两实例配置隔离、真实控制器输入开火/换弹、弹药守恒、射线与分划一致，以及关闭界面后恢复移动/观察输入。稳定 ADS 分划中心误差 0.0000 像素。

日志：`Saved/M4GunsmithAudit/final-1280-write.log`、`final-1280-reload.log`。

960×540 也完成相同写入/重新启动两阶段，28+25 项均通过、进程退出 0，分划误差同为 0.0000 像素。两种尺寸共 106 项检查；已实际查看两种尺寸的最终截图，右侧配件操作完整可见。

![M4 全息镜改造与瞄准](../../Saved/M4GunsmithAudit/final-1280-reload-m4-holographic-ads.png)

![保留原手部动画的换弹](../../Saved/M4GunsmithAudit/final-1280-reload-m4-holographic-reload.png)

## 交付范围

本次完成原生 M4 与这一个全息镜的可用改造流程，不代表旧九类配件/六把武器全部迁移。镜内分划是有限距离的实体分划，不宣称完整光学准直模拟。未进行完整打包验收；已加入新配件目录的 cook 引用。

材质导入 commandlet 的现有 GameFeatureData 和 HTTP 端口错误与本配件独立；新材质经过实际 D3D12 游戏渲染，最终日志没有本配件材质编译失败。源资产、编辑源文件及哈希见 `SourceAssets/M4Holographic20260909/PROVENANCE.md`。

编译采用独立编号模块，避免关闭用户正在使用的编辑器。已运行的旧编辑器需要保存当前工作并重启以加载新 C++ 类型。回退前的相关文件保存在 `trash/M4Holographic-before-20260909`。
