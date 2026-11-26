# 丘陵地面准备失败：高度贴图采样类型修复

用户截图：场景准备失败，进度 89%，提示“地面材质编译失败，请返回主场景”，等待 63 秒。

本次 `Saved/Logs/FPSGAME.log` 的 2026-11-14 11:18:01（UTC+8）记录 `HILLS_GROUND material compile failed`：`T_ChapelEarth_H` 实际采用 `TC_ALPHA` 压缩，材质节点却为 `SAMPLERTYPE_LINEAR_COLOR`。这是实际材质编译失败，未修改加载门槛或屏蔽错误。

`temperate_ground_cache.py::road_surface` 新建的道路高度采样节点及 `AbandonedVillage/author_village.py::road_material` 的数据采样分支未处理 `TC_ALPHA`。两个作者脚本均补上 Alpha 分支，保留贴图压缩、颜色、法线、混合参数及连接。

后台 D3D12 / SM6 Python commandlet 用资产注册表查询这张高度贴图的全部直接引用，得到以下三个材质，并各修复一个错误节点：

| 材质 | 高度节点数 | 修复数 | 编译后像素／顶点指令数 |
| --- | ---: | ---: | ---: |
| `AbandonedVillage/M_VillageMudRoad` | 1 | 1 | 393 / 344 |
| `M_TemperateGround` | 1 | 1 | 2126 / 164 |
| `PebbleShore/M_PebbleShoreGround` | 2 | 1 | 2719 / 164 |

以上均位于 `/Game/WorldGeneration/TemperateHills/`。河岸地面的另一个高度节点原已使用 Alpha，保持不变。

调用 `MaterialEditingLibrary.recompile_material` 后再调用 `get_statistics`；本机 UE 5.8 的后者会提交缺失编译任务并调用 `FinishCompilation`，因此非零指令数不是仅“编译已请求”的记录。三个材质均无编译错误并保存，11:25:44 标记 `HILLS_HEIGHT_SAMPLER_REPAIRED materials=3 saved=3 compile_errors=0`，进程退出码 0。日志中三个初次加载的采样错误来自修复前旧资产，后续重新编译和保存成功。

证据及恢复边界：

- 修复脚本：`Tools/WorldGeneration/repair_chapel_height_samplers.py`。
- 逐材质回执、修改前后 SHA256：`SourceAssets/HillsGroundSamplerRepair20261114/repair.json`。
- 编译和保存日志：同目录 `repair.log`；启动参数和 DLL 散列：`launch.json`。
- 原始资产备份：同目录 `Before/Content/WorldGeneration/TemperateHills/`，仅以上三个材质。
- `Host/Content` 和 `Host/Plugins` 是联接，禁止递归清理进入目标；正式资产从项目 Content 入口保存。

未启动交互编辑器或游戏。本次确认材质修复、编译及落盘，不代表丘陵加载耗时、树木闪动或草地完整运行验收。

随后用户明确要求运行复查，已完成独立后台渲染检查：丘陵实际进入，原地面材质错误未复现；加载时长、画面采集和退出异常分别记录在 [运行复查](hills-runtime-check-20261114.md)，不将局部功能通过等同于整轮正常退出。
