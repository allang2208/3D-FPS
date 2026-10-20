# SVCh 标准／扩容弹匣接口修复

用户报告两种弹匣错位、没有插入接口。本轮范围为标准 10 发与扩容 20 发弹匣的装配、互斥显示及换弹抓握；保留上一轮左手拉栓。

## 原因

标准弹匣的源模型装配正确，但共享 SVD 动画的弹匣骨在中立姿态相对该源模型存在约 6.648 cm 的位移。枪体替换时未抵消该装配差。旧绑定变换在枪体坐标中的平移约为 `(-0.22775, -6.13887, +2.54120) cm`。

扩容显示原先落入通用步枪分支。SVCH 未匹配 SVD 专用资产条件，因而会走到 M4 扩容网格；原厂隐藏规则又依赖材质名含 `Magazine`，未匹配本模型的 `KVInhibitor_mag` 和 `bullet_338lp`，会留下原厂弹匣及弹药。

## 修复方式

两种弹匣独立为精确适配当前 `WPN_SOCKET_Magazine` 的刚体配件。标准件复制已选枪体的原厂弹匣与弹药；扩容件使用同一下载源中的 `other\mag_extended.smd` 及其原始贴图，去掉作者为了分开展示而设置的物体下移，保留原有供弹接口。没有将 M4 弹匣缩放成 SVCh 弹匣。

导出时使用实际装配姿态的插座逆变换，运行时位置和旋转为零，只使用 `.01` 抵消骨架继承的 ×100 单位。标准与扩容共用正确接口和机械骨轨迹；原枪体中旧弹匣／弹药的两个精确材质分区隐藏，避免双层重叠。拆掉扩容时恢复适配后的标准件。两种配件都随宿主视模显隐。

只在弹匣操作窗口同步左手目标：普通换弹在第 255–302 源帧释放修正，空仓在第 248–292 帧释放；第 292 帧之后的左手拉栓和回位保持上一版。沿用手掌朝向及手指局部曲线，用固定骨长的肩肘解算跟随修正后的弹匣，必要肩点跟随不超过作者结果中的约 1.93 cm。右手、枪机、弹匣骨、总时长和机械音效时钟保持原值。

没有重导入枪体骨骼网格，没有写入 V9 的网格、参考绑定、权重、材质或形变目标，也没有改写共享 SVD 序列。

## 制作和接入文件

目录：`SourceAssets/SVCHReplacement20261018/MagazineSeat20261019/`。

- `Inputs/`、`runtime_magazines_before.json`：本轮活动资产及现有 PIE 的只读记录；读取时旧 SVCH 视模被用户切换隐藏，不能据此宣称现有扩容画面已抓拍。
- `seat_calibration.json`、`author_magazines.py`、两个 `SM_SVCH_Magazine*.fbx`：原厂装配到实际插座的转换与两款模型。
- `SVCH_MagazineSeat_Editable.blend`：标准／原生扩容模型制作源。
- `author_contact.py`、`profile_magazine_seat.json`、`SVCH_MagazineSeat_ReloadGrip_Editable.blend`：在当前左手拉栓版本之上的普通／空仓抓握修正及可编辑标准弹匣动作。
- `install_assets.py`、`install_profile.py`、`run_finish.ps1`：实际保存及构建入口；`assets_receipt.json`、`profile_receipt.json`、`build_receipt.json` 分别记录结果。
- C++：`Source/FPSGAME/Weapons/SVCHMagazineAssets.h` 与 `M4DrumVisual.cpp` 的 SVCh 分支。

运行路径为 `/Game/Weapons/SVCH/Replacement20261018/MagazineSeat20261019/SM_SVCH_Magazine10`、`SM_SVCH_Magazine20`。抓握配置继续使用当前 `SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip`，避免丢失左手拉栓版本。

## 检查范围

`contact_check.json` 对实际源姿态与新配置进行重建：两种换弹的右手和机械变换差为零，手掌朝向差处于舍入量级，骨长误差约 1.3e-9 cm；空仓第 292 帧后的姿态重建差约 3.7e-8。沿先前换弹相机记录的离线投影，没有新增臂根入镜采样。这些是离线数值检查，不等于当前游戏画面验收。

保存后通过 `check_saved_seats.py` 对 UE 实际导入的顶点与原装接口逐点比对，结果记录在 `seat_check.json`。本轮不主动开启游戏或截图；最终视觉与手感由用户确认。

2026-10-19 后台 `FPSGAMEEditor Win64 Development` 构建成功，两款静态弹匣、扩容材质／贴图及抓握配置均已实际保存。UE 导入顶点重建到原模型装配位置后的最大误差：标准约 `6.24e-6 cm`，扩容约 `5.89e-6 cm`。此数字只证明资产坐标转换和导入一致，不代表已完成游戏画面验收。新配置 SHA-256：`d26541acd94b6ab409914d2216cc5a3c722df9fcb4cb788313fa98990745b57e`。
