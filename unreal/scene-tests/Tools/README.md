# 场景测试入口

## 整理记录（2026-09-09）

本轮废案归档在 `trash/scene-tests-20260909`；清单记录原路径、字节数及 SHA256，可按原路径恢复（先确认不会覆盖新文件）。早期 Normandy 建图脚本会重复创建出生点，已退出活动工具目录。一次性检查/MCP 脚本和过期 UI 操作记录亦已归档。

保留 `build_trench.py`（仅首次创建，已有地图时拒绝运行）、`organize_maps.py`（仅旧路径迁移，目标存在时拒绝运行）、两个修复脚本和启动入口；这些脚本不是自动重建整个项目的流水线。修复前备份、源场景和重定向资产均保留。

旧 `landing-trench-final.log` 仅站立通过但未识别雾体支撑，已经归档；当前战壕证据以 `trench-movement-final.log` 为准。下文 `landing-*-final.log` 现仅指 DayNight 和 Normandy。

项目：`D:\FPS3D\FPSGAME\FPSGAME.uproject`，引擎 UE 5.8。
三张游戏入口地图统一放在 Content/GameMaps。默认启动 DayNight_Lighting。
单人模式出生点前方生成两座测试门，靠近 2 米内按 E；返回和场景互换均通过门操作。
地图切换会重新创建角色和场景，不代表已接入跨地图存档。

## 战壕雾体碰撞修复（2026-09-09）

- 浮空支撑体是使用 MI_LocalVolFog 的大型 Cube。测试副本中改为 Custom 碰撞并忽略 Pawn；模型、雾材质及其他通道保留，源包不变。
- 备份：Saved/SceneTests/TrenchBeforeCubeFix-20260909.umap。保存重载报告：Saved/SceneTests/trench-blocker-fix.json。
- 战壕出生延迟至子关卡加载后，完成流送再选择有净空的落点，防止后加载的箱子、木墙夹住角色。
- 自动物理验收：`-SceneSpawnAudit -SceneMovementAudit`。trench-movement-final.log 记录 rise=1、fall=1、ground=1、moved=102.7cm、bad_support=0；支撑为场景木箱/木墙模型，不再是雾体 Cube。
- 这是局部自动行走和跳跃检查；未覆盖全部战壕路线，也不代表最终画面与所有简化碰撞已全面验收。

| 用途 | 内容浏览器路径 |
|---|---|
| DayNight 主地图 | `/Game/GameMaps/DayNight_Lighting` |
| Normandy FPS 测试 | `/Game/GameMaps/L_Normandy_FPS_Test` |
| Normandy 组件展示 | `/Game/UnrealNormandy/Levels/ML_Overview` |
| Military Trench FPS 测试 | `/Game/GameMaps/L_MilitaryTrench_FPS_Test` |
| Military Trench 组件展示 | `/Game/MilitaryTrench/Maps/AssetZoo` |
| Military Trench PCG 展示 | `/Game/MilitaryTrench/Tutorial/Scenes/PCG_Zoo` |

启动独立游戏窗口：

```powershell
& 'D:\FPS3D\FPSGAME\Tools\SceneTests\Open-SceneTest.ps1' -Scene MilitaryTrench
& 'D:\FPS3D\FPSGAME\Tools\SceneTests\Open-SceneTest.ps1' -Scene Normandy
```

## 已完成与边界

- Military Trench 源项目保留在 `D:\FPS3D\FPSGAME\MilitaryTrenchMegascansSa`，未修改源项目配置或资产。导入时 2024 个文件 SHA256 全部一致。
- 战壕测试地图通过模板复制，包含新路径下的外部 Actor；保存并重载确认 457 个 Actor、原 PlayerStart 和 FPSGAMEGameMode。关闭展示序列自动播放。
- 三张地图的出生点已重新做地面/胶囊净空检测并保存。单人入口在实际运行时重新检测安全点；失败时阻止生成，不再落回世界原点。
- DayNight 原 Floor 改为同范围、同表面高度的 40cm 厚实体地板，保留原材质；未新增第二块地板。天空球关闭碰撞，新增明确的 PlayerStart。
- 战壕测试地图已将外部 Actor 与私有地形 Nanite 网格内置到测试地图，源资产包不变。
- 修改前备份：Saved/SceneTests/SpawnFixBackup-20260909。运行时诊断使用 -SceneSpawnAudit，正常游戏不启用；日志在 Saved/SceneTests/landing-*-final.log。该检查只验证初始落地和连续站立，不等同于完整行走、视觉或传送往返验收。
- 2026-09-09 已通过 UE 资产重命名把三张入口地图移到 GameMaps，默认地图的新路径及传送门目标同步更新；未改变全局渲染设置。
- 迁移前备份位于 Saved/SceneTests/MapOrganizationBackup-20260909；旧目录可能保留 UE 重定向资产，不要当作重复场景手工删除。
- 测试地图仍共享源模型、材质、蓝图和部分关卡引用。Normandy 尤其共享原子关卡。重搭布局前复制要修改的子关卡/组装资产；修改材质时创建自己的实例，不直接覆盖原件。
- 首次运行会编译材质、纹理和 PSO；窗口启动不等于视觉与碰撞验收完成。待人工确认出生、行走、射击、光照、材质及帧率。
- 完整命令行检查仍有项目已有的 GameFeatureData 配置、MCP 端口占用和 ChaosNiagara 警告；地图脚本成功标记和 Saved/SceneTests JSON 报告单独作为保存重载证据，不能把进程退出码视为全项目通过。
