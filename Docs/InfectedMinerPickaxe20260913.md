# 感染矿工：单手挥镐修正

> 用户已认可本版整体方向。后续放大矿镐、拖镐待机/移动和前倾砸地见 [当前交付](InfectedMinerDragGround20260913.md)；本页保留为该次认可版本的记录。

2026-09-13。上一版把 `A_Mannequin_Axe_Act` 的斧击用于矿镐，被用户指出动作身份错误。本版改用工程现有 EBS 的 `A_Mannequin_PickAxe_Act`，并明确处理原动作的双手握持。

## 动作来源和适配

源目录 `/Game/EasyBuildingSystem/Mannequin/Animations/`，攻击为 `A_Mannequin_PickAxe_Act`，待机为 `A_Mannequin_Pickaxe_Idle`，移动为 `A_Mannequin_Pickaxe_Walk`。源攻击 65/30 秒、30 fps、单次执行。已按用户预览要求查看原模型第 0、12、21、27 帧：从身前举过头顶后方蓄力，随后向前下方挥落，躯干随势前倾并收势回位。

采用 UE 原生 IK Retargeter 的精确骨链映射、目标参考姿态对齐和 FK 重定向。保留矿镐源的身体、腿与持镐左臂轨迹；右侧锁骨、上臂、前臂、手及对应扭转骨改用已认可 `AuthoredChopFinal/A_Miner_Idle` 中已有的局部动画。双手手指固定为该 Idle 第 0 帧的已认可抓握。身体和手部几何、静止骨架、蒙皮权重、PBR 材质、握持位置与矿镐大小均沿用已认可资产。

实际模型预览发现旧镐头在新的挥击轨迹下横向朝着目标，因此只将刚性镐头沿木柄轴转正 90 度，使镐尖在挥落平面内；木柄、手部与动画不随之旋转。以同一骨架导入 `SK_InfectedMiner_Pickaxe`，沿用原材质、顶点色和 Physics Asset，再绑定原矿工蓝图。原 `AuthoredChopFinal` 模型保留。

这是由双手采矿源与已有放松右臂合成的单手动作，不是原生单手动捕；没有重新编排持镐手的攻击 IK 或人体攻击关键姿态。原始 65 个帧间隔均匀重采样为 54 个，输出 1.8 秒，速度约 1.204 倍。速度烘焙进动画数据，因为现有怪物按战斗时钟直接设置动画时间，不依赖 `RateScale`。

## 接入

新 UE 目录 `/Game/Monsters/InfectedMiner/PickaxeSingleHand20260913/`。重定向器 `RTG_EBS_Pickaxe_Miner`，三个新序列 `A_Miner_SingleHand_PickAxe_Act`、`A_Miner_SingleHand_Pickaxe_Idle`、`A_Miner_SingleHand_Pickaxe_Walk` 已保存到原 `BP_InfectedMiner` 的对应引用。

伤害窗口从源动作第 21–27 帧同步换算为约 0.582–0.748 秒。EBS 自带交互 Notify 不迁入矿工；沿用已有的单次伤害时钟、24 点伤害、150cm 范围及受击/死亡中断。村庄继续通过原 `InfectedMiner_Village_01` 生成同一个蓝图，不需另放怪物或改写整张地图。

十字镐仍为当前已认可模型（柄长 0.96m、镐头跨度 0.72m）。先前找到的免费 Fab Basic Pickaxe 尚未下载或替换，不把当前模型称为该 Fab 资产。

## 可编辑交付和预览

本版文件根目录 `SourceAssets/InfectedMiner20260913/PickaxeSingleHand/`：

- `Delivery/InfectedMiner_Editable.blend`：已认可模型及这版三动作。
- `Delivery/SK_InfectedMiner_Pickaxe.fbx`：仅修正刚性镐头方向的骨骼网格。
- `Delivery/A_Miner_Attack.fbx`、`A_Miner_Idle.fbx`、`A_Miner_Walk.fbx`：UE 烘焙动画。
- `Delivery/rebuild.json`：源资产、输出资产、合成方式、速度和接触时序。
- `Reference/Pickaxe_Source_*.png`：按用户要求查看的原始采矿动作姿态。
- `Previews/InfectedMiner_SingleHand_Pickaxe_Attack.gif` 及同名 MP4：这版动作的正面斜视、侧面并排预览；保留真实模型材质，离线 Blender 渲染，不是 UE 游戏录像。

## 制作入口

1. UE Python 运行 `Tools/InfectedMiner/rebuild_pickaxe_tools.py`，可用 `-NullRHI -unattended -nosound`；只导出动画，不导出预览网格。使用引擎现成 `AnimPoseExtensions` 和 `AnimSequencerController` 完成局部骨层与时间重采样，不需要新原生制作接口。
2. Blender 执行 `package_default_tools_blend.py -- --pickaxe`，接回已认可可编辑模型；执行 `orient_pickaxe_head.py`，只旋转镐头顶点、保存可编辑文件并导出骨骼网格。
3. UE Python 执行 `import_pickaxe_head.py`，导入新网格并沿用已认可骨架与材质，不重设参考姿态。
4. 用户已明确要求 GIF，执行 `render_default_preview.py -- --pickaxe`，再以 Python 执行 `package_default_preview.py --pickaxe`。不带 `--pickaxe` 的旧入口仍为历史斧击输出，不用于本版。

必要的 `FPSGAMEEditor` 构建已完成，日志 `Saved/InfectedMiner/build-pickaxe-integration.log`。此前两次构建曾受并行建筑模块的未完成修改影响；保留该任务修改，后续构建在其更新后完成。资产制作通过现成编辑接口完成，不依赖本次新增原生函数。

本轮未执行游戏、战斗或状态切换测试，由用户在村庄自行测试；已打开的编辑器或游戏需重启加载新模块和资源。预览交付不代表动作观感已获认可。商店原始素材和派生二进制保留本机，公开 Git 仅提交制作脚本、相关代码与说明。
