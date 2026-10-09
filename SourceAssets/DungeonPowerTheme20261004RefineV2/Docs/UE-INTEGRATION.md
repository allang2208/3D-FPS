# RefineV2 本地导入

2026-10-06：两台服务器已在原测试地图接入独立搜寻容器，上排左侧模块向外抽出 32 厘米后打开搜寻界面；总控室剩余门参数已补存。制作与保存记录见 [服务器抽拉容器](../ServerContainers20261006/README.md)。未运行测试。

2026-10-05：第三间房总控室迁至二层，改为真实玻璃大开间；平台、护栏和两座 2.4 米宽楼梯同步重做，设备/容器/灯具重新布置。15 个专用资产及原测试地图已保存，当前门参数收尾状态见 [二层总控室记录](../UpperControlRoom20261005/README.md)。本轮未测试。

2026-10-05：文字卡片修订已实际保存到原测试地图，26 个 Actor、175 处牌面采用新几何与按尺寸原生排版的文字。后续样板重建和模块草案导出自动保留本轮引用。详见 [文字卡片制作与接入记录](../TextCards20261005/README.md)。本轮未进行运行测试。

## 范围

- UE 5.8.3，工程 `D:\FPS3D\FPSGAME`
- 新源目录 `SourceAssets\DungeonPowerTheme20261004RefineV2`
- 新资产 `/Game/Dungeons/PowerTheme20261004/RefineV2`
- 当前唯一地图 `/Game/GameMaps/Design/L_PowerTheme20261004_Subject`
- 返回地图 `/Game/GameMaps/DayNight_Lighting`

按用户后续要求，新版已发布到原样板入口；未被新版或其他场景引用的旧PowerTheme专属资产与作者目录已可恢复归档。车站、Staff/DataArchive/Facility共享资产均不改写。原有打开的编辑器/后台导入不得终止。先保存用户工作，等共享批次互斥量空闲后再运行。导入器拒绝未授权、未归属或不同指纹资产；不得通过删除保护绕过。

## 生产命令

在本地 PowerShell，用已确认的 UE 5.8.3 命令行程序路径：

```powershell
& 'D:\FPS3D\FPSGAME\SourceAssets\DungeonPowerTheme20261004RefineV2\Scripts\install_background.ps1' -ProjectRoot 'D:\FPS3D\FPSGAME' -UnrealEditorCmd '<已确认的UE5.8.3路径>\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' -AuthorizeProjectWrites -Stage All
```

该包装器同步持有 `Local\CodexUeMcp-Port-8000`，依次运行资产导入和新样板组装。已有 FPSGAME 编辑器或 commandlet 时拒绝启动，不结束任何进程。未指定 `-AuthorizeProjectWrites` 不写入。

资产碰撞计数沿用本地已确认的 `StaticMeshEditorSubsystem.get_convex_collision_count`，不回退到不存在的旧API。

中文柜体覆写是组件级材质绑定：包括可搜索柜体的移动门/抽屉。配电柜中文牌使用独立alpha图层，原BaseColor/NormalGL/ORM按字节保留；仅新主题材质混合中文区域。

导入阶段只创建本包命名空间内的新网格/材质/图；组装阶段只保存新的RefineV2样板。现有原资产依赖必须存在，缺失则停止，不制造替代品。

## 成功判据

本地 `Receipts/import.json` 必须为当前 revision 的 `assets_saved`；`Receipts/subject-map.json` 必须为同 revision 的 `map_saved`。以真实回执报告成功，不能把云端作者结果当成本地导入结果。

新地图保存后用户可执行：

```text
open /Game/GameMaps/Design/L_PowerTheme20261004_Subject
```

返回：

```text
open /Game/GameMaps/DayNight_Lighting
```

未加入MapsToCook的样板在打包版本中可能不可用。没有修改默认地图、菜单、正式随机池、战斗/导航、光照调度器或怪物生成。

## 可编辑制作源重建

完整包包含Blender源和实际原FBX/贴图。Python需Pillow、fontTools；Blender作者版本4.3.2。字库从References/Fonts读取。

依次运行准备脚本：prepare_design.py、layout_reuse.py、prepare_revision.py、prepare_chinese_container_labels.py、prepare_chinese_cabinet_overlay.py、prepare_chinese_server_overlay.py、prepare_chinese_workshop_overlay.py、place_revision_supplement.py。

随后Blender后台依次运行 author_scene.py、assemble_reused_assets.py、apply_source_surfaces.py、assemble_revision_supplement.py。最后运行prepare_modules.py、write_layout_drawing.py。这些是生产步骤，不是游戏/视觉验收。

不要运行References下历史安装器；它们只是接口/来源证据，可能指向旧地图。

## 本机实际发布与恢复

实际导入、中文组件材质绑定、原入口发布、引用审查和可恢复归档记录分别见 Receipts/import.json、subject-map.json、publication-reference-audit.json、publication-archive.json、completion-local.json。

恢复目录：`D:\FPS3D\FPSGAME\trash\PowerTheme20261004-ReplacedByRefineV2-20261004-145441`。目录内 Restore-Previous.ps1 可在关闭编辑器、互斥空闲时显式恢复上一版，并先保留当前新版地图；此脚本未执行。旧版已退出项目可用场景，RefineV2临时样板也已归档。

本地实际引擎5.8.3。本轮仅后台导入/保存/发布；未启动游戏、PIE、渲染或验收，不进入正式随机池。
