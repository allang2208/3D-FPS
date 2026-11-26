# M24 机匣尾端透空修复（2026-11-02）

用户截图红圈位于先进机匣后端、瞄具后方与枪栓之间。当前实例确认使用独立握把版先进前机匣。实际套筒内孔半径约 18.8 mm，与原生枪栓尺寸不匹配；从后上方透过间隙可看到侧面抛壳窗后的背景。该处不是材质透明参数造成的问题。

## 已保存资产

- `/Game/Weapons/M24/ReceiverGripRebuild20261031/Meshes/SM_M24_AdvancedFront_ForIndependentGrip`：LOD 0、1、2。
- `/Game/Weapons/M24/AdvancedAction20261029/Meshes/SM_M24_m24_advanced_action`：现有 LOD 0。

只局部重建现有套筒内壁，形成连续收口。保留外壁、原尾端开口轮廓、抛壳窗及手柄活动空间；不增加独立遮盖件，不改双面材质。收口位于源 UE 坐标 Y=-10.84 至 -11.54 cm；14.2 mm 的最小内孔半径围绕原生枪栓轴线生成。该轴向范围在旋转手柄的前方。

所有替换三角形保存原三角形的重心坐标。发布时从当前 SOURCE_MODEL 读取面角属性，插值保留两套 UV、法线、顶点色及材质索引，再生成局部法线与切线。其余三角形直接保留。枪托、握把、枪栓模型、骨骼、动画及材质资产未修改。

## 本次排查范围与结果

- 使用实际静态源网格和保留的原生枪栓复现了红圈处透空；局部修补后的同角度离线预览不再出现原来的白色缺口。诊断预览按部件着色，不代表正式材质颜色。
- 当前保存的原生枪体与建模基线对应点位置一致。
- 读取当前保存的压缩开火动作 111 帧、空仓换弹动作 221 帧，按枪栓表面采样检查新增内壁区域；未发现采样穿入，最小间隙约 0.546 mm。此结果是局部离线几何排查，不等于游戏验收。
- 后台 commandlet 已实际写入两个 `.uasset`；`publish_receipt.json` 的 `complete` 为 `true`。
- 未打开 UE 编辑器，未启动游戏测试。

## 源与恢复

任务目录：`SourceAssets/WeaponRearOpening20261102/`。

- `author_patch.py`、`bore_patch.json.gz`：可重建的局部内壁补丁。
- `publish.py`：读取原属性、备份、写入全部目标 LOD 并保存。
- `geometry.json.gz`：修改前的源几何与磁盘哈希。
- `before_rear.png`、`after_rear.png`：同角度诊断图。
- `after_diagnostic.blend`：离线几何排查场景；正式 UV/材质以已保存 UE 资产及补丁发布流程为准。
- `saved_mechanism_clearance.json`：当前资产的局部活动间隙记录。
- `publish_receipt.json`：实际保存的资产、LOD 与最终哈希。
- `Before/Weapons/M24/...`：两个目标 `.uasset` 的修改前完整备份。恢复时仅使用这里记录的对应文件，避免覆盖后来其他改动；不要重新运行早期整枪生成脚本覆盖当前资产。
