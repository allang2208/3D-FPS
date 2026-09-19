# 突变体-3 / The Forsaken Brute

**最新修订（2026-09-15）：** 按用户指定改用旧 Godot 奔跑僵尸的 Denys Almaral `running_58f`（实际播放别名 `Walk`），经 UE 原生 IK 重定向后已替换正式 Running / RunFast。Running 1.875 s、RunFast 1.25 s，游戏追击速度仍为 360 cm/s；Stagger 保留 revision2 的 Hit_Chest。源文件、制作和导入记录见 [godot_runner/README.md](godot_runner/README.md)，当前参数以 animation_contract.json 及 godot_runner/installed.json 为准。未进行游戏测试。revision2 的 Jog 适配已被用户否定并被此次替换；Hyper Chase 商业候选与 Quaternius 免费候选未接入。以下首次接入记录保留历史说明。

用户提供的 Meshy 双足模型接入 `D:/FPS3D/FPSGAME`。运行类为 `AMutant3`，内容目录为 `/Game/Monsters/Mutant3Meshy`。游戏内 F6 开发面板的怪物列表新增「突变体-3」，沿用现有导航落点与生成逻辑。

本次完成模型、材质、移动、快速抓击、受击、弹反、死亡、布娃娃、生命显示、经验奖励与开发面板入口。原项目的五连击、飞扑尚未迁移；Rage 是保留的动作素材，没有配置额外嚎叫伤害。

## 模型与动作

- 原始输入：`D:/FPS3D/资产/Meshy_AI_The_Forsaken_Brute_biped.zip`。保留 Mesh0 网格、UV、34 根原骨与蒙皮；角色网格 9,354 顶点、18,679 三角形，参考高度约 170 cm。排除 FBX 附带的 Icosphere 骨骼显示辅助物，FBX/UE 容器根命名为 Mutant3Root。
- 原四张 BaseColor / Normal / Roughness / Metallic 贴图。UE 法线翻转绿通道，颜色采用 sRGB，法线与遮罩按线性数据导入。Meshy 模型的授权来源与 CC0 动作分开记录。
- 三段移动保留用户文件的步态、左右差异与上下起伏；仅去除周期净水平漂移，并处理末尾 80 ms 的循环衔接。不会把腾空跑步逐帧压到地面。
- 待机参考 Mesh2Motion `Zombie_Idle_Crouch`：深屈膝、前倾、双手低垂，保留小幅身体晃动。抓击参考 `Zombie_Scratch`：右手抬起蓄力、前下方抓击、躯干随动后回收，时长由约 1.8 s 收紧到 1.15 s。
- `Hit_Knockback` 改为 0.9 s 受击片段：0.1 s 快速反应、保持到 0.6 s，再用 0.3 s 收势，与现有反应时钟对应。`Death_D` 保留后倒动作。
- 模型没有独立手指骨，此次没有增加手指开合动画。

| 片段 | 时长 | 用途 |
| --- | ---: | --- |
| Idle | 2.9333 s | 待机循环 |
| Walking | 0.95 s | 低速移动 |
| Running | 0.6167 s | 中速跑步 |
| RunFast | 0.45 s | 全速追击，保留原独特步态 |
| Attack | 1.15 s | 单次快速抓击；命中窗口 0.40–0.51 s |
| Stagger | 0.9 s | 普通受击及弹反后硬直 |
| Death | 2.1667 s | 60%（约 1.30 s）转布娃娃 |
| Rage | 3.6667 s | 备用嚎叫动作，未接入战斗状态 |

所有成品以 120 FPS 烘焙。状态转换使用当前姿态快照混合；攻击仍由现有战斗时钟控制。弹反当帧取消伤害并击退，从打断位置倒放攻击 0.3 s，再以 0.08 s 混合到 Stagger。尸体自死亡起 15 s 回收。

当前开发默认值：750 生命、40 原始抓击伤害、360 cm/s 追击速度、攻击距离基数 130 cm（现有全局 1.5 倍后为 195 cm）、0.65 s 攻击冷却、482 经验。六属性采用原项目突变体-3：力 50、敏 30、智 5、体 40、感 10、运 6。上述模型适配数值可在派生蓝图中调整。

物理使用原蒙皮拟合的 18 个骨骼形体，加一个不碰撞的根与 18 个约束，总质量 100 kg；简单近战扫掠和复杂枪械 Visibility 射线共用骨骼形体，保留头部命中。死亡交接先采样 60% 姿态再启动模拟。

## 可编辑源与重建顺序

1. `prepare.py`：读取 Meshy 原包与两份源 GLB，导出原网格和原动作。`Meshy_*_Source.blend` 保存用户原移动。
2. `import_and_retarget.py`：在 `UEAuthoring/Mutant3Authoring.uproject` 中导入 PBR、创建原生 IK Rig / Retargeter、烘焙并导出重定向 FBX，输出物理参考坐标。`native_retarget/` 保存原生输出。
3. `author_animation.py`：在原蒙皮上烘焙成品，输出 `Mutant3_Meshy_Animated.blend`、`final/*.fbx`、`animation_contract.json`。
4. `fit_damage_collision.py`：依据 UE 参考坐标与原蒙皮制作骨骼局部胶囊。
5. `import_final.py`：在独立 UE 制作工程中导入八段成品到同一 Skeleton。
6. `deliver_to_project.py`：首次复制本怪物专用目录到 FPSGAME；已存在时停止，避免覆盖后续手工编辑。
7. 正式模块用项目 `Tools/Build/Build-Editor.ps1` 编译；在 FPSGAME 制作命令中运行 `install_combat_physics.py`，安装形体、约束和查询设置。

源动作仓库：https://github.com/Mesh2Motion/mesh2motion-assets

本地动作来自官方应用仓库固定提交 `2d3d1ff03247d9e7e830d1ae375653da4e2146e2` 的 `human-base-animations.glb` 和 `human-addon-animations.glb`。动作许可为 CC0-1.0，副本与来源记录见 `sources/LICENSE-CC0.MD`、`source_manifest.json`。源视频画面仅用于读取动作姿态与节奏，位于 `sources/reference_videos`。

模块构建记录：`Saved/BuildEditor/build-20260915-104707.log`。资产制作与导入记录：`retarget-authoring.log`、`animation-authoring.log`、`final-import.log`、`physics-install.log`。未启动游戏，未进行运行或视觉验收，由用户测试。
