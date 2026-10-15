# 战锤冲刺低位拖持与出手衔接

用户明确选择：冲刺时双手握锤柄、向右下方拖持，锤头在右后方退出第一人称镜头；同时衔接冲刺后的攻击。用户强调肩、肘、腕遵循既有技能经验，不得错误扭曲或拉伸。

后续普通攻击已改为 [三连击](steel-warhammer-combo-20261014.md)。本版低位冲刺持握继续使用，冲刺退出后进入首段斜挥；本版独立 SprintAttack 保留为历史源资产。

## 当前交付

- 作者源：`SourceAssets/SteelWarhammer20261014/SprintDragV1/Warhammer_SprintDrag_Editable.blend`。
- 当前裸手视模：`/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1`。
- 新动作：同目录 `A_Warhammer_SprintCarry` 与 `A_Warhammer_SprintAttack`，共用原矿镐骨架；普通 Idle、Equip、Swing、HitRecover 不复制。
- 冲刺准备由双手低位拖持转到右后低位蓄势，再向前下方砸出；避免接回矿镐过顶准备时的前臂大面积遮挡。普通非冲刺下砸保持原动作。
- 源攻击仍为 0.68 s，接触仍为源 0.24 s，运行沿用战锤 1.6 s／0.82 s 的时间映射；伤害、体力、联机权威与命中范围未改。

## 关节与绑定处理

参考 `ue5-fps-arms-animation` 的双手工具、双手近战、手部与整臂优化、原生绑定经验。原先裸手源与作者骨架关节位置相同，但骨轴表示不同；对已经处于作者空间的裸手几何再次应用参考骨轴变换，会造成二次扭转。新视模保留原几何位置和权重，仅按对应作者骨架绑定；保留原生皮肤 UV1-3 和分区顶点色。

双手沿真实锤柄整手换握，右手向柄尾滑移 6 cm；手指保持原抓握形状。肩、上臂、前臂、手腕和辅助骨整链求解，肘在固定骨长的两骨圆上移动，前臂扭转连续展开。换握与肘弯平面共用释放包络，避免肘先转、手掌后转而折腕。臂展不足时只作小幅肩带支撑调整，不缩放骨段。

作者几何记录：拖持左右可达比分别约 0.91／0.54，锤头全部位于相机后方，最近端进深约 -15 cm。新增动作段最大骨段长度误差约 0.0001 mm，为浮点计算量级；这些数据只描述作者骨架，不替代实际游戏动画验收。

## 运行接入

`ProductionToolMotion.cpp` 采样冲刺拖持片段，`ProductionAxeLocomotion.cpp` 保留既有共用步态。攻击入口使用退出冲刺后仍保留的可见 `SprintBlend` 选择专用起手，避免 `ExitSprintForWeapon()` 清掉状态后选不到动作。

工具视模复用 `URuneSwordMeshComponent` 已有的双手抓握约束入场混合，手、锤柄与肩肘用同一交接时钟。原方法默认时长保持不变，战锤使用显式 0.14 s 交接。旧战锤物品实例在档案归一化时刷新模型路径，运行刷新也识别视模引用变化；物品身份、强化、附魔、位置和旋转保留。

## 保存、构建和预览范围

`import_receipt.json` 记录新视模和两条动画实际保存；commandlet 返回 0。Editor／Game 构建均成功，回执为同目录 `build_receipt.json`。

按用户要求制作并查看了冲刺入场、拖持、低位蓄势和出手衔接的第一人称源预览。相机使用项目冲刺水平 FOV 112°、16:9；图片是 Blender 对实际网格与作者动作的渲染，裸手使用作者预览材质，不是 UE 实机画面。交付图为 `sprint_first_person.png`，其余阶段为 `carry_entry_first_person.png`、`attack_entry_first_person.png`、`attack_join_first_person.png`。

没有启动编辑器或游戏，没有执行玩法、联机或性能回归；当前游戏内观感仍由用户体验。原版视模、动作和原始 GLB 保留。
