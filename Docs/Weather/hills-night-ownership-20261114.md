# 丘陵夜间光照归属修复（2026-11-14）

用户现象：丘陵夜间接近白昼亮度，未见月亮。

## 排查证据

后台只读加载 `/Game/GameMaps/L_TemperateHills_Initial`，结果保存在 `SourceAssets/HillsNightRepair20261114/before.json`：

- `DirectionalLight_0`（Hills Sun）可见、影响世界，强度 5，固定姿态，Atmosphere Sun Light Index 为 0。
- `SkyLight_0` 可见、影响世界，强度约 0.9；`SkyAtmosphere_0` 仍可见。
- 地图仍有植被研究阶段的固定曝光覆盖（Min/Max 均为 1）。已有运行时桥会释放该覆盖，但原始地图资产尚未迁移。
- 地图没有预置 UDS；天气桥运行时生成 UDS。旧的原生光照没有随之停用，且已退役的 TemperateHillsDayNightSky 不再更新这套旧灯。
- 当前 UDS 的月亮贴图存在，Render Moon 和 Render Moon Directional Light 均为 true；月光强度为 0.15，月相为 0，没有发现月亮资源缺失或关闭。
- 新增室内曝光适应只在房屋局部范围及白昼生效，未发现它向室外夜景施加亮度增益的路径。

## 修改

`FPSUDSHillsAtmosphere.cpp` 在丘陵 UDS 就绪后，停用制作脚本遗留的三个固定光照/大气组件；明确交给 UDS 的自定义光源不作停用。只按丘陵地图和原始持久层实例身份处理。

`Tools/Weather/hills_sky_ownership.py` 负责地图迁移：预置一套 UDS 天空、保留月亮与月光、关联既有高度雾、清理旧太阳/天空光/大气、释放旧固定曝光。后续丘陵制作脚本调用同一入口，不再重新生成固定日光。没有修改全局天空蓝图或主神空间。

`repair_hills_night.py` 保存丘陵地图，并记录中午、午夜及恢复 09:00 后的编辑器构造状态。这些数据不等于游戏渲染画面；云层遮挡与最终夜间观感由进场画面确认。

## 交付记录

实际保存与构建结果在本批次 `saved.json` 及 `Receipts/*-build.json` 中记录。


### 完成结果

- Game 构建于 18:55 成功。当前 Editor 模块已在 18:35 的共享构建中编译 `FPSUDSHillsAtmosphere.cpp` 并成功链接；源码、对象、DLL 时间和实际 DLL 中的修复标记已核对，回执明确标记复用既有构建。
- 在用户已运行的丘陵预览中只读取得：旧太阳与天空光 `visible=false`，UDS 太阳 5.6、捕获天空光 0.85 生效。此项证明运行时移交已执行，不是夜间画面验收。
- 结束相关丘陵预览后，通过现有编辑器互斥批次完成地图保存，移除三个旧光照/大气 Actor，预置单一 UDS；已恢复原 `/Game/GameMaps/DayNight_Lighting` 编辑地图及视口。
- 编辑器构造状态核对：12:00 太阳 5.6、月光 0、Night Filter 0；00:00 太阳 0、月光 0.15、Night Filter 1；月亮显示保持开启。最终地图恢复 09:00 后保存。
- 未启动额外游戏或渲染夜景截图；实际夜景明暗与月亮可见性由用户进场确认。
