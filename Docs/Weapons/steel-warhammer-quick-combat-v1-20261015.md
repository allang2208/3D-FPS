> 当前快速近战已替换为 [锤头直刺 V3](steel-warhammer-quick-combat-head-thrust-v3-20261015.md)。本文横柄前顶方案已被用户否定，保留作历史恢复记录。

> 当前动作为 [前顶强化 V2](steel-warhammer-quick-combat-impact-v2-20261015.md)。以下为 V1 历史记录；原制作脚本和正式动画备份保留在 `SourceAssets/SteelWarhammer20261014/QuickCombatImpactV2/Before/`。

# 双手战锤快速近战：双手横柄短顶 V1

用户确认采用双手横柄短顶，整体约 0.5 秒、0.15 秒命中，双手持续握柄，肩肘手腕自然衔接，避免拉伸和遮挡镜头。

## 动作合同

- 作者时长 0.5 秒，300 fps；命中 0.15 秒，跟随到 0.175 秒，随后连续恢复待机。
- 使用 `NormalComboV4` 当前待机和 V7 原生手模。五指局部姿态及双手相对 `WPN_root` 的握点全程保持；不松手、不换握。
- 0–0.065 秒略收锤柄并压平；随后快速前送，命中时相对待机前移 14 cm、上移 2.5 cm、左移 1.5 cm，柄身压平约 11°。短暂跟随后回收，首末帧均为原待机。
- 位置与旋转使用连续速度、加速度的分段曲线。肩带向前下方提供有限支撑，大小臂保持原生长度，肘部留弯曲余量；手臂放在画面下方。
- 接触标记位于两手之间的柄身前表面，作者脚本写入 `WarhammerQuickCombatMarker.h`；不是锤头砸击。

## 接入

- `ColdSteelSkillModel::TriggerQuickCombat` 将战锤的 F 键／快捷栏请求分派给工具执行器，普通采集工具不受影响。
- 新 `EQuickCombatStyle::Warhammer` 复用 `UFPSQuickCombatComponent` 的体力提交、技能修炼、动作占用、命中音和恢复释放。时钟固定为 0.5 秒，不受普通攻击速度改造影响。
- 工具执行器在角色合成相机前推进一次动作时钟，动画采样和接触使用同一年龄；跨帧超过 0.15 秒时仍先求值到精确接触姿态，再进行一次判定。
- 复用快速近战数值和单目标查询；只有既有改造开启快速近战 AOE 时，使用同一球扫范围的群体查询。沿用低位小目标补判和场景遮挡；没有加入重击冲击波或重击眩晕。
- 命中快照使用实际战锤，附魔、削韧、击退及快速近战改造继续生效。客户端沿现有快速近战序号上报，服务器复算伤害和数值；战锤普通攻击服务器接触链不会重复结算本次 `0x80` 快速近战。
- 打断、换武器、死亡、输入受阻或动作结束都会释放占用。进入动作时清除砸地 IK，并保留实时入场衔接。第三人称状态标识为 `WarhammerShaftCheck`，沿现有工具原生手臂采样链。
- 装备时异步加载新动画，不在触发或每帧路径同步加载资源；旧存档中的战锤无需修改物品数据。

## 资产与交付边界

- 源目录：`SourceAssets/SteelWarhammer20261014/QuickCombatV1/`。
- 可编辑文件：`Warhammer_QuickCombat_Editable.blend`；FBX：`Export/A_Warhammer_QuickCombat.fbx`。
- 正式资产：`/Game/Weapons/SteelWarhammer20261014/QuickCombatV1/A_Warhammer_QuickCombat`。
- 修改前相关源码在 `Before/`，制作参数在 `authored.json`；导入、构建和交付状态分别由 `import_receipt.json`、`build_receipt.json`、`delivery.json` 记录。
- 正式动画已通过无界面 commandlet 导入、完成动画编译并保存，`import_receipt.json` 为 `complete=true`。
- `FPSGAMEEditor Win64 Development` 和 `FPSGAME Win64 Development` 正式构建均返回 exit 0、`Result: Succeeded`（最终构建分别 39.41 秒、59.61 秒）。DLL、Game 可执行文件和 `delivery.json` 已落盘；完成后没有启动编辑器或游戏。

本次正式构建遇到现有并行开发源码的阻断错误，作了必要的小范围修正：M66 三个复制函数使用 `DOREPLIFETIME` 要求的参数名；尸体组件通过 `.Get()` 取 `TObjectPtr`；M66 调试 RPC 参数改名以免 UHT 生成代码遮蔽成员；技能资源准备代码使用公开的压缩数据可用性接口替代 UE 5.8 受保护的 `IsCompiling`。旧文件已保存在 `Before/`，未运行相关调试场景或测试。

仅进行后台制作、接入和必要构建，未运行游戏、渲染、自动测试或联机验收。实际握姿、镜头遮挡、判定手感和多人表现交由用户体验。
