# 胖子僵尸无法被攻击、无受击反馈修复 · 2026-09-14

用户确认导航修复有效后，反馈玩家攻击胖子僵尸没有受击反馈。本轮修复命中资产和受击表现接入，未启动游戏或进行实战复测。

## 原因

胖子沿用护士的碰撞规则：移动胶囊忽略 `Visibility`，由骨骼网格承担精确命中。实际 `SK_FatZombie_Meshy` 的 `physicsAsset=None`，且未开启逐三角形碰撞。枪械、飞行子弹及符文剑均使用 `Visibility` 查询，因此可见身体没有对应命中形状。

第二个缺口是胖子没有专用受击片段；共用战斗组件暂停动画，而胖子专用动画实例也在硬直期间保持原姿态，缺少可见的受击反应。

## 修改

- 新增并绑定 `SK_FatZombie_Meshy_PhysicsAsset`，按原模型蒙皮与 UE 参考骨骼空间拟合 18 个命中胶囊，覆盖躯干、头、颈及四肢。独立 `Head` 形体保留现有要害判定。形体使用 Kinematic 跟随动画，角色网格继续使用 QueryOnly。
- 物理拟合读取原 `FatZombie_Meshy_Source.blend`，使用对应关节换算 FBX 坐标轴及单位，再转换到各骨骼局部空间；未更改原网格、蒙皮、贴图或四段动画。
- 胖子新增沿命中方向的上身旋转反应，在 `Spine02` / `Spine` 分配约 18 度后仰。前 0.1 秒起势，最后 0.45 秒回落；较长眩晕保持受击姿态，连续命中从当前偏移继续，位移不累积。
- 共用战斗组件通过护士的虚函数调用角色受击表现。护士保留原片段播放逻辑，胖子使用自身动画图的叠加旋转；不把专用混合动画实例切成单节点播放。
- 受击表现使用原战斗组件的硬直时间。原有扣血、攻击打断、记忆攻击者、眩晕、死亡和一次性击杀奖励继续由既有入口负责；切入恢复或死亡时捕获当前姿态并清除额外旋转，防止重复叠加。
- 真实命中返回有效伤害后，沿用已有玩家准星命中提示。没有修改武器伤害、射速、移动导航或攻击命中窗口。

## 文件与重建

- 原生实现：`FatZombie.h/.cpp`、`FatZombieAnimInstance.h/.cpp`、`NurseZombie.h/.cpp`、`MonsterCombatComponent.cpp`。
- 资源：`Content/Monsters/FatZombieMeshy/SK_FatZombie_Meshy.uasset` 及同目录新增的物理资产。
- 制作步骤：UE 执行 `Tools/FatZombie/prepare_damage_collision.py` 导出参考骨架；Blender 后台执行 `fit_damage_collision.py` 拟合原蒙皮；UE 执行 `install_damage_collision.py` 创建并保存命中资产。
- 中间数据：`SourceAssets/FatZombieMeshy20260913/damage_collision_rig.json`、`damage_collision_shapes.json`。最后在现有 `UEAuthoring/FatZombieAuthoring.uproject` 保存，再将网格和物理资产交付回主工程。
- 修改前网格保存在 `Saved/FatZombieDamage/before`。本次物理资产用于伤害查询，死亡继续播放既有死亡动画。

## 构建与交付范围

`FPSGAMEEditor Win64 Development` 和 `FPSGAME Win64 Development` 均已构建成功；日志分别为 `Saved/Logs/FatZombie-damage-Editor-build-retry.log`、`FatZombie-damage-Game-build.log`。资源保存日志为 `FatZombie-damage-install-final.log`。

未运行游戏、射击测试、视觉预览或其它怪物回归。若编辑器仍打开，请重启后进入 `DayNight_Lighting`，F6 清除旧实例并重新生成胖子僵尸，由用户测试枪击、头部命中、受击恢复和击杀表现。
