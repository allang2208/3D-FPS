# PKM 木制提把分件与惯性摆动

2026-09-23，按用户要求，将木制提把作为独立活动件，在换弹、奔跑等枪身运动中产生带阻尼的摆动。

## 模型制作

源为当前模块化枪体 `../Accessories14/PKM_Modular_Editable.blend`。

- 141 个原始部件中的 `PKM_Part_136` 是木柄，`PKM_Part_075` 是与之连接的金属支架。二者共同刚性绑定到新增 `PKM_CarryHandle`，父骨仍是 `WPN_root`。
- 铰轴取金属支架根部两条窄边的中线，沿原枪体 Y 轴。源坐标中心约 `(0.019102, -0.090669, 0.060028)` 米；不使用木柄整体中心充当转轴。
- 木柄与支架保持独立可编辑网格，沿用原 UV、木纹、金属涂层、法线及倒角。仅这两个部件改为新骨骼的刚性权重。
- 原骨骼、其他网格和权重不动；不重导入现有动画。新骨骼在原动作上继承枪根，再由运行时摆动层驱动。
- 保留枪托／后握把／枪口改造分区及旧／新弹箱、弹链的显隐材质身份。

当前作者源：`PKM_CarryHandle_Editable.blend`。后续重新导出枪体请以此版本为基底，避免 Accessories14 的旧网格覆盖新铰轴。Reload16 换弹与 Combat17 冲刺／近战继续沿用，不需要重新制作。

## 运行方式

`FPKMCarryHandleDynamics` 在第一人称网格完成作者动画与施法姿态后，更新独立提把骨骼。每个网格实例有自己的运动状态。

- 使用枪根铰轴的世界加速度及角加速度产生惯性力矩，包含换弹倾枪、奔跑摆动、起步和停步。
- 单轴弹簧、阻尼、适度重力偏转；不是一段固定正弦抖动，也不是整个武器的 Chaos 刚体模拟。
- 初始设置：固有频率 3.8 Hz，阻尼比 0.62，转角范围 −9° 至 +7.5°；积分子步不大于 1/240 秒。
- 木柄与支架一起绕根部转动，无平移自由度。转动范围用于限制过度摆动，不作动态碰撞检测。
- 切枪、隐藏、长停顿或相机位置跳变时清除弹簧速度，防止换枪后突然甩动。重复姿态求值不会在同一游戏帧重复积分或叠加旋转。
- 不修改弹药结算、装箱时钟、射速、伤害、移动速度或改造件数值。

代码：`Source/FPSGAME/Weapons/PKMCarryHandleDynamics.h/.cpp`，接入点为 `Source/FPSGAME/Skills/FPSCastingMeshComponent.h/.cpp` 的姿态完成阶段。

## 导入与恢复

- `read_source.py` / `source_geometry.json`：转轴定位所需的源部件几何读数，无渲染／验收。
- `author_handle.py` / `authoring.json`：分件、刚性权重及铰轴制作。
- `Exports/SK_PKM_Manny_Modular.fbx`：模型导出。
- `import_handle.py`：通过工程互斥桥更新当前运行网格 `/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular`，保留 PKM 私有骨架及当前实际材质绑定。
- `materials_before.json` / `imported.json`：导入前绑定和最终保存回执；按 FBX 导入材质身份绑定，避免再次出现木柄／枪身串色或弹箱显隐串段。
- 原始源模型、Accessories14 作者源以及所有动作作者源均保留，可重新导出恢复。

## 状态

模型分件、FBX、动力学代码已完成。常规 Editor 构建成功，记录为 `build.log` 与 `Saved/BuildEditor/build-20260923-081021.log`，Result: Succeeded。模型、私有骨架及原材质绑定已导入保存，回执为 `imported.json`、`Saved/pkm18-import-handle-02.txt`。第一次桥调用因编辑器退出未连接到执行节点，没有提交导入；重连后的第二次调用完成保存。构建后已重新打开编辑器完成接入，没有启动 PIE。

按用户规则未运行游戏测试、截图或验收渲染。实际摆动幅度、近景接触和构图由用户实机体验后反馈。
