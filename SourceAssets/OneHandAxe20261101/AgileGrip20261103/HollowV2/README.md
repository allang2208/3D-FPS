# 握柄中段镂空 V2

用户要求将原轻捷握柄改成参考图中的中段镂空形式。名称为破阵握柄，ID `hatchet_grip_agile`，属于特殊改造。本页及保存回执记录外观改版时的状态；用户随后指定的新数值已同步至 `hollow_grip.json`，当前属性以父目录 `design.json`（`user_tempo_20261103`）为准：体力消耗-25%、攻击速度+15%、重击蓄力速度+15%、武技冷却时间-20%。

保留 V1 外侧握持轮廓、两端连接面和紧固件；中段切出一个长圆贯穿孔，双侧连续框架包围开孔，孔缘使用小倒角与银灰加工面，黑色碳纤维握片延续原材质。孔宽 1.36 cm，局部 Z 范围 -14.58 至 -5.82 cm，总长仍 19.25 cm。孔穿过整个 Y 向厚度；不是黑色贴片或浅凹槽。握柄装配位置仍为 `[0,0,11.5] cm`，柄尾偏移仍为零，既有挂坠规则继续使用。

图像只作为中空框架的造型参考；图中斧头、紫色纹饰、外露尖刺和缠线不在本次握柄改动范围。原图保存在 `References/user_hollow_grip.jpg`。

## 入口与资产

- `author_hollow.py`：以父目录保留的 V1 Blend 与纹理为固定源，制作贯穿孔、内壁与倒角；孔边三角化后烘焙 2K BaseColor/Normal/ORM，导出 FBX 与可编辑 Blend。
- `render_icon_input.py`：只制作实际模型的 UI 图标素材。统一金属框图标由内置 imagegen 制作，见 `icon_manifest.json` 和 `icon_prompt.txt`。
- `import_hollow.py` / `run_import.ps1`：无界面导入新命名网格、材质、贴图及同一改造 ID 的 UI 图标。网格沿用已编译导入助手允许的 `ModulesV1` 路径，法线导入时翻转绿色通道。
- `register_hollow.py`：仅切换模型/材质配方与外观描述，保留现有数值字段、选项 ID 及其他槽位。
- `record_delivery.py`：记录已保存资产及接入状态，不运行验收。

父目录 `prepare_pipeline.py` 与常用制作/导入/登记入口已指向本修订，V1 入口脚本、旧制作清单和旧图标备份在 `Before/`。父目录原 Blend、纹理及 `Before/agile_grip.json` 作为 V1 固定制作输入保留；父目录 `agile_grip.json` 在接入后同步为当前清单，`active_model.json` 指向当前模型源与回执。

无需 C++ 改动或重新编译。实际保存状态以本目录 `delivery.json` 为准。未启动游戏、未做手部穿模或联机测试；图标素材渲染不作为游戏验收。

本次后台导入与登记已完成：实际保存 6 个 UE 资产（新网格、材质、3 张 PBR 贴图和同一选项的新版图标），模块配方与外观文案已切换至中段镂空版本。数值及其他改造项保持原配置。入口、制作源与实际保存路径见 `delivery.json` 和父目录 `active_model.json`。
