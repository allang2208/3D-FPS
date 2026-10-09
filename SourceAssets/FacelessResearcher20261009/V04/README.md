# 研究员 M-05 V04：前襟、腰身连续变形

2026-10-09 整理补注：本文记录对应版本历史；当前组合、保留依赖及已移入 trash 的旧导出/备份路径见 [无面职员发布与恢复](../../../Docs/Publication/FacelessStaff20261009/README.md)。不要批量运行旧导入脚本覆盖当前入口。

用户于 2026-10-09 反馈 V03 身前尖刺、抖动和腰部扭曲。V03 不作为已解决穿模的版本。

## 原因与制作范围

为修复本次问题读取了原作者网格、权重及既有形态：V03 用高度和横向坐标圈定腰部，误纳入 A 姿态的部分袖子；相邻顶点修正不连续，攻击形态出现约 22 cm 的边间位移差。逐帧最近面投射、接触后逆混合蒙皮矩阵以及继承的 V01 上半身修正，会把局部接触变化放大。V01 在约 1.05 m 高度的衣身／下摆权重也存在分界。定位数据保留在 `deformation_source.json`，该文件记录旧版本，不是新版验收结果。

V04 从 V01 原始基础衣面重新制作，清除前襟、外套与附属衣片全部旧修正形态：

- 沿实际缝合拓扑平滑衣物骨骼权重，内外壁同步；根据手臂骨骼权重区分袖子，避免按坐标误选。
- 躯干与下摆使用固定的 40 × 64 控制面及固定角度／高度坐标，权重和修正均连续插值。肩袖区有平滑的解剖过渡。
- 碰撞只产生控制面的径向撑开量，再进行空间和时间平滑；不使用逐顶点换面跟随，也不再求逆混合蒙皮矩阵。
- 制作碰撞按静态解剖高度分带并限制局部投射范围，避免弯腰时把远处身体当成本片衣物的接触对象。临时低模碰撞体仅用于制作，不导出、不改实际身体。
- 门襟、口袋、胸牌与纽扣从同一外套表面绑定权重与修正；外套内外壁使用同一位移，保留实体厚度。
- 重制待机、移动、攻击、受击四组曲线，共 120 个形态。正值时间滤波和线性权重插值处理连续变化，待机／移动首末修正一致。

初次 V04 制作中整身射线曾产生不合理的大撑开量，已改为上述局部解剖分带后重新烘焙和导出；第一次导出未接入 UE。日志分别保存于 `Saved/FacelessResearcher-stable-v04.log` 和 `Saved/FacelessResearcher-stable-v04-local-contact.log`，以第二次为最终制作输出。

完整身体、裤子、鞋、衣物拓扑和 UV、材质、原骨架、动作骨骼轨道、时长、播放倍率及玩法数值保持原来源。完整身体 199621 三角面，运行组合 219505 三角面，独立衣物 19 个作者对象；无新增运行时衣物模拟或 Tick。

## 文件与接入

- 作者文件：`Authoring/FacelessResearcher_V04.blend`。
- 完整身体、独立衣物和穿衣组合：`Delivery/` 中 FBX；衣物和组合同时提供 GLB。
- 当前动作输入：`waist_source.json` 和 `Motion/`。
- 新形态曲线及制作参数：`stable_curves.json`、`stable_manifest.json`。
- 导出回执：`export_receipt.json`；UE 实际保存以 `ue_delivery.json` 为准。
- 重建链：`Tools/FacelessResearcher/export_stable_inputs_v04.py` → `tailor_stable_v04.py` → `prepare_stable_import_v04.py` → `import_stable_outfit_v04.py` / `import_stable_clothing_v04.py` → `apply_stable_v04.py`。

两份网格及四段动画使用独立 V04 名称，接入原 `BP_FacelessResearcher` 与 F6“研究员 M-05”。新的动作副本清除 V01–V03 旧衣物曲线，仅保留本版衣物修正与原骨骼动作。

已通过无界面 commandlet 导入并保存 `SK_FacelessResearcher_V04`、`SK_FacelessResearcher_Clothing_V04`、`Animations/V04/A_Researcher_{idle,walk,attack,hit}_V04`、原骨架曲线元数据及 `BP_FacelessResearcher`。`ue_delivery.json` 的 `stage` 为 `saved`，共 8 个资产；`import_process.json` 记录正常退出码 0。保存前已等待动画异步编译完成。

接入前现存编辑器已退出，首次桥接未找到节点、未执行写入；随后通过 `save_stable_v04.ps1` 取得既有 UE 桥互斥窗口，使用后台 commandlet 完成保存，未启动编辑器界面。无 C++ 改动，未启动游戏、追加测试、截图或渲染；最终效果由用户测试，不把离线制作或保存成功表述为视觉验收通过。
