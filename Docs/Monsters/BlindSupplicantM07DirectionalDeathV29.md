# M-07 V29：按来袭反方向倒地

2026-10-03 用户要求把死亡改为受打击反方向后仰倒地。原 V15 为固定侧前方倒伏，最后一击的方向没有参与死亡动作选择。

## 本次制作

- 新建八段 `AnimationsDirectionalDeathV29/A_M07_DeathAway000…315`，均为 2.8 秒、60 fps。从当前 V20 自然待机开始，骨盆失衡带动整身倾倒，胸颈分担短促反应，双脚错时失去支撑，完整肩臂链滞后松落。正面受击对应后仰，侧后方受击选择向远离来袭方倒下的动作。
- 角色保持原朝向，不在死亡时强制转向攻击者。一次性比较八段动画在交接点的实际骨盆水平位移与伤害传播方向，选最近方向；八方向最大量化偏差为 22.5°。从导入后轨道计算方向，避免 FBX 坐标手性、网格朝向补偿造成左右颠倒。
- 点伤害使用 `ShotDirection`，爆炸使用爆心到怪物的方向，其余伤害使用来源位置；零方向再尝试施加者位置，无有效水平来向时默认向自身后方倒地。
- 1.68 秒（60%）从当前精确姿态交给原共享布娃娃，沿用选中动画的骨盆速度。预算不足时继续播放同一段动画至倒地结束。已经受击倒地或进入物理的怪物继续原状态，不重新站起播放死亡。
- 只烘焙动画和修改死亡方向选择，没有新增 Tick、运行时 IK、独立布娃娃或物理预算。显示网格、骨架、骨长、蒙皮、近战、移动、V28 施法及距离配置保持现有引用。

离线支撑使用原显示身体的蒙皮厚度，脚失去支撑后允许骨盆下降；不把站立双脚锁定套用到整段倒地。背膜布料不参与这个支撑计算。此项属于动画制作，不作为实际地形碰撞或观感通过的证据。

## 交付

- 可编辑源：`SourceAssets/BlindSupplicantM07Meshy20261001/DirectionalDeathV29/Motion/M07_DirectionalDeath_V29.blend`，同目录八份动画 FBX 和 `directional_death_manifest_v29.json`。
- 原生：`BlindSupplicantMonster.h/.cpp`、`BlindSupplicantDeathPresentation.cpp`。只新增死亡数组引用与选择逻辑，复用现有死亡交接。
- 导出：`Tools/BlindSupplicantM07/author_directional_death_v29.py`。
- 导入：`Tools/BlindSupplicantM07/import_directional_death_v29.py`。
- 已保存资产：八段死亡动画和原 `BP_BlindSupplicantM07`；回执 `DirectionalDeathV29/ue_directional_death_delivery_v29.json`。
- Editor 必要构建完成：`Saved/BuildEditor/m07-FPSGAMEEditor-20261003-175015.log`。
- 独立 Game 构建受范围外现有编译错误阻断：`FPSPlayerBodyMotion.cpp:177` 引用 `UFPSPlayerBodyAnimInstance` 中不存在的 `bCoupledActionWrists`；日志 `Saved/BuildEditor/m07-FPSGAME-20261003-175836.log`。按并行工作规则保留该模块，不把 Editor 成功记作 Game 已更新。
- 后台导入保存日志：`Saved/Logs/M07Import-20261003-175445.log`。

没有打开交互编辑器、启动游戏、运行测试、截图或渲染。动作观感和实际地形接触由用户自行测试；资产保存、构建完成不表示已获视觉认可。
