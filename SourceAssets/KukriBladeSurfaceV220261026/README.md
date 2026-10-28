# 尼泊尔弯刀刀身材质与细节 V2

> 后续接入修复已完成：[KukriAssetRepair20261026](../KukriAssetRepair20261026/README.md)。三款刀身曾因 SurfaceV2 槽名及默认网格材质绑定而显示白膜；当前 FBX 已恢复稳定槽名，正式网格已重建并绑定本批 PBR。重导入使用修正后的 `import_surface.py`。

用户要求优化三款刀身改造件的表面材质与细节，沿用既有无数值改造及游戏接入。

## 制作内容

- 轻型迅刃：浅冷银缎面、细密定向磨纹，4.2 mm 刃口精磨区。
- 厚背重刃：中灰锻钢、微细锻造起伏，6.4 mm 宽刃口精磨区。
- 百炼均衡刃：银灰钢面、弯曲且不规则的层叠流纹，5 mm 素面刃口精磨区。
- 重新划分刀面与刃口，依据真实刃缘距离生成表面分区；清理旧纹理在外露刀根处的发黑混合区域，粗糙度与微米级法线表达细节。
- 面角法线在外露刀身处改为相邻面面积加权平滑，保留刀根接口过渡。顶点位置、三角面数量、UV0、安装坐标和原有动作数据不变。
- 每款 2K BaseColor、ORM、Normal，共九张 PBR；每款仍为 10,528 三角面、5,266 顶点。贴图可流送。
- 图标以更新后的实际模型图和认可金属框通过 imagegen 生成：灰阶、四角铆钉、银色内圆环、深灰底板、窄透明外缘；仅替换三款刀身图标。

## 接入方式

三个 StaticMesh 与九张 PBR 覆盖既有 `/Game/Weapons/Kukri20261020/BladeVariants20261026/` 对应资产；保留材质槽名和原材质绑定。三款基础材质以及九个已选符文材质实例继续引用这些贴图，原装刀身使用独立资源。

稳定选项 ID、共享图标键和模块配方不变，继续由已接入的主手、副手、双持、改造预览、背包图标与掉落装配读取。没有添加伤害、速度、耗体、范围、强化或特效加成，也没有改动玩家存档。此批没有 C++ 修改，无需重新编译。

## 作者入口

- `author_surface.py`：从旧三刀身母版制作新法线和 PBR，烘焙、导出 FBX 并保存可编辑母版。
- `Kukri_Blade_SurfaceV2_Editable.blend`、`Export/`、`Textures/`、`surfaces.json`：当前三款刀身源文件。
- `render_icon_inputs.py`、`IconInputs/`：实际图标素材生产；不是游戏验收截图。
- `Icons/`、`imagegen-receipt.json`：三张最终标准图标与生成来源。
- `import_surface.py`：通过现有互斥桥导入并保存十二个表面资产。
- `import_all.py`：同一批次先导入表面，再导入图标；无编辑器运行时可使用 `import_background.ps1`，沿用同一 UE 批次互斥并以无界面 commandlet 保存。
- `deploy_icons.py`、`import_icons.py`：发布三个共享 PNG 并保存三个同名 UE Texture2D；同步前批 `KukriFinalIntegration20261026/manifest.json` 的三张母图引用。
- `Before/`：本批替换前的精确资产副本；`Receipts/`：生产导入记录，实际落盘状态以完成回执为准。

旧刀身批次保留为造型来源；重跑旧导入后，应最后执行本批的表面导入、图标部署及图标导入，避免恢复旧表面。前批完整图标部署清单也已转向这三张新母图；直接执行前批旧导入回执不会自动更新来源，应先重新部署。

## 交付边界

只进行制作、图标资产渲染与必要导入保存；不主动启动或重启编辑器、不运行游戏或测试，不做验收渲染。游戏中的最终光照、近看质感及组合表现由用户检查。

## 实际保存状态

2026-10-26 22:07（北京时间），`Receipts/import-surface.json` 与 `Receipts/import-icons.json` 均为 `complete: true`：三个 StaticMesh、九个 PBR Texture2D、三个菜单 Texture2D 已逐包保存；三个共享 PNG 也已部署。

现有编辑器导入桥先因互斥占用而排队，取得窗口时编辑器已退出；随后在没有编辑器进程的情况下，通过同一互斥执行无界面 commandlet。本批没有启动、关闭或重启交互编辑器。

Commandlet 总退出码为 1，启动日志报告项目已有的 GameFeatureData / PrimaryAssetTypesToScan 配置错误；本批 Python 导入流程仍完整执行且两个保存回执均已完成。此处只据实际保存结果交付，不将总退出码描述为成功，也不处理无关的项目配置。原始日志见 `Receipts/import-all-background-console.log`。
