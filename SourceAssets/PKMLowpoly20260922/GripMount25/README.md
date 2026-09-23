# PKM GripMount25 — 握把安装位修正

日期：2026-09-23。范围为 PKM 的 3 款后握把和 5 款前握把；用户明确要求检查并修复安装错位。

## 检查结果与修改

以当前 Motion21 枪体的 WPN_root 为统一坐标，检查实际导出的机械部件和原厂后握把，不将源文件里未导出的停放零件作为接口依据。

- 后握把：上一版按顶部安装点定位，未同时对齐握持段的中心线。以原厂握把 z=-15/-30/-50/-70 mm 的截面中心拟合握持轴，三款改造握把逐款刚性旋转和平移，不再次缩放。
- 握持段平均中心原先向枪托方向偏移：phantom 7.44 mm、balanced 14.93 mm、stable_antislip 12.11 mm。对应倾角修正为 8.14°、20.69°、12.73°，stable 同时修正约 1.04 mm 的侧偏。
- 移除不贴合 PKM 的旧金属颈圈与长垫片，重做连接座，顶部占地 29 × 44 mm。下端按各款握把真实颈部截面单独制作，消除连接座与握柄之间的缝隙。
- 前握把：握持主体保留原位置，重做安装垫片，使其连接当前枪体底部平面和配件夹座。侧倾握把原垫片长 85 mm，改为与夹座相符的 55 mm；上端高出其他夹座的 6 mm 也已收回。其余握把根据各自顶部高度调整垫片厚度。
- 保留聚合物的 UV0/UV1 和已有表面细节，连接座补倒角及加权法线，涂层 UV2 使用现有 5 cm 的贴图尺度。

## 已落盘的运行资产

8 个静态网格均已通过后台 UnrealEditor-Cmd 导入并保存到既有目录：

`/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_<key>`

key 为：`phantom_reargrip`、`balanced_reargrip`、`stable_antislip_reargrip`、`vertical`、`tactical_vertical`、`canted`、`prism`、`angled`。

导入按材质槽名称保留导入前的 Finish20 材质对象。所有导入后使用的材质均有既有干燥/湿润映射，详见 `import_receipt.json`；没有重建材质图或更改天气数据资产。

运行时仍使用 WPN_root 挂点及原有 0.01 附件缩放。枪体骨架、手部动画、换弹、战术冲刺和 Melee24 快速近战资产未替换。本次是静态模型修正，不涉及 C++ 构建。

## 交付证据和边界

- `sections.json`：修改前握持段截面及枪体底面测量。
- `neck_measurements.json`：各款握把颈部高度测量。
- `authoring.json`：实际模型修正矩阵、连接面尺寸及导出信息。
- `before_*.png` / `after_*.png`：同坐标源模型接口对照。橙色用于区分配件，**不是游戏内最终材质颜色**。
- `assets_before.json`：导入前材质、尺寸和源文件记录。
- `import_receipt.json`：8 个已保存资产、尺寸、当前材质/湿润映射和文件散列。
- `BeforeImport/`：本轮覆盖前的 8 个 uasset 备份。

已完成本次请求范围内的模型接口检查和后台导入；commandlet 正常退出，日志包含 `PKM25_ALL_GRIPS_SAVED`。没有启动交互式 UE 编辑器或运行游戏，实际第一人称显示和动作中的手部接触由用户测试。

## 后续制作入口

源文件为本目录 `SM_PKM_*.blend`，FBX 位于 `Exports/`。`author_mounts.py` 重建模型，`import_mounts.py` 保留实时材质绑定并写入原有运行资产。

不要重新运行旧 Accessories14/GripContact15 导入脚本覆盖本轮握把，也不要用旧动画导出替换现有 Reload16、Combat17、Melee24 动作。导入前按项目规则确认编辑器没有加载这些资产。
