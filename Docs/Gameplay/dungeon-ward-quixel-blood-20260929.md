# 病区 Quixel 血迹替换

目标：替换隔离病区墙、地面的程序化血迹外观，保留进入场景时的随机分布；病床、玻璃和房间结构沿用当前版本。

本次用户下载的是 [Quixel Blood Stain](https://www.fab.com/listings/765d43e1-45ef-42f2-80a5-43d6214aa1d3)，资源编号 `sgfjdepc`。原始扫描区域 25 × 25 cm；8K glTF 包含颜色/透明度、法线、ORM。源文件和 Fab 元数据留存于 `SourceAssets/DungeonIsolationWard20260929/BloodScan20260929/Source`，遵循用户取得的 Fab 许可，不作为自制贴图发布。

## 实现

- 主材质 `/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel` 使用 Substrate 贴花，颜色、透明度、粗糙度与法线全部来自扫描贴图。
- 颜色纹理使用 sRGB，透明度从 Alpha 读取；ORM 按线性读取 G 粗糙度；glTF 法线翻转绿通道后按 UE 法线压缩导入。运行贴图上限 2K，原始 8K 保留。
- 稍偏暗红，按实例种子轻微变化明暗和干湿程度，不重新用程序噪声覆盖扫描轮廓。
- `DungeonBloodScatter.ScannedSizeRangeCm` 设为 `[25,60]`，单位为贴花完整宽度 cm。扫描采用正方形投影，防止原有长条范围拉扯纹理；随机位置和朝向保留，投影半深度由 10 cm 缩至 4 cm。
- 目标数量仍为地面 44、墙面 16，保留现有命中接收面和有界尝试逻辑；失败位置可跳过。仅使用本次下载的一款血迹，未声称已接入手印或其他喷溅扫描。
- `room.json`、`module-draft.json`、`prepare_design.py` 与完整安装入口同步，旧作者入口根据配置转入扫描材质作者，避免后续重建恢复旧外观。

## 落盘入口与状态

资源作者：`SourceAssets/DungeonIsolationWard20260929/Scripts/author_scanned_blood.py`。

编译新原生属性后，`apply_scanned_blood.py` 仅修改 `L_AbandonedIsolationWard_Subject` 内已有 `Ward_ProceduralBlood` 的材质和尺寸范围，再保存关卡。`install_scanned_blood.py` 串联两个阶段。

实际保存进度以 `BloodScan20260929/Receipts/material.json` 与 `map.json` 为准。源码已修改不等于 DLL 已编译、地图已接入。本轮不执行 PIE、截图、渲染或游戏测试，由用户自行测试。

## 本轮落盘结果

2026-09-29：3 张贴图与主材质已保存；正式 Editor 构建成功（`Saved/BuildEditor/build-20260929-193159.log`）。无界面 Python commandlet 已将新材质与 `[25,60]` cm 尺寸范围写入病区关卡，退出码 0，回执 `BloodScan20260929/Receipts/map.json`。未启动交互编辑器、PIE 或游戏；未进行运行测试或渲染。
