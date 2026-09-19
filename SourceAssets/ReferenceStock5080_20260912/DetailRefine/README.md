# 双管骨架枪托细节精修

用户接受 RTX 5080 版整体方向后，要求修开粘连细节，并按枪型匹配枪身金属。这是同一生成结果的硬表面精修：三视角输入、RTX 5080 原始模型与纹理母版仍在上级目录；最终网格按生成母版轮廓、双管位置和后架窗口尺寸重新整理拓扑，不能称作“仅减面”。

## 当前成果

- 独立管口/接环、双管间隙、贴腮板及细防滑条、夹板/斜肋、浅凹面与六角凹槽螺钉。
- 重建生成网格撕裂的后架边界，保留两个镂空窗口；分开后托金属夹层、橡胶抵肩垫与横向纹路。
- `m4/Stock_Refined_Parts.blend`、`akm/Stock_Refined_Parts.blend` 保留逐件可编辑结构。对应 `Stock_Refined_Editable.blend` 为合并导出版，`SM_SkeletonStock.fbx` 为 UE 厘米静态网格。
- 最终 UE 读回：M4 35,828 三角面，23.025 × 2.880 × 11.149 cm；AKM 40,530 三角面，23.115 × 4.100 × 11.149 cm（含独立机匣尾盖）。逐件整理重复顶点后，作者网格与 UE 面数一致，两版均为零开放边、零非流形边、零面积面为零；金属 UV 越界为零。见 `topology_uv_report.json`、`geometry_report.json` 与 `publish_report.json`。

## 逐枪材质与 UV

M4 金属槽直接引用当前机匣 `Body_001`（`/Game/Weapons/M4InfimaV3/Body_001`）；AKM 金属槽直接引用 `/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR`。这是相同的材质资产，不是按颜色近似制作的新灰色材质。所有管体、后架、接环、夹板、螺钉及 AKM 尾盖都使用该槽；贴腮垫和抵肩垫分别保留 `StockPolymer`、`StockRubber`。

各枪导出独立 UV0，映射到已查看的机匣金属区域，避免枪身图集的木材、文字和边界。M4 区间 `[.54,.73,.655,.85]`；AKM 区间 `[.055,.053,.285,.092]`，来源为本项目已许可 AKM 枪身图集的原有安装座金属取样区域。AKM 按 12 × 2.5 cm 实际纹理尺度投射，在图块边界分割几何，避免跨图集插值与长条拉伸。原层留在 UV1 供源文件参考；最终新拓扑靠几何法线表现结构，不沿用旧生成模型的粘连法线。

`m4_detail.png` / `akm_detail.png` 是同一灯光下的实际模型装配近景；另有侧视、接口近景和整枪渲染。Blender 预览使用本地枪身源材质，最终 UE 使用上述实际运行材质；两者不是同一渲染器。

## 接入与验证

候选先导入 `/Game/Weapons/ReferenceStock5080/Refined/M4` 与 `Refined/AKM`，读回尺寸和三个材质槽后，发布到既有游戏装配路径：M4 `/Game/Weapons/ReferenceStock5080/SM_SkeletonStock`，AKM `/Game/Weapons/ReferenceStock5080/AKM/SM_SkeletonStock`。使用现有 `SetGunsmithStock` 的逐枪资源/挂点分支，不改 ADS、后坐、动画时序或库存存档规则。

`refine.py` 重建；`render.py` 装配渲染；`import_refined.py` 默认候选导入，`STOCK_PUBLISH=1` 发布现有游戏路径。`import_report.json` 与 `publish_report.json` 检查金属引用与对应枪身资产相同。

运行证据写入上级 `stock5080-refined-v1/`。最终统计见本目录 `acceptance.json`，不沿用上级早期版本的 1787 项通过数字。导入日志有项目现存 GameFeatureData 配置错误导致退出码 1；Python 导入读回独立成功。此轮为资源精修，未额外修改原生玩法；尝试全项目构建时遇到并行仓库 UI/天气代码错误，记录在 `build_native*.log`，不把它们计为枪托构建通过。游戏验证使用实际可用模块并记录日志，未做打包验收。

最终验证结果：初轮精修版四进程 1444 项通过；完成逐件顶点整理、重新发布后，M4 与 AKM 从已保存实例重新加载，各完成完整装配/拆装/草稿/ADS/射击/四种换弹/图标/掉落/切枪检查，共 786 项通过，零失败。总记录 2230 项，包含连续帧挂点采样，不能理解成 2230 个独立业务案例。最终模块清单、日志与截图在 `final-runtime/`；换弹联系表和 GIF、`rifle_material_comparison.jpg` 是交付预览。
