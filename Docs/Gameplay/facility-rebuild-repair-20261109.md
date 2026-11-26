# 废弃设施全量重建修复（2026-11-09）

用户要求修复旧版全量重建的历史快照冲突，保留当前场景与四轮写实升级。本次只修复作者重建与保存入口；没有新增素材、改动运行时代码、启动编辑器界面或运行游戏。

## 修复内容

1. `DungeonFacilityFlow20261007/extend_catalog.py` 保留当前布局库的独立副本。旧竞技场配方的中间校验不能用来判断最终目录；全部配方重放完成后，必须重新匹配安装布局库的完整校验值，并逐项匹配布局库内容。不能将旧坐标简单重新签名后写入。
2. 三个生态房间地板的对象路径统一为现有包路径；中转大厅拖把位置沿用已保存的浮点写法。没有移动这些部件，也没有放宽几何签名检查。
3. 增加 `installed_authoring_repairs.py` 与 `Sources/installed-authoring-repairs-20261109.json`。记录 39 项明确的旧值/新值修订：车站已有宝箱位置与通行区、医疗修订标记和玻璃效果、部分依赖顺序、接待区及发电机房净空表示等。逐字段匹配旧值或已应用的新值；任何其他值都会中止。补丁位于氛围配方之后、四轮写实配方之前，不替换整个模块或整份目录。
4. `build_sources.ps1` 不再运行最早入口的 Blender 导出器；`install.py` 不再调用旧材质导入或 `restore_original_entry.py`。现有固定入口、Actor、灯光、材质资产以及地图包都保留。正常重建结果与保存目录一致时直接返回，不重复保存相同包。
5. `rebuild_catalog()` 始终读取 `Sources/production-catalog.json` 和独立作者配方，不读取输出 `Config/catalog.json` 作为回退来源。磁盘目录与重建结果相同则不写；目录缺失可恢复；目录或保存地图出现独立修改则停止覆盖。布局库缺失必须先恢复已有布局库，不生成或伪造布局。

修订清单来自四轮写实升级前已经落盘的独立作者检查点。检查点路径与 SHA-256 仅记录来源；正常重建不读取该备份。各轮已有的实际资产仍保存在 Content，并由原各轮资产制作脚本维护。这个入口用于重建已安装场景的目录，不承担从空项目重新导入所有资产。

## 日常入口

```powershell
# 仅后台重建作者目录；相同内容不写入。
& D:\FPS3D\FPSGAME\SourceAssets\DungeonFacilityFlow20261007\build_sources.ps1

# 将重建结果与已安装地图对照，保留固定场景和资产。
# 沿用现有 UE 批次互斥；已有编辑器时走既有桥，不另开界面。
& D:\FPS3D\FPSGAME\SourceAssets\DungeonFacilityFlow20261007\install_background.ps1
```

正常输出分别为 `FACILITY_FLOW_RECIPE_UNCHANGED` 与 `FACILITY_FLOW_REBUILT_SCENE_PRESERVED`。新回执使用 `Receipts/rebuild.json`，阶段为 `scene_preserved`；早期安装回执继续保留其原始来源意义。

以后真实修改作者几何或玩法配置时，应通过对应制作批次同步生产目录与布局合同。重建入口遇到独立修改会保留现场，不能通过删除检查、强写旧快照或重签旧布局绕过。

## 本次实际检查结果

- 从最早作者源完整重放后，与当前生产目录相同：42 个模块、120 条布局；四轮美术重放与最新批次再次应用也一致。
- 显式禁止读取输出目录后，完整重建仍然成功；没有以当前输出冒充重建。
- 在临时目录中实际恢复缺失目录；独立改动的目录拒绝覆盖，原始字节保留。
- 注入过期布局合同、独立修改通行区，均在写入前拒绝。
- 实际执行 `build_sources.ps1`，退出码 0，输出 `FACILITY_FLOW_RECIPE_UNCHANGED`。
- 使用 UE `-run=pythonscript -nullrhi` 实际执行 `install.py`，退出码 0；地图内目录与重建结果一致，无资产重导和地图包保存。
- 前后比较 485 个文件的 SHA-256：生产地图、该地图全部外部 Actor/Object 包、旧入口资产目录及四轮升级资产目录均未变化。生产目录和布局库文件字节也未变化，包括本次地板材质、77 处玻璃绑定与固定入口的已保存优化。

证据：

- `SourceAssets/FacilityCompletion20261109/Receipts/catalog-check.json`
- `SourceAssets/FacilityRebuildRepair20261109/Receipts/rebuild-check.json`
- `SourceAssets/FacilityRebuildRepair20261109/Receipts/saved-rebuild-check.json`
- `SourceAssets/DungeonFacilityFlow20261007/Receipts/rebuild.json`
- `SourceAssets/FacilityCompletion20261109/Receipts/check-20261109-195145.log`

原入口源码、原安装器和生产 JSON 备份位于 `SourceAssets/FacilityRebuildRepair20261109/Backups/BeforeRepair/`。这次通过的是后台重建与保存一致性检查；未进行游戏实机、全场视觉或 FPS 验收。
