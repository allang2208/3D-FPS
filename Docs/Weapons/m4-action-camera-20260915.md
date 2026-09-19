# M4 换弹与拉栓镜头反馈

## 开源参考与选择

2026-09-15 阅读的项目及其实际覆盖范围：

| 项目 | 能确认的实现 | 本轮用途 |
| --- | --- | --- |
| [ARC9 / cl_camera.lua](https://github.com/necoarctic/ARC-9/blob/main/lua/weapons/arc9_base/cl_camera.lua) | 读取动画镜头挂点相对角度，按总强度、侧倾强度及 ADS 权重叠加到视角 | 借鉴动作时钟驱动镜头及分层控制的方法 |
| [ARC9 COD2019 / M4](https://github.com/Seulyy/ARC9-COD2019/blob/main/lua/weapons/arc9_cod2019_ar_m4.lua) | M4 指定 `CamQCA = 4`，使用 ARC9 的镜头运动接口 | 说明该机制有实际武器接入；不能据此宣称在本项目已运行通过 |
| [ProceduralFPSAnimationsPlugin](https://github.com/gerlogu/ProceduralFPSAnimationsPlugin) | 提供 UE4/5 曲线动画、Camera Sway 和示例工程；[许可证为 MIT](https://github.com/gerlogu/ProceduralFPSAnimationsPlugin/blob/main/LICENSE) | 借鉴可调曲线和组件分层；README 的最后更新说明为 2022-09-10，没有将它视为已适配本项目 UE5.8 的即插即用包 |
| [UE5-CrystalRecoil](https://github.com/CrystalVapor/UE5-CrystalRecoil) | 射击后坐力轨迹、玩家压枪及回正 | 侧重射击；本轮使用现有射击系统 |

ARC9 及 COD 武器包属于 Garry's Mod 生态。本轮把相关机制适配为 FPSGAME 原生 C++ 组件，没有安装其整套框架，也没有引入 COD 提取模型、音频、动画或复制仓库代码。镜头曲线和接触响应是按当前 M4 动作新写的参数，不宣称精确复刻 COD 的原始镜头轨道。

## 效果与时间

覆盖当前 M4 的普通换弹、空仓换弹、弹鼓换弹、弹鼓空仓换弹，以及装备时的拉栓。

- 甩出旧弹匣：明显侧倾，保留重量感后回摆。
- 插入新弹匣：较轻的垂直震动。
- 压实弹匣：更明确的点头和回弹。
- 空仓拍击／释放枪机：较强的反向点头，随后停稳。
- 装备拉栓：后拉产生牵引感，复位产生较明确的冲击。

镜头由两部分组成：动作过程中的缓慢跟随曲线，以及机械接触后的受力曲线。第二版将跟随缩放提高到 3 倍、接触缩放提高到 3.5 倍后，用户仍反馈基数偏小。第三版保留这些缩放，直接提高源曲线的角度与位移基数，并延长响应。实际视觉幅度还取决于曲线叠加、动作速度与角色镜头系数。

接触响应采用分段平滑曲线：在持续时间的 23% 达到主峰、37% 保持 82% 力度、72% 回摆到 -24%、末端归零。第三版出匣持续 0.55 秒（弹鼓 0.65 秒）、插匣 0.36 秒、压匣和枪机释放最多 0.48 秒；装备后拉 0.22 秒、复位 0.26 秒。这里均为源动画秒数，随现有动作速度映射。压匣和枪机尾段限制在动作结束前归零。

主要基数变化（以下为源角度，不是实测画面角度）：

| 项目 | 第二版 | 第三版 |
| --- | --- | --- |
| 普通甩匣跟随侧倾 | 1.10° | 2.60° |
| 普通甩匣接触侧倾 | 1.25° | 2.80° |
| 插匣接触侧倾 | -0.35° | -1.00° |
| 普通压匣接触俯仰 | 0.80° | 2.00° |
| 弹鼓压匣接触俯仰 | 0.95° | 2.40° |
| 空仓放栓接触俯仰 | -0.85° | -2.30° |
| 装备放栓接触俯仰 | -0.85° | -2.25° |

位置基数同时提高，例如压匣向后牵引从 0.18 cm 提高到 0.65 cm，上抬从 0.15 cm 提高到 0.55 cm。甩匣跟随主峰由接触后 0.12 秒移到 0.14 秒，第一段回摆由 0.32 秒延到 0.40 秒，延长动作重量的停留。

| 动作 | 出匣 | 插入 | 压实 | 枪机释放 |
| --- | --- | --- | --- | --- |
| M4 普通 | 29/60 秒 | 76/60 秒 | 95/60 秒 | 无 |
| M4 空仓 | 21/60 秒 | 54/60 秒 | 80/60 秒 | 130/60 秒 |
| 弹鼓普通 | 18/60 秒 | 76/60 秒 | 95/60 秒 | 无 |
| 弹鼓空仓 | 14/60 秒 | 54/60 秒 | 80/60 秒 | 116/60 秒 |

表中是当前源动画秒数。运行时直接读取已有 `MechanicalCueTimes`，没有新增另一套换弹接触时钟。源时间通过 `ReloadSourceTime` 获取，保留弹鼓的非线性时间映射与换弹属性的速度缩放。归零终点同样取该映射的实际结束时间，兼容弹鼓空仓动作使用片段前 148 帧的路径。

装备动画采用 `M4WrapGrip20260910` 的实际拉机柄轨道：第 15 帧开始后拉、第 18 帧接近后止点、第 22 帧回到前方。源动画为 60 fps、38 帧；按现有 0.72 秒装备状态映射。源轨道读取文件在 `SourceAssets/M4ActionCamera20260915/charge-source.json`。M4 装备姿态也改为读取现有 `WeaponStateElapsed`，使镜头和手臂共用状态时钟。

制作前查看的现有参考：

- `SourceAssets/M4TacticalToss20260910/Delivery/非空仓甩匣取弹检查.jpg`
- `SourceAssets/M4SlapImpact20260910/Delivery/拍击接触分帧.jpg`
- `SourceAssets/M4HK416Replica20260910/Reference/equip_charge/Frame_0021.png`（历史源动作参考）

## 接入与调节

`UWeaponActionCameraComponent` 是角色拥有的独立组件，不新增 `AFPSGAMECharacter` 成员，不开独立 Tick，也没有 RPC。`UpdateCamera` 在现有视角计算后调用它。

组件通过 `UCameraComponent::AddAdditiveOffset` 影响最终渲染视图，不修改 `ControlRotation`、相机组件变换、手臂骨骼或弹道计算。它目前是 FPSGAME 中相机 additive offset 的唯一写入者，每帧先清除上一帧偏移，再应用当前采样；未来若新增该接口的写入者，应在此处合成。

换弹／装备结束时归零对应动作偏移。切枪重置冲刺镜头状态，进入枪匠观察、攀爬或施法阻断时停用该层。ADS 权重会衰减效果。此前 M4 压匣和放栓写入射击镜头弹簧的微小脉冲已移到本层，原枪身机械震动继续保留。

## 第三版战术冲刺镜头

M4、AKM、QBZ191 的各握把共用新的镜头响应。`UpdateCamera` 采样现有脚步相位，组件把左右整步侧倾、偏航和每次落脚的俯仰／起伏合成到同一个 additive offset。落脚使用圆滑脉冲，去除平均值，避免连续跑动使镜头高度偏移。

- 源旋转基数：俯仰 2.4°、偏航 0.9°、侧倾 4.0°。
- 源位移基数：前后 0.4 cm、左右 2.2 cm、上下 2.6 cm；俯仰与上下位移另叠加落脚脉冲。
- 在默认角色 `CameraMotionScale=0.45`、满速和非 ADS 条件下，持续侧倾的计算幅度为 1.8°，旧逻辑约为 0.15°。这是参数计算，未作本版实机测量。
- 强度随实际移动速度和着地权重混合；进入和退出的指数响应速率分别为 9、6。目标不变时约 0.26 秒达到 90% 强度，停跑约 0.38 秒衰减掉 90%。
- 进入和退出期间，旧步行镜头随新镜头权重反向混合；相位连续，快速松开／重按冲刺也不重置波形。
- 瞄准、开火、换弹会停止冲刺请求并衰减冲刺镜头。切枪重置状态；滑铲、闪避、攀爬、枪匠观察和施法阻断由各自表现接管。

本次只调整镜头代码和配置，现有握把与左手退到画面外的冲刺动画沿用上一轮资产。

配置位于 `Config/DefaultGame.ini`：

```ini
[/Script/FPSGAME.WeaponActionCameraComponent]
Strength=2.0
FollowStrength=1.5
ImpactStrength=1.75
SprintStrength=1.0
SprintAnglesDegrees=(X=2.4,Y=0.9,Z=4.0)
SprintTravelCM=(X=0.4,Y=2.2,Z=2.6)
```

- `Strength`：换弹／装备动作总强度，0 关闭，最大 4。
- `FollowStrength`：缓慢跟随动作的幅度。
- `ImpactStrength`：接触时的短震幅度。
- `SprintStrength`：独立的战术冲刺强度，0 关闭，最大 3。
- `SprintAnglesDegrees`：冲刺俯仰、偏航和侧倾基数，单位为度。
- `SprintTravelCM`：冲刺前后、左右和上下位移基数，单位为厘米。

这些值同时暴露在组件的 Weapon Camera 属性中，并乘以现有角色 `CameraMotionScale`。角度以度、位置以厘米表示。具体动作参数位于 `Source/FPSGAME/Weapons/WeaponActionCameraComponent.cpp`；当前为用户反馈后的第三版幅度与节奏参数，由用户在游戏中测试手感。

## 交付状态

第三版源码和配置已修改。编辑器关闭后通过 `Tools/Build/Build-Editor.ps1` 构建；等待已有构建释放锁后，本轮完成 7 项增量链接／元数据工作，退出码 0、`Result: Succeeded`，输出普通 `UnrealEditor-FPSGAME.dll` 及依赖插件模块。日志为 `Saved/BuildEditor/rifle-camera-strength-v3-20260915.console.log`。未启动游戏、生成预览或进行本版运行测试，新的镜头幅度与节奏由用户测试。

下面为第二版构建记录：

第二版幅度与节奏修改已随 AKM / QBZ191 冲刺扩展完成 160 项完整重建，退出码 0、`Result: Succeeded`。本次日志为 `Saved/BuildEditor/rifle-sprint-camera-rhythm-20260915.console.log`。未运行游戏测试，由用户测试新的镜头手感。

下面为第一版构建记录：

已完成源码接入、可调参数和源动作时间记录。编辑器关闭期间完成 160 项完整重建；最后的源结束时间接入修改另完成 4 项增量构建，均退出码 0、`Result: Succeeded`。输出普通 `UnrealEditor-FPSGAME.dll`，没有使用后缀热重载模块。

日志：`Saved/BuildEditor/m4-action-camera-20260915.console.log`、`Saved/BuildEditor/m4-action-camera-final-20260915.console.log`。按用户规则，本轮没有启动游戏、渲染预览或运行测试；由用户重新打开 UE 后测试实际幅度、节奏和晕动感。
