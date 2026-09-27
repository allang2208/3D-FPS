# 左手取药水、饮用与抛瓶 · 2026-09-26

本页保留首次动作制作记录。当前四品阶正式瓶型见 [分品阶药水瓶](potion-tier-bottles-20260926.md)，最新恢复量和旧存档迁移见 [恢复数值调整](potion-recovery-balance-20260927.md)。旧瓶动作 Blend 是编辑参考，最后两次握点下移以运行 JSON 为准。

使用现有 `Consumables5080_20260910` 红／蓝药水模型，接入背包使用和快捷栏使用；普通、中、高、特级药水按 HP／MP 家族复用瓶型。没有修改恢复数值、物品冷却或存档格式。

地面拾取补接：`ColdSteelPickupConsumable.cpp` 按 `hp_potion`／`hp_potion_*` 和 `mp_potion`／`mp_potion_*` 选择对应瓶型。中、高、特级的六种药水现在使用已有红／蓝瓶网格，并按 18 cm／18.5 cm 高度设置显示和碰撞盒；仅归一化网格路径，物品实例的定义、数量、等级、稀有度和存档身份保留原值。未执行游戏测试。

## 动作

- 0–0.26 s：左手离开当前握点，到画面下方抓瓶。
- 0.26–0.78 s：举瓶，四指保持弯曲包握，拇指挑开瓶塞；蓝瓶带走封住瓶口的银色塞圈，瓶颈装饰保留。
- 1.08–1.52 s：举至嘴边并倾瓶，液体逐渐减少；1.46 s 在原库存存档事务中扣一瓶并应用恢复效果。
- 1.52–1.76 s：喝完后放低、向左前方加速抛出，1.76 s 脱手，1.80 s 完成手臂随挥；五指在 0.08 s 窗口内张开。空瓶相机空间初速度为 `(540,-360,190)` cm/s，叠加角色速度，受重力／环境碰撞影响，7 s 后回收。
- 1.80–2.10 s：五次平滑曲线交回当前装备的实时握姿，recover 时长 0.30 s。

手型参考 AKM 大弹鼓 `PalmGripV3` 的四指并拢、各关节连续屈曲与拇指对握，结合 AKM 弹匣抓握的拇指舒展方式。红、蓝瓶按各自瓶颈／肩部尺寸单独配置。运行时按本枪原生参考姿态重建掌向、固定骨长解肩肘腕、辅助骨跟随完整骨段，沿用当前 V7 手模和装备外观。

第二轮按用户反馈将红瓶掌心握持位置沿瓶轴下移 2.0 cm、蓝瓶下移 2.2 cm；掌心外移并放松各指屈曲，适配更宽的瓶身。采用 `grip_in_palm.Y` 调整手相对瓶的高度，保留瓶轨迹及饮用时的瓶口位置，`grip_height` 仍表示原轨迹锚点。喝完至脱手由 0.40 s 缩为 0.24 s，抛瓶速度由约 4.54 m/s 提升至约 6.76 m/s，recover 由 0.50 s 缩至 0.30 s；总时长由 2.50 s 缩至 2.10 s。饮用和效果结算时点保持一致。

## 使用与打断

药水动作占用左手。取药前检查当前动作、资源和物品；动作期间拒绝重复取药，并阻挡换弹、瞄准、近战出招与新左手动作。枪械仍遵循已有左手动作期间的右手腰射规则。双持左手持枪时沿用已有的左手占用限制。

背包内使用药水会收起背包再播放；其他阻挡操作的面板不启动动作。空手／收弓时使用 V7 备用左臂，枪械、近战和工具使用自身的原生手模。换武器、快速近战、翻越、菜单、死亡／输入锁定可打断；喝下前不扣除，喝下后已提交的恢复和消耗保留。结算时重新读取物品与资源，仍通过原有 A/B 存档事务写入。

## 文件与制作

- 动作参数：`Content/ColdSteelData/potion_use_motion.json`。
- 运行时：`Source/FPSGAME/Items/FPSPotionUseComponent.*`、`PotionArmPose.*`、`PotionUseMotion.*`。
- 入口：`ColdSteelProfileRuntime.cpp`；左臂后置层：`FPSCastingMeshComponent.cpp`；角色动作占用／中断：`FPSGAMECharacter.cpp`、`FPSGAMECharacterActionPriority.cpp`。
- 可编辑源：`SourceAssets/PotionUse20260926/AKM_V7_hp_potion_DrinkThrow.blend`、`AKM_V7_mp_potion_DrinkThrow.blend`，120 Hz、完整 2.1 s。作者场景的抛物线用于编辑轨迹，游戏落地采用实际物理。
- 模型派生与 FBX：同目录 `*_DrinkParts.blend`、`Export/`，运行资产写入 `/Game/Items/Consumables/PotionUse/`；复用原瓶材质，不覆盖地面拾取模型。
- `prepare_bottles.py` 拆分瓶身／液体／瓶塞并输出 UCX 简单碰撞；`author_left_hand.py` 从 V7 AKM 源烘焙可编辑动作；`import_bottles.py` 在无界面 commandlet 中导入并保存六个静态网格。运行时按 JSON 求解各武器原生左臂，不将 AKM 的骨骼旋转直接套到其他骨架。

未启动游戏、PIE、预览、渲染或测试；视觉和手感由用户测试。导入回执与构建日志只记录制作和落盘结果。

本次六个动作网格已导入并保存，记录为 `SourceAssets/PotionUse20260926/import_receipt.json`。后台 Editor 构建完成；最终构建记录 `Saved/BuildEditor/build-20260926-195805.log`（Succeeded，目标已更新）。未打开交互编辑器。

第二轮调参已落盘并重新烘焙两套动作源，记录 `SourceAssets/PotionUse20260926/author-hand-lower-grip.log`。本轮源码由现有串行构建 `Saved/BuildEditor/build-20260926-201744.log` 编入 DLL：包含 `FPSPotionUseComponent.cpp`、`PotionUseMotion.cpp`、`PotionArmPose.cpp`，结果 Succeeded，DLL 于 20:18:14 更新。没有重复发起构建、重导无变化的静态网格或启动游戏测试。
