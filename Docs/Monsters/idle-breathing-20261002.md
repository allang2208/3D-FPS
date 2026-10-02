# 怪物待机呼吸与微动（2026-10-02）

## 制作范围

给当前接入的 13 个怪物生成条目加入按体型区分的待机呼吸，明确排除盲祷者 M-07。
重建版巫婆虽然 F6 名称仍带“候选”，是当前保留且整体模型已获用户接受的巫婆版本，因此纳入。
没有给退役普通巫婆或纯动画模板另做资源。

| 怪物 | 基础呼吸周期 | 主要部位与增量 |
| --- | --- | --- |
| 胖子僵尸 | 4.5 秒 | 上胸缓慢起伏，深度扩张最多约 1.3%，颈部弱延迟 |
| 突变体-3 | 2.9 秒 | 较紧张的胸背节奏，约 0.9% 扩张 |
| 护士僵尸 | 3.8 秒 | 小幅胸腔起伏，约 0.8% 扩张 |
| 毒液僵尸 | 3.4 秒 | 胸背起伏，约 1.0% 扩张 |
| 巫婆·重建版 | 4.1 秒 | Quinn 上胸，约 0.6% 扩张；道具手臂保留源姿态 |
| 异变巨手 | 4.2 秒 | 原有待机上增加弱掌面、指根微动，约 0.3% 掌面扩张 |
| 小皮肤手 | 2.8 秒 | 同骨架，降低旋转与扩张，约 0.2% |
| 手脑 | 4.8 秒 | 颈部与颅体缓慢错相起伏，约 0.6% / 0.3% |
| 毒蛆 | 3.3 秒 | body_03 / body_05 / body_07 依次错相，约 0.8–1.0% |
| 野狼 | 3.2 秒 | 保留 IdleBreathe，叠加弱胸背与颈部微动，约 0.4% |
| 僵尸犬 | 3.2 秒 | 同狼骨架和原有待机，采用弱增量 |
| 感染犬 | 2.9 秒 | 沿自身骨架映射，胸背与颈部弱增量 |
| 百目炉渣 | 5.2 秒 | 胸腔与背甲的慢节奏，约 0.8% 胸腔扩张 |

每只实例根据名字派生稳定的相位、噪声起点和 ±6% 周期差，不让一群怪物同步呼吸。
表中是制作参数，未通过本轮画面或游戏测试判断观感。

## GitHub 方法参考

- [AiGameKit Animator3D breathe-idle](https://github.com/maikramer/AiGameKit/blob/main/Animator3D/src/animator3d/bpy_ops.py)：按骨链区分呼吸、颈部与附肢微动。
  [连续噪声实现](https://github.com/maikramer/AiGameKit/blob/main/Animator3D/src/animator3d/_motion.py)，[MIT 许可](https://github.com/maikramer/AiGameKit/blob/main/Animator3D/LICENSE)。
- [Dust3D 四足 idle](https://github.com/huxingyi/dust3d/blob/master/dust3d/animation/quadruped/idle.cc)：主呼吸叠加弱次节律，头颈/脊柱错相，并保留足端支撑。
  [MIT 许可](https://github.com/huxingyi/dust3d/blob/master/LICENSE)。
- [Procedural Multi-Rig Blender idle](https://github.com/Brolegion/Procedural-Multi-Rig-Animation-Blender-Addon/blob/main/idle_animation.py)：呼吸、噪声和骨链延迟。
  [GPL-3.0 许可](https://github.com/Brolegion/Procedural-Multi-Rig-Animation-Blender-Addon/blob/main/LICENSE)。仅作方法参考；未复制代码，未安装或运行该插件。

本工程独立实现。使用弱二次谐波改变呼吸波形、连续 Perlin 噪声提供微动，不逐帧随机抽值。
这些仓库的离线完整姿态生成没有直接替换本工程现有动画。

## 接入方式与状态合同

新增 `UMonsterIdleBreathingMeshComponent`，复用工程已有的 `FinalizeBoneTransform` 姿态叠加方式。
六个原生基类的默认骨骼组件改为该派生组件，其派生怪物自动沿用：
`ANurseZombie`、`AWolfMonster`、`AFleshHandMonster`、`AHandBrainMonster`、
`APoisonMaggotMonster`、`AHundredEyedSlagMonster`。

- 各怪物必须处于自己的严格 Idle 枚举，同时实际速度小于 3 cm/s，才淡入呼吸。
- 进入待机采用 0.35 秒时间常数，离开待机采用 0.12 秒时间常数，指数插值与帧率无关。
- 死亡、受控、击倒、物理模拟、暂停动画、离地、隐藏或关闭 Actor Tick 时关闭增量。
- 不增加 Tick、定时器、AI 决策或战斗时钟；沿既有骨骼求值终结流程运行。
- 不在编辑器预览/制作场景或 dedicated server 执行呼吸。
- 明确识别并跳过盲祷者；盲祷者源文件、动作和资产未修改。
- 在组件空间只修改选中胸背/掌面/体节骨骼，支撑肢和道具手臂保留输入姿态。
  只有选中的头颈或手指链带动其自身后代；不改 root、骨盆、脚、胶囊或 Actor 位移。
- 根据未加呼吸的动画局部姿态计算每次增量，不累积上一帧的旋转或尺度。
- 骨名与附肢索引按当前网格缓存；替换网格后重新映射。保留原来的主动画、后处理、蒙皮、材质、攻击接触与死亡/布娃娃控制。

## 落盘与交付

源码位于 `Source/FPSGAME/Monsters/MonsterIdleBreathingMeshComponent.h/.cpp`，
接入点是上述六个怪物构造器的默认骨骼组件类型。
不需要创建或覆盖动画、骨架、网格、蓝图或地图资产；不自动打开 UE 或运行游戏。
必要的常规 Editor 构建完成后记录实际结果；游戏观感由用户测试。

本轮 `FPSGAMEEditor Win64 Development` 常规后台构建已完成，结果为 `Succeeded`，
新呼吸组件及六个构造器接入点均完成编译，基础 `Binaries/Win64/UnrealEditor-FPSGAME.dll`
已经链接落盘。日志：`Saved/BuildEditor/build-20261002-154911.log`。
这是基础模块构建，不是 Live Coding 补丁。未启动/重启编辑器或游戏，未进行自动测试、截图或渲染。
