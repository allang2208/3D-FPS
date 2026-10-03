# QBZ191 机械瞄具 ADS 左倾修复（2026-10-02）

用户反馈：近期统一枪械腰射默认位置之后，191 在机械瞄具 ADS 下向左歪。

## 定位

近期[统一腰射构图](rifle-hip-standard-20260930.md)使用前后瞄点的枪轴和 `WPN_root` 的上方向定义完整朝向，独立生成腰射位置与旋转。`UpdateADSPose()` 仍为 QBZ191 机械瞄具使用 `FindBetweenNormals`，只将前后瞄点连线对齐相机前向，保留绕瞄线的滚转自由度。腰射修正没有被叠入 ADS；差异来自两个状态使用了不同的朝向约束。

本轮后台只读作者源 `SourceAssets/QBZ191Refine20260913/QBZ191_base_Editable.blend` 的瞄准第 0 帧。原厂、angled、vertical、canted、prism 的枪根和瞄点一致。按现行单轴 ADS 算法转换后，枪根上方向的相机 Y/Z 倾角为 -4.88248°，对应向左倾斜。读取脚本和数值记录位于 `SourceAssets/QBZ191IronADS20261002/read_source_frame.py`、`source_frame.json`。这是源数据定位，不是游戏画面验收。

## 修改

`Source/FPSGAME/FPSGAMECharacter.cpp::UpdateADSPose()` 将 QBZ191 机械瞄具加入已有的完整瞄准坐标系标定：从同一瞄准第 0 帧取 `WPN_root` 上方向，与前后瞄点轴通过 `MakeFromXZ` 一起对齐相机前向和上方向。

位置继续按修正后的旋转计算 `EyeDistance * Forward - Rotation * Rear`，使照门保留原眼距并位于视线中心。没有写死 4.88° 补偿，也没有把腰射旋转搬进 ADS。保留原瞄点、12 cm 眼距、光学镜分支、腰射标定、骨架、手模、动画与配件资产；无需重新导入资产。

共享角色文件的修改前工作区快照位于 `SourceAssets/QBZ191IronADS20261002/Before/FPSGAMECharacter.cpp`。仅作追溯，不应整文件覆盖其他任务的修改。

## 交付状态

修复源码与制作记录已落盘。`SourceAssets/QBZ191IronADS20261002/build_editor.ps1` 的后台 `FPSGAMEEditor Win64 Development -Module=FPSGAME` 构建成功，UBT 总执行时间 18.87 秒，包含修改后的 `FPSGAMECharacter.cpp` 编译与 `UnrealEditor-FPSGAME.dll` 链接保存。结果另存 `build_receipt.json`，日志为 `Saved/BuildEditor/qbz191-iron-ads-20261002.log`。

未启动 UE 编辑器、游戏或 PIE，未执行运行测试、截图、渲染或验收。最终机械瞄具画面与开镜手感由用户测试。
