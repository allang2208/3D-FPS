# 伐木斧 V3：右后蓄势、左下快劈与嵌入拔斧

基于用户认可方向的 V2 继续修改：右后蓄势更深、下劈更快且向左下带出；有效采集命中时停帧、卡住、上下撬柄、拔出，再进入恢复，并同步镜头反馈。继续使用 H3 整手握点和 V2 腕肘支撑，不修改手指、骨长、蒙皮或工具模型。

## 动作与时序

| 实际时间 | 动作 |
| --- | --- |
| 0–0.275 s | 向右后上方收斧，握持中心达到约 `(右 23.5, 前 20.5, 高 13.5) cm` |
| 0.275–0.405 s | 右后压实、短暂停蓄，最终中心 `(24.5, 19.5, 14) cm` |
| 0.405–0.48 s | 约 75 ms 加速左下劈；0.405 s 挥动声，0.48 s 唯一采集提交 |
| 空挥 0.48–0.61 s | 继续左下带出，中心到 `(-36.5, 23.5, -31) cm` |
| 空挥 0.61–1.10 s | 绕低位回握 |
| 命中 0.48–0.555 s | 完整接触姿态冻结约 75 ms，镜头冲击同步发生 |
| 命中 0.555–0.63 s | 斧刃留在接触支点，微小受力余颤 |
| 命中 0.63–0.91 s | 以刃口为支点上下撬柄：约 `+5.5°、-4°、+4.5°、-2°`，随后归零 |
| 命中 0.91–1.04 s | 抽斧：向后 12.5 cm、向右 5.5 cm、向上 3.5 cm，并略微抬柄 |
| 命中 1.04–1.40 s | 拔出后沿弧线恢复 H3 待机 |

坐标为作者相机空间：X 右、Y 前、Z 上。与 V2 蓄满位置相比，V3 向右约 11 cm、向后约 8 cm。接触中心较 V2 向左 5 cm、向下 6.5 cm，空挥带出向左 7 cm、向下 10.5 cm。

命中恢复以动画中的实际斧刃前缘为支点，工具和双手一起运动。支点从现有工具网格的前缘顶点读取，撬柄期间保持在接触姿势的作者空间位置；这是第一人称动画的嵌入表现，没有新增世界物理约束、锁定鼠标或冻结角色移动。停帧只冻结该工具的接触姿态，不暂停世界。

## 镜头与采集接入

- 新增 `FProductionAxeImpactMotion`，读取 `Content/ColdSteelData/axe_impact_motion.json`。作者脚本也读取同一文件，命中恢复长度、撬动角度/时间、拔出起止点共用数据。
- 镜头包含右后蓄势随动、左下压头、确认命中的短促衰减冲击、两次撬动的轻微反作用以及拔出的反向脉冲。强冲击只出现在有效采集提交之后，空挥仅保留动作随动。
- 镜头沿项目现有 `UpdateCamera` 位置/旋转叠加入口加入，受角色 `CameraMotionScale` 控制；专属控制台倍率为 `fps.Tool.AxeCamera`，默认 1，0 关闭这层。
- `AdvanceActionBeforeCamera` 由角色在组合镜头前推进一次。工具组件后置 Tick 读取同一时钟采样手臂，不再重复推进，避免镜头、声音、采集接触与手臂各走一套计时。
- 成功命中时从接触时刻开始命中表现，晚到一帧不直接跳过停帧区间。单次采集、体力扣除和奖励仍各执行原来的一次。
- 新增震动后，斧头的资源射线使用角色的稳定控制视线；纯表现偏移不移动采集判定或改变树木倒下方向。
- `HitRecover` 作者片段仍为 0.44 s，但命中后映射为实际 0.92 s；Swing 仍为作者 0.68 s → 实际 1.10 s，接触仍是作者 0.24 s → 实际 0.48 s。矿镐和铲子的时序不变。
- 菜单、死亡、切换或收起沿原 `CancelUse` 取消动作，工具镜头返回零。运行范围仍为项目既有本地单人采集组件，没有新增 Blueprint/RPC 或联网流程。

## 可编辑文件

- 空间关键点与腕肘参数：`SourceAssets/AxeTwoHandAttack20260919/V3/motion.json`。
- 命中/镜头共同参数：`Content/ColdSteelData/axe_impact_motion.json`。改变动画时序或撬柄参数后，需要重新运行作者脚本并导入；镜头专属幅度在下次游戏初始化读取。
- 作者入口：`SourceAssets/AxeTwoHandAttack20260919/V3/build_attack.py`。
- 可编辑源：同目录 `Axe_TwoHand_Attack_V3_Editable.blend`。
- FBX：同目录 `Export/A_Harvest_Axe_Swing.fbx`、`Export/A_Harvest_Axe_HitRecover.fbx`，300 Hz 烘焙。
- 导入入口：`Tools/Production/import_axe_two_hand_attack.py`，仍写入现有运行路径的 Swing / HitRecover；V2 源与 `V3/Before/` 的旧二进制均保留。
- 原生接入：`ProductionAxeImpactMotion.h/.cpp`、`ProductionToolComponent.h/.cpp`、`ProductionToolMotion.cpp` 与角色 `UpdateCamera` 的工具入口。

本次仅制作、导出、接入与必要构建，没有运行游戏测试、渲染或验收。手腕外观、斧刃卡入感和镜头强度由用户实机确认。

构建期间遇到 `RuneSwordComponent.cpp` 的 `TObjectPtr` 被 `const auto*` 直接接收导致的 C3535；仅将该行改为显式 `const UAnimSequence*` / `.Get()`，不改剑组件的行为。第一次构建记录为 `Saved/BuildEditor/build-20260919-180531.log`，失败不是斧头代码编译错误；后续正式链接需在编辑器关闭后执行。

最终交付状态：用户保存并关闭编辑器后，正式 DLL 编译与链接成功，记录为 `Saved/BuildEditor/build-20260919-181150.log`。此前编辑器内导入在保存 Swing 时返回失败，已在关闭编辑器后的独立 commandlet 中重新完成两条动画的导入与保存；该进程退出码为 0，记录为 `SourceAssets/AxeTwoHandAttack20260919/V3/import.log` 与同目录 `import_receipt.json`。未进行游戏测试或渲染。
# 后续左臂修订

用户随后要求优化挥砍左腕和左臂，当前动画更新为 [V4 左臂联动](axe-left-arm-v4-20260919.md)，保留本页 V3 武器轨迹与冲击时钟。
