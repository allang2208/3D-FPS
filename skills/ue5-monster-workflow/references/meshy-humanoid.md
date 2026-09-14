# Meshy 人形怪物与成熟动作复用

适用：用户提供 Meshy 生成、已有材质与蒙皮绑骨的双足人形，要求复用现有待机、移动、攻击、死亡动作并接入 UE。2026-09-14 用户确认胖子僵尸整条流程成功；这不代表 Meshy 对所有体型或持械动作均可直接套用。本次整理不追加游戏测试。

## 输入与动作选择

- 模型、材质、蒙皮和绑定由用户通过 Meshy 完成；本地工作保留其网格、UV、骨架父链和权重，负责动作适配与 UE 接入。已认可输入直接进入适配，不重新走 5080 生成或无必要重绑。
- 模型来源与动作来源分别记录。胖子的 Meshy ZIP 是用户资产，Mesh2Motion 的 CC0 不覆盖该模型或工程水体素材；Git 发布源码、脚本和必要记录，二进制按工程 AssetSetup 恢复。
- 先看现有动作参考并读取实际片段，选择能表达目标身份的源动作，再制作体型修正。胖子使用 Mesh2Motion 的 `Zombie_Idle`、`Zombie_Walk`、`Zombie_Scratch`、`Death_D`，固定提交 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`。来源与散列在 `SourceAssets/FatZombieMeshy20260913/source_manifest.json`；许可副本在 `sources/LICENSE-CC0.MD`。
- 无手指骨就明确没有独立手指动画；本例无武器抓握，不升级为持械人形通用成功案例。持械动作继续参考 `humanoid-weapon-motion.md`。

## 重定向与体型修正

1. 保留原始模型场景、干净源动作、原生重定向输出和体型修正成品四层。胖子入口是 `prepare_blender.py` → `import_and_retarget.py` → `fit_body_animation.py` → `export_final_with_skin.py` → `import_final.py`，均在上述 SourceAssets 目录；UE 制作宿主为 `UEAuthoring/FatZombieAuthoring.uproject`。
2. 用 UE IK Rig / IK Retargeter 映射骨链与参考姿态，不按骨名数字猜解剖顺序。胖子实际脊柱为 `Hips → Spine02 → Spine01 → Spine → neck → Head`；34 根原骨之外，FBX/UE 使用容器根 `FatZombieRoot`。
3. 明确骨骼局部、组件、世界空间及单位。UE 导出 FBX 的参考骨架缩放与动画键的单位换算不一定表现相同。本例动画世界坐标已是米，再按参考尺寸比乘 100 曾造成瞬移；只锁 `FatZombieRoot` 无法阻止子骨 `Hips` 跑远。修正版直接使用已换算的位置，保留死亡需要的骨盆后倒位移。
4. 在原蒙皮上修正腹部避让、手臂可达性、站距及接地，保留源动作左右差异。胖子使用双段肢体求解和蒙皮最低点校正；腹部半径、站距与骨名是本例数据，新体型重新取值。
5. Idle/Walk 修正后明确处理循环末键；Death 保持单次后倒及末姿态。胖子以 120 FPS 烘焙，成品 Idle 1.6 s、Walk 1.6667 s、Attack 2.0833 s、Death 2.5667 s（含 0.4 s 保持）。这些时长属于案例，后续角色保留各自合同。
6. 分动作 FBX 带原网格与蒙皮输出，UE 仅提取动画到同一个目标 Skeleton。PBR 保留四张原贴图；该 Meshy 输入的 OpenGL 法线在 UE 翻转绿通道，颜色用 sRGB，法线与遮罩用对应线性采样。

## 游戏接入

- 动画姿态与世界移动分别归属：原地动画由 CharacterMovement 移动，行走播放速度跟随实际速度；不能因为能播放攻击就判定导航正常。胖子在主场景没有 NavMesh 时只会原地攻击，后续为开发区域补建适合胶囊尺寸的导航，并使生成落点同时满足物理放置和导航覆盖。
- 状态切换从当前可见姿态混合，保留循环相位；受击时不要用 `PlayAnimation` 把专用 AnimInstance 切回单节点。`UFatZombieAnimInstance` 用姿态快照与 Sequence Evaluator，默认混合约 0.2 s；攻击仍由唯一战斗时钟驱动，命中窗口 1.00–1.18 s。
- 生命只由怪物原有伤害入口维护，受击硬直不另建一份生命。HUD 通过 `UMonsterCombatComponent::GetVitals` 读取真实生命；命中显示与是否持枪分离。胖子 600 生命、25 攻击、65 cm/s 移速是此项目配置，不是新角色固定模板。
- 骨骼网格没有 Physics Asset 时，视觉模型不会自动参与武器射线。胖子先按原蒙皮拟合命中胶囊；近战简单查询有效、枪械复杂查询漏检时，在其物理形体设置 `CTF_UseSimpleAsComplex`，保留头骨命中和世界遮挡，不改变全世界枪械射线的复杂查询规则。最终物理制作入口为 `Tools/FatZombie/install_combat_physics.py` 与 `FatZombiePhysics.cpp`。
- 完整死亡动画后再接布娃娃：交接时间取死亡片段时长与最小延迟的较大值；交接时采样精确末帧、刷新骨骼后再模拟。已倒地尸体不额外踢飞。胖子保留 18 个拟合形体，加不碰撞的物理根和 18 个约束；存活跟随动画，死亡才统一模拟，尸体默认从生命归零起 15 s 回收。

## 地面残留物

死亡脓液在生命归零时独立生成，锁定死亡脚下位置，布娃娃移动不拖动液洼。当前默认：1.6 s 由小片向外扩散；每 0.5 s 一次、每次 8 点原始魔法伤害；第 20 s 末跳后进入 1 s 淡出。尸体 15 s 回收不影响脓液。模型和状态机只触发一次生成，Actor 销毁时清理自己的定时器。

形状随机种子每次生成取一次，地面采样拒绝墙面、陡坡和跨层落差。主体与外围液滴共用实际地面三角形；顶点保存到达进度，材质扩散与脚下伤害裁剪使用同一进度，避免液体尚未出现就掉血。保留阵营筛选、落地要求和每目标每跳去重。

材质复用项目已有水体法线、泡沫及浑水遮罩，独立调为黄绿湿润薄膜；不改原河流水体。`Tools/FatZombie/build_pus_material.py` 是当前生成器，Masked PBR、覆盖边缘与干燥淡出由 Actor 控制。

看不到薄膜但能掉血时，先区分材质、网格位置与地面绘制遮挡。此场景的引擎 Cube 被缩放成 5 km 地板，绘制深度与碰撞面偏离约 5 cm；最终改为尺寸写入网格、分段构建、单位缩放的地面，保持原 Actor 和碰撞。不要把抬高脓液、强发光或关闭深度当成此次成功方案，也不要将该场景原因断言为所有地面问题。

## 交付与恢复

- 正式运行资产：`Content/Monsters/FatZombieMeshy`，另有 `Content/GameMaps/Geometry/SM_MainGround_Subdivided` 与主地图；作者源、源动作、prepared、native_retarget 和 UEAuthoring 继续保留，属于重建输入。
- 当前成功流程以 `Docs/fat-zombie-workflow-publication-20260914.md` 和 SourceAssets README 为入口。原修复报告保留历史时序，后续确认与数值更新独立注明。
- 错误的 100 倍动画、已替代物理/材质/地图副本和旧 WorkProject 进入 `trash/fat-zombie-workflow-20260914`；恢复路径、大小与 SHA-256 见 `Docs/AssetArchives/fat-zombie-20260914.json`。不能用归档整张地图覆盖并行场景更新。
- 默认按用户规则由用户测试；构建记录、用户确认和新任务的实际测试分开表述。后续复用本例不自动触发游戏、截图或渲染验收。
