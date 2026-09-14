# Meshy 胖子僵尸：已认可的人形动作接入流程

使用你提供的 Meshy 模型和原有蒙皮，将 Mesh2Motion 的免费动作通过 UE 5.8 原生 IK Retargeter 转到目标骨架，再在原模型上制作体型调整版本。

2026-09-14 用户确认：Meshy 生成模型并完成材质、蒙皮绑骨，随后接入成熟动作与游戏的流程成功。以下保留作者链和历史修复依据；最新游戏接入、归档与发布范围见 [整理记录](../../Docs/fat-zombie-workflow-publication-20260914.md)。此次整理没有重新运行游戏测试。

## 2026-09-14 瞬移修复

上一版 `fit_body_animation.py` 依据 UE 导出 FBX 的参考骨架尺寸再次缩放骨盆位置；该文件的动画键已经完成单位转换，导致位置被额外放大 100 倍。锁住 `FatZombieRoot` 不能消除子骨 `Hips` 的错误位移。现已移除重复缩放，重建本目录的 Blender 源文件、四段 FBX 和游戏中同路径的动画资源，并使 Idle/Walk 末帧与首帧姿态一致。

游戏角色改用 `UFatZombieAnimInstance`，从当前可见姿态以约 0.2 秒过渡到下一个动作，保留循环播放进度；攻击仍由原近战时钟定位。排查记录见 [瞬移修复](../../Docs/fat-zombie-continuity-fix-20260914.md)。错误动画、Blender 文件和制作脚本现已归档到工程 `trash/fat-zombie-workflow-20260914/SourceAssets/FatZombieMeshy20260913/repair_20260914/before`，未覆盖用户模型原件。

## 使用位置

- UE 角色：`/Game/Monsters/FatZombieMeshy/SK_FatZombie_Meshy`
- UE 成品动作：`/Game/Monsters/FatZombieMeshy/Animations`
- 可编辑模型与四个动作：`FatZombie_Meshy_Animated.blend`，四张 PBR 图片已打包进文件。
- 分动作 FBX：`final/A_FatZombie_Idle.fbx`、`A_FatZombie_Walk.fbx`、`A_FatZombie_Attack.fbx`、`A_FatZombie_Death.fbx`，带原网格与蒙皮，UE 中仅提取动画到已有目标 Skeleton。
- UE 重定向配置：`/Game/Monsters/FatZombieMeshy/Rig` 中的两个 IK Rig 和 `RTG_M2M_FatZombie`。
- 未经体型调整的重定向结果：UE 的 `RetargetedRaw` 文件夹及本目录的 `native_retarget`。

| 成品动作 | 免费源动作 | 时长 | 默认循环 |
|---|---|---:|---|
| A_FatZombie_Idle | Zombie_Idle | 1.600 秒 | 是 |
| A_FatZombie_Walk | Zombie_Walk | 1.667 秒 | 是 |
| A_FatZombie_Attack | Zombie_Scratch | 2.083 秒 | 否 |
| A_FatZombie_Death | Death_D | 2.567 秒，含 0.4 秒倒地保持 | 否 |

四个成品动作使用同一个目标 Skeleton，已由 `AFatZombie` 与 `UFatZombieAnimInstance` 接入待机、移动、攻击和死亡状态。待机和移动循环，攻击和死亡单次播放。采用原地动画，移动距离由角色移动组件控制；倒地保留骨盆相对根节点的后倒位移。F6 开发面板可在玩家前方生成，真实扣血、受击反馈、死亡动画转布娃娃及地面脓液已接入本机游戏。

## 制作内容

- 保留用户原模型、34 根骨骼的名字与父子关系、蒙皮权重、UV 和 PBR 材质；FBX/UE 使用 `FatZombieRoot` 作为额外容器根节点。
- 对应目标骨架特殊的脊柱顺序：`Hips → Spine02 → Spine01 → Spine → neck → Head`。
- 先用原生 IK Rig / IK Retargeter 对齐参考姿势与骨骼链，再把动作转回原始蒙皮上制作，最终烘焙为 120 FPS 动画。
- 依据原模型躯干范围为手腕加入腹部避让，用双段骨骼求解调整手臂，站姿每侧外展约 3 厘米；保留源动作的左右差异。
- 待机和拖步节奏适度放慢，抓挠攻击保留起势、挥击和收势；死亡保留源动作后倒过程并延长末尾保持。
- 依据实际蒙皮最低点写入骨盆高度修正，包含倒地后的背部接地；用户后续已确认流程成功，本次未重新验收。
- 原有骨架没有独立手指骨骼，因此没有新增手指抓握动画。

源动作预览来自官方仓库，已作为动作参考阅读，保存在 `sources/reference_videos`。关键动作依据为：弓背站立与躯干起伏、交替拖步、抓挠前的抬臂与挥击、屈膝失衡后向后倒地。实际攻击命中由原战斗时钟在 1.00–1.18 秒结算；完整死亡片段结束后同步末姿态再转布娃娃。

## 来源与许可

- 用户模型原件：`D:\FPS3D\资产\Meshy_AI_Mutant_Zombie_Charact_biped.zip`，保留原件不覆盖。解包副本在 `sources/meshy`。用户模型遵循其自身来源与 Meshy 许可，不属于下述 CC0 动画许可。
- 动画：[Mesh2Motion 官方仓库](https://github.com/Mesh2Motion/mesh2motion-app)，固定提交 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2`。
- 使用文件：[human-base-animations.glb](https://github.com/Mesh2Motion/mesh2motion-app/blob/2d3d1ff03247d9e7e830d1ae375653da4e2146e2/static/animations/human-base-animations.glb)。下载的扩展库也保留在 `sources/human-addon-animations.glb`，本轮未从扩展库选取动作。
- Mesh2Motion 模型、骨架和动画采用 CC0；许可副本在 `sources/LICENSE-CC0.MD`。应用程序本身的 MIT 许可与动画资源许可分开记录。
- 下载地址、固定版本和 SHA256 记录在 `source_manifest.json`。

## 可编辑文件与制作脚本

- `FatZombie_Meshy_Source.blend`：用户模型原始导入场景。
- `M2M_SelectedSources.blend`：官方源动作参考场景。
- `FatZombie_Meshy_Animated.blend`：原模型加体型调整后的四个动作。
- `prepare_blender.py`：准备目标网格和源动作 FBX。
- `import_and_retarget.py`：导入 PBR、目标和源骨架，创建原生 IK 资产，导出重定向动作。
- `fit_body_animation.py`：在原蒙皮上制作体型调整并输出 FBX / Blender 文件。
- `export_final_with_skin.py`：从成品 Blender 文件输出带蒙皮的分动作 FBX。
- `import_final.py`：将成品动画导入同一个目标 Skeleton。
- `animation_contract.json`：源动作、最终时长、循环和制作参数。
- `ue_delivery.json`：UE 资产路径与导入记录。
- `deliver_to_project.py`：将完成的资产目录复制到 FPSGAME Content，不覆盖同名已有目录。

实际导入使用独立的 `UEAuthoring/FatZombieAuthoring.uproject`，避免 FPS 项目并行热重载模块对资产制作的干扰，产物按原路径复制到 FPSGAME 的 Content。旧 `WorkProject` 已归档到工程 `trash/fat-zombie-workflow-20260914/SourceAssets/FatZombieMeshy20260913/WorkProject`，交付以 FPSGAME Content 和当前 UEAuthoring 为准。

## 当前死亡与脓液设置

尸体从生命归零起默认保留 15 秒。脓液同时在脚下独立生成，1.6 秒逐渐扩散，每 0.5 秒造成一次 8 点原始魔法伤害，持续至第 20 秒后开始 1 秒淡出。尸体销毁不提前移除脓液。当前材质制作、物理配置和主地面修复工具见 `Tools/FatZombie`；源码、素材和构建记录的发布范围见整理记录。
