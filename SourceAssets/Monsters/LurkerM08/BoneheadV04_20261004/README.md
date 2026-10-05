# 伏窥者 M-08 / Bonehead V04

本次替换的是动作驱动方式。V03 犬科动作被用户反馈仍然僵硬；保留其已制作的异形骨架、蒙皮和 V02 背部几何，改用接触驱动的爬行及 M08 专用攻击姿势。

## 来源与使用范围

- 参考：[WeaverDev/Bonehead](https://github.com/WeaverDev/Bonehead)，提交 `acc989256fa0fe8bc70dcfd5da29f032b3765fd6`。
- 采用脚掌脱离根节点位移、触发距离、预测落脚、平滑抬落和对角换步思路，重写为 UE C++。
- `Reference` 留存 `LegStepper_Full.cs`、`GeckoController_Full.cs` 和 MIT 许可。许可另存 `Content/ThirdPartyNotices/Bonehead.txt`。
- 未使用 Bonehead 的模型、纹理、场景或动画美术。

## 制作内容

- `M08_Bonehead_Animated_V04.blend`：保留 70 骨拟合骨架和原网格、UV、材质的编辑源。实际骨表见 `authoring.json`。
- `Animations`：11 个 120 fps FBX。Idle / IdleAlert / Walk / Run 为支撑和呼吸姿势；AttackBite / AttackPounce / TraverseJump / HitFront / HitLeft / HitRight / Death 为重新制作的动作。
- Walk / Run 不是独立四足循环。正式角色的原生接触节点根据真实位移控制脚掌，单看 FBX 不会出现完整步行。
- 前掌领先、对侧后腿稍迟换步；支撑脚固定在世界或支撑组件上；步长预测包括平移与转弯。
- 前肢二节 IK，后肢保留膝—跗—足三节结构。肩胛滑移、手指收放及关节辅助骨跟随求解。
- 躯干根据支撑点做有阻尼的位移，头颈参与转弯；背拱左右轨由同一胸部—骨盆变形场驱动。
- 地面、墙面、倒挂使用当前角色表面朝向。跳跃、攻击、受击和死亡由动作接管，停止落脚约束。
- 原有表面寻路、胶囊位移和唯一攻击时钟不变。咬击接触 0.30–0.42 秒；扑击 0.52–0.64 秒；跳跃飞行姿势区间 0.16–0.54 秒。

## 实际接入

原生类 `ULurkerM08AnimInstance` 继承既有四足动作接口；`FLurkerM08ContactNode` 只接到该类的动画图。世界射线在游戏线程按 30 Hz、每批 4 条执行，工作线程仅求解已复制目标。快照在接触修正之后混合，避免重复施加上一帧偏移。

制作脚本：`Tools/LurkerM08/author_bonehead_v04.py`。

导入脚本：`Tools/LurkerM08/install_bonehead_v04.py`。要求常规 Editor 构建完成后再执行；复用 `/Game/Monsters/LurkerM08/CanineV03/SK_LurkerM08_CanineV03` 的骨架，向 `/Game/Monsters/LurkerM08/BoneheadV04/Animations` 保存新动作。正式蓝图和数据集原路径不变，F6 仍使用 `LurkerM08`。

2026-10-04 已完成常规 Editor 构建（`build.log`：Succeeded），随后无界面导入实际保存 11 个动画及正式动作集、怪物蓝图。`installation.json` 状态为 `bonehead_contact_locomotion_saved_and_bound`，动画类绑定为 `/Script/FPSGAME.LurkerM08AnimInstance`；`import_02.log` 记录脚本执行成功、0 errors，进程退出码 0。`Before` 保留替换前蓝图与数据集。

第一次导入在引擎初始化阶段退出、未执行脚本，记录保留于 `import.log`；第二次导入已完成上述保存。没有主动启动交互 UE 或游戏。

本次按用户规则不运行游戏、测试、截图或预览渲染。构建和导入状态单独记录，不代表动作观感或穿插已经验收。

## 2026-10-05 归档说明

本目录中旧 Before、PreviousSource、before_references.json、Blender 上次保存和已替代定位文件（如存在）已移到 `trash/lurker-m08-retired-20261005/`。按工程 `Docs/Publication/LurkerM08_20261005/archive-manifest.json` 查询原路径及恢复目标；历史段落的旧位置不表示备份仍在本目录。仍供当前制作链读取的正式源继续保留。
