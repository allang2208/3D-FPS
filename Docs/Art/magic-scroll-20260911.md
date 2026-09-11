# 捆扎魔法卷轴接入 — 2026-09-11

已制作写实羊皮纸卷轴的正、右侧、背面三视图，从同一正面图提取透明背包图标，并将三个独立视角送入 RTX 5080 TRELLIS.2 管线。四种现有附魔卷轴共用外观：`enchant_scroll_heavy`、`enchant_scroll_sharp`、`enchant_scroll_skeleton`、`enchant_scroll_tarantula`。名称、附魔效果、稀有度和 99 堆叠上限保持原定义。

## 交付文件

- [三视图](../../SourceAssets/MagicScroll5080_20260911/magic_scroll_three_views.png)
- [透明背包图标](../../Content/ColdSteelData/Icons/magic_scroll_realistic_v1.png)：512×512，正面提取后旋转 35°，便于单格辨认。
- [可编辑 Blender 模型](../../SourceAssets/MagicScroll5080_20260911/magic_scroll_lod0_editable.blend)
- [游戏用 GLB](../../SourceAssets/MagicScroll5080_20260911/Delivery/magic_scroll.glb)
- [实际游戏模型截图](../../Saved/MagicScrollModelInGame.png)
- [实际背包截图](../../Saved/MagicScrollInventory.png)
- [完整来源、参数及处理说明](../../SourceAssets/MagicScroll5080_20260911/provenance.md)

5080 原始几何 6,677,298 三角面；带贴图母版 95,091；游戏版 19,999。实际执行约 118 秒，不含排队。512、12/16/12、Euler、2K，回执、完整工作流、历史、远端散列和原始文件均保留。游戏尺寸高 24 cm，宽/深约 6.4/7.0 cm。绳子微细编织纹理没有逐根重建，不宣称与参考图逐像素一致。

## UE 接入

`/Game/Items/MagicScroll/magic_scroll/SM_magic_scroll`，颜色、粗糙度、金属度、烘焙法线均连接，FBX 保留法线与切线，关闭 Nanite。`ColdSteelPickupConsumable.cpp` 将上述四种卷轴映射到共享模型，沿用已有刚体、重力、碰撞和拾取逻辑。增加对应 AlwaysCook 目录。

`items.json` 绑定新图标；旧实例重载时只刷新 `icon` / `ue_icon`，通过原有 A/B 校验存档事务保存，其余物品数据保持原样。没有向用户正式存档额外发放卷轴。

## 验收

- 原生编译通过：`Saved/MagicScrollBuild.txt`，模块后缀 `9111142`。
- 导入脚本输出 `MAGIC_SCROLL_IMPORT_PASS`，见 `Saved/MagicScrollImport.log` / `MagicScrollImport.json`。命令行退出码为 1，来自现有 GameFeatureData 配置和 8000 端口占用；无本脚本 Python 异常。未将退出码写为全工程通过。
- 独立真实游戏运行 `-MagicScrollAudit -ColdSteelProfile=MagicScrollAsset20260911B`：**44 项通过，0 失败**，见 `Saved/MagicScrollAuditB.log`。包含四种旧卷轴实例图标刷新、效果/数量保持、模型加载、自由下落、地面落稳、位置/旋转保存重载、瞄准拾取、数量及拾取后持久化。首轮 A 也为 44/0。
- 已查看最终 UE 模型及背包截图，无卷轴材质编译失败。模型截图为停止物理后的正立材质展示；重力落地由独立运行检查验证，未将正立截图当成重力落地证据。
- 本次验证为编辑器宿主的独立游戏运行，未执行完整打包验收。

复现：运行 `Tools/AssetPipeline/import_magic_scroll.py` 导入，再以 `-MagicScrollAudit` 和独立 `-ColdSteelProfile` 启动项目。
