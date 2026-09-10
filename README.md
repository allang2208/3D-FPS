# 无尽轮回 3D FPS · Unreal Engine 5

当前项目入口是根目录 **[FPSGAME.uproject](FPSGAME.uproject)**，基于 UE **5.8.2**。2026-09-10 起，`main` 已从旧 Godot 原型切换为 UE5 工程源码。

仓库包含当前宿主的完整 `FPSGAME` C++ 模块、Editor/Game targets、配置、库存与枪匠 JSON 数据、开发工具及工作流。原始模型、贴图、音频、地图等本地 Content 尚未纳入公开源码，恢复这些依赖后才能得到本机的完整游戏效果。当前源码状态和迁移记录见 [仓库迁移](Docs/RepositoryMigration.md)。

| 目录 | 用途 |
| --- | --- |
| `Source/` | 当前游戏代码：角色、枪械、UI/库存、天气、场景与怪物 |
| `Config/` | 工程、输入、渲染、CommonUI 与打包配置 |
| `Content/ColdSteelData/` | 当前物品、枪匠、仓库及提示数据 |
| `Tools/` | 导入、检查、运行验收与场景工具 |
| `SourceAssets/` | 当前 M4 抓握、甩匣、拍击的作者脚本和参数；二进制源在本机 |
| `Docs/` | 当前工作说明、功能验收记录和资源恢复说明 |
| `skills/` | UE5 枪械、手臂动画、C++、调试及天气标准 |
| `ThirdPartyNotices/` | 已记录的第三方来源说明 |
| `unreal/` | 迁移期间的历史快照；当前代码以根目录 `Source/` 为准 |

先读 [开发与发布规则](WORKFLOW.md) 和 [资源恢复](Docs/AssetSetup.md)。本机完整宿主仍位于 `D:/FPS3D/FPSGAME`，不要用历史快照覆盖它。

安装 UE 5.8.2 及其 Windows C++ 工具链，在 PowerShell 中编译：

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAMEEditor Win64 Development "-Project=$((Get-Location).Path)/FPSGAME.uproject" -WaitMutex
```

修改实际引擎路径，并从仓库根目录执行。工程启用了 CommonUI、EnhancedInput、Niagara 相关运行模块和 PCG；`ModelContextProtocol`、`AllToolsets` 是当前宿主额外安装的编辑器工具，详见资源恢复说明。

- [枪械与手臂工作流](WEAPON-WORKFLOW.md)
- [M4 当前动作合同](skills/ue5-fps-arms-animation/references/m4-baseline.md)
- [UI 与库存记录](Docs/UI/README.md)
- [雨效](Docs/RAIN_UPGRADE_20260910.md)、[雷雨云层](Docs/STORM_CLOUDS_20260910.md)

旧 Godot 项目的完整历史保留在 [archive/godot-before-ue5-20260910](https://github.com/allang2208/3D-FPS/tree/archive/godot-before-ue5-20260910)。它不再是当前开发入口。少量 `Tools` 中的 `.gd` 只是迁移参考导出器，仓库不再包含 Godot 游戏工程。
