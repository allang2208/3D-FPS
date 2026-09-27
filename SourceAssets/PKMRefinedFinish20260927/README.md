# PKM 枪钢与弹药箱缎面升级（2026-09-27）

参考 `ue5-weapon-workflow/references/weapon-finish.md`、`svd-finish-and-interfaces.md`、`pkm-lowpoly-mechanics.md`，读取现用 PKM 材质及 SVD RefinedFinish 实际参数后制作。

## 调整

- 移除 HandleFinish27 的 0.56–0.80 哑光钳制。保留现有枪体图集和原始金属分区，改用深色缎面：主体中心 0.37、连接座 0.36、一般配件 0.38、枪口与深色钢件 0.40、弹链钢片 0.33；原粗糙度保留局部变化，最终按范围限幅。这些是本轮制作值，尚未视觉验收。
- 独立复制 SVD 的可平铺涂层纹理为 `T_PKM_SatinFinish`，使用已有蒙皮前位置/法线插值，按 5 cm 尺度和 2.4:1 方向比例采样；微纹仅影响颜色与粗糙度。稀疏 PKM 划痕保留但降低强度，不新增颗粒法线。
- 钢件底色保留原图明暗，仅以 0.30 权重靠向中性深灰 `.025/.030/.036`；既有金属度、白色标记、非金属与光学区域继续使用原有输入。
- 新旧弹药箱共用独立军绿色漆面，颜色基准 `.047/.065/.025`；粗糙度中心 0.43。完整漆面金属度为 0，少量细划痕以一致遮罩显示露钢颜色及金属度，避免整个箱体变为裸钢。
- 每个选中干燥材质从当前 `DA_PKM_WetMaterials` 找到实际湿润对应项，在湿膜/水珠之前替换相同基础涂层。修正旧弹箱干湿基础层不同的问题；现有天气控制、正常干湿映射路径保留。
- 不重导网格，不修改 UV、结构法线、AO、骨架、动作、插槽、当前 V7 手臂或原厂分件显隐。钛色饰件、木材、聚合物、弹壳和弹头不纳入枪钢涂层。

## 执行入口

- `read_inputs.py` / `inputs.json`：本轮制作输入，实际资源绑定、节点和参考参数读取；不启动场景。
- `finish_recipe.py`、六份 HLSL：当前可编辑材质配方。
- `install_finish.py`：修改 PKM 私有材质的原涂层节点、必要材质编译、逐个保存；保留现有实例参数与运行路径，不在旧哑光输出上增加第二层。
- 修改前 `.uasset` 与旧脚本备份已归档至 `trash/weapon-bow-inspect-publication-20260927/SourceAssets/PKMRefinedFinish20260927/`；当前源保留在本目录。
- `install_receipt.json`：本批次逐材质保存记录，`complete` 为真才表示资产接入结束。

三个旧材质入口 `Finish20/build_finish.py`、`HandleFinish27/import_finish.py`、`AmmoBox30/restore_box_paint.py` 在原有制作步骤后应用本配方。Finish20 重建同时合并保留后续已有的 PKM 私有雨湿映射。它们仍是历史分阶段工具，不能作为全枪几何恢复入口顺序重跑。

## 制作与验收边界

不主动启动或重启 UE，不运行 PIE、截图、渲染、回归或自测。当前编辑器已运行时只通过项目桥批次互斥保存；没有编辑器时可用 Python commandlet 执行同一入口。无需 C++ 构建；材质编译与保存不代表游戏视觉已验收，效果由用户测试。

纹理取自工程内已使用的 SVD/A762 涂层，保留其本机资产来源边界；未新增第三方下载或公开上传。

## 本轮落盘结果

2026-09-27 18:19（本机时间）：Python commandlet 已完成，退出码 0。41 组干湿材料、共 82 份 PKM 私有母材质已执行必要编译并保存，独立细纹纹理已保存至 `/Game/Weapons/PKMLowpoly20260922/RefinedFinish20260927/Textures/T_PKM_SatinFinish`。

正式网格的新旧弹药箱仍共用 `/Game/Weapons/PKMLowpoly20260922/AmmoBox30/Materials/M_PKM_AmmoBoxPaint_Dry`；本轮无须改网格绑定或天气表路径。配件、脚架和瞄具座通过原有私有材质引用取得此次修改。

`install_receipt.json` 已记录 `complete: true`、`materials_saved: 82` 和两种弹箱实际绑定。制作日志为 `install.20260927-181843-224.log`，统一执行入口为 `run_install.ps1`。早先两次桥接分别因批次锁及编辑器已退出而未写入资产；最终使用无界面 commandlet 完成，未启动或重启交互式编辑器。

没有运行游戏、截图、渲染或测试；本次已完成材质资产落盘，观感仍由用户测试。
