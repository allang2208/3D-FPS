# 关闭 UDS 自动光照转换提示

用户要求以后进入场景不再弹出 `Convert Existing Lighting Scenario`。

本机 UDS 的 `Ultra_Dynamic_Sky` 蓝图在 `Query Project Settings And UDS Version` 初始化图中自动调用 `UDS_LightingScenario_Convert` 编辑器工具。这个工具会询问是否匹配原场景光照并删除冲突 Actor，属于作者迁移入口，不是游戏天气必需逻辑。

已在 `/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky` 中断开唯一的自动执行连接：`K2Node_MacroInstance_0.Is Valid -> K2Node_Message_0.execute`。该调用没有下游执行工作；其他项目设置查询和初始化逻辑保留，手动光照转换工具本身保留。没有删除场景灯光，没有修改地图、天气数值或 C++。

通过后台 PythonScript commandlet 完成蓝图编译和实际保存，最终进程返回 0；没有启动交互编辑器或运行场景测试。先前读取期间编辑器已退出，后续资产写入在无编辑器占用时完成。

- 可重放制作脚本：`SourceAssets/UDSNoConversionPrompt20261106/disable_auto_prompt.py`。
- 原资产备份：同目录 `Before/Ultra_Dynamic_Sky.uasset`。
- 保存回执：同目录 `save-receipt.json`。
- 最终制作日志：同目录 `save-commandlet-03.log`。前两轮脚本适配失败发生在保存前，不代表最终状态。

后续如果整体替换或升级 UDS 母蓝图，需要迁移这条项目定制。运行效果仍由用户自行测试。
