> 旧彩色 `Icons/` 和 `Scenes/` 已移入本机 `trash/sword-publication-20260927/SourceAssets/MeleeAttachmentIcons20260927/`。几何来源读取脚本、来源快照和历史记录保留；当前渲染与导入从 [灰阶作者入口](../MeleeAttachmentIconsGray20260927/README.md) 开始。

# 近战改造栏图标检查与替换 — 2026-09-27

已完成符文长剑、寒晶剑、高地双手剑、伐木斧、矿镐的全部分类、原装项与可选改造图标检查，共 130 个条目。

- 重做替换 76 张旧图，补齐 50 张缺图，保留 4 张合格的近期图标。
- 126 张新 PNG 已写入 `Content/ColdSteelData/AttachmentIcons20260913`，同名 UE Texture2D 已导入并保存。导入回执见 `import_receipt.json`。
- 新图统一 1024×1024 RGBA、透明底、居中正交安装侧视，武器纵向前端向左，最大轮廓占幅约 83%。没有对原图进行镜像来代替模型转向。
- 使用当前实际部件模型和材质。高地剑使用连续连接区 V5 和棱脊穿甲刃窄根 V2；保留部件所需的安装适配座。
- 符文图标使用真实剑身、现有运行时符文贴图和材质公式，静态采样时刻为 2.4 秒。没有新画与游戏不一致的符号。
- 斧、镐的改造目前只改变数值：图标取对应原装模型区域，同槽数值改造复用原装图。改件槽没有独立模型，按规则复用实际头部和接头。
- 保留棘冠配重球，以及符文长剑的陨星锤首、凝碧星核、疾星配重图标。

## 检查结果与预览

检查范围仅为用户要求的图标：已逐组查看更换前后总览，核对透明通道、完整轮廓、尺寸与留白。未启动 PIE 或进行游戏测试，未主动打开或重启 UE。游戏内显示由用户测试。

- [高地双手剑](after_ue_highland_claymore.jpg)
- [符文长剑](after_ue_rune_sword.jpg)
- [寒晶剑](after_ue_frost_crystal_sword.jpg)
- [伐木斧](after_tool_axe.jpg)
- [矿镐](after_tool_pickaxe.jpg)

## 生产文件

- `baseline.json`、`Before/`：开始检查时的目录与旧 PNG 快照。
- `runtime_sources.json`、`rune_sources.json`：当前 UE 网格、材料与符文贴图来源。
- `render_icons.py`、`rune_surface.py`、`Scenes/`：可重做的渲染脚本与打包材质的部件场景。
- `Icons/`：126 张新图；保留的 4 张仍使用原正式路径。
- `audit.json`、`visual_review.json`：130 个条目的逐项结果与视觉检查记录。
- `BeforePackages/`、`backup_manifest.json`：被覆盖的正式 PNG、UE 资产备份及哈希。
- `import_receipt.json`、`import-bridge-01.txt`：126 张图已导入并保存的回执。

本次未修改武器模型、改造属性、战斗代码或存档格式。
