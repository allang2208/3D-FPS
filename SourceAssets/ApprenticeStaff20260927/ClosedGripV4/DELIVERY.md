# 长杖包握修正 V4 · 2026-09-27

用户提供的实机图片中，四指仍然摊开贴在杖前，拇指未形成对握。原图保存在 `user-feedback-v3.png`，对应修改前 V3，不是本轮渲染或验收结果。本次继续使用 `ue5-fps-arms-animation` 的 `vertical-grip-family.md`、`github-grasp-donor.md` 和 `pose-contact.md`，保留 V7 原生骨架。

## 修改

- 修正坐标转换：`target_reference.json` 是 Blender 坐标；V7 UE 原生参考位置为对应坐标的厘米值并反射 Y。V3 只做了左右手解剖镜像，漏掉导出坐标反射，导致屈曲方向错误。现在先把源旋转和掌面参考统一转换到 UE，再转为右手。
- 移除按三指节外接圆半径再次减弱握拳的搜索。完整保留已认可的 VRE 80% 四指包握和拇指横扣，通过整手接触坐标适配长杖，保留骨长、rest、平移和缩放。
- 握姿缓存增加版本失效条件，避免同一手模保留 V3 的错误缓存。
- 保留 V3 的上段握点、杖身构图、分件模型及肩肘腕运动，不再次改动握柄网格。

制作入口仍为 `UpperGripV3/author_grasp.py`；本轮数据归档在 `ClosedGripV4/grasp-source.json`，生成 `Source/FPSGAME/Weapons/Staff/StaffGripDonor.h`。运行代码为相邻的 `StaffGripPose.cpp`。修改前文件在 `ClosedGripV4/Before/`。

## 交付状态

源码与 19 个指骨的修正姿态数据已落盘。准备编译时，项目还有未完整构建的反射类型头文件改动，因此本轮不重复 V3 的类型热重载路径。

首次读取编辑器状态时无脏资产/地图、无 PIE；正常退出脚本执行时游戏已开始运行，保护条件触发并取消退出，未关闭或中断游戏。记录为 `editor-state-result-01.txt` 和 `close-result-01.txt`。随后用户选择正常关闭 UE 并继续编译。

已完成后台常规 Editor 构建，`Saved/BuildEditor/build-20260927-140450.log` 返回 `Result: Succeeded`，其中包含 `StaffGripPose.cpp` 的编译和基础 `UnrealEditor-FPSGAME.dll` 的链接。产物信息保存于 `build-receipt.json`。无需重新导入网格；本轮没有执行 Live Coding，也没有重新打开编辑器。

本轮未启动游戏、截图、渲染或测试，实际视觉由用户确认。
