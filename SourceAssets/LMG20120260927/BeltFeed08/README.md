# 201 弹箱供弹与开盖换弹 — BeltFeed08

> 发布说明：此页保留当时制作记录；本机模型、回执与图片不公开，已退役资料从 trash 恢复。当前恢复入口见 [201 发布记录](../../../Docs/Weapons/lmg201-publication-20261001.md)。

**动作已被用户否定。** 本版两条弹箱换弹的手臂求解造成扭曲，不再作为动作模板。后续使用 PKMDirect09（本机历史资料：`SourceAssets/LMG20120260927/PKMDirect09/README.md`） 直接复用项目内 PKM 原生旋转轨道；此目录继续保留模型及机构来源。下面是上一轮历史制作记录，不能据此宣称手部获得认可。

用户已指定：沿用项目内认可的 PKM 换弹动作，适配 201 骨骼与接触点，并把弹药箱改造件一并接入枪匠。

## 制作内容

- 原先顶盖表面虽然是独立作者对象，但绑定在 `WPN_root`，不能开合。本版增加 `LMG201_Cover`，将顶盖、冠面、侧边和盖锁随盖绑定；前铰链、后方独立导轨与机械瞄具保留原位置。
- 机匣顶部制作可见开口、浅供弹面和上盖内表面。它们是游戏美术表现，不是内部机械设计图。
- 复用当前安装的 PKM 弹箱和弹链表面及 UV，缩放、平移至 201 接口，制作旧箱／新箱、旧链／新链独立骨骼与材质区。运行配色接续 201 枪体涂层、五金和铜色弹药。
- 使用独立骨架，原共享骨架不改。原生 V7 手臂从当前 201 UE 网格直接复制，按骨名重映射新增骨架索引；保留 Skin07 蒙皮及原 12 个动作，包括战术冲刺收手。
- 两条弹箱换弹直接取当前 PKM UE 压缩动作的 120 Hz 姿态，保留动作节奏、手指关节姿态及双手分工，适配 201 上盖、弹箱、弹链接触。前臂沿 Skin07 扭转分配，空仓拉栓尾段使用当前 201 右侧拉柄动作。

## 游戏接入

枪匠新增 `magazine` 槽：`false` 为原厂 30 发弹匣，`lmg201_ammo_box` 为 100 发弹箱。100 发是本轮游戏配置，非对实枪容量的资料结论。

弹箱的普通／空仓换弹基准分别为 **6.5 / 6.6 秒**。枪匠属性和运行时使用同一倍率；技能等既有换弹加成继续作用于整条动作。原厂弹匣保持原换弹动作和时长。

| 接触阶段 | 普通换弹源时间 | 空仓换弹源时间 |
| --- | ---: | ---: |
| 开盖 | 0.65 | 0.65 |
| 提起剩余弹链 | 1.65 | 省略 |
| 取出旧箱 | 2.60 | 1.70 |
| 插入新箱、提交弹药 | 4.35 | 3.45 |
| 铺放弹链 | 5.10 | 4.20 |
| 合盖 | 5.72 | 4.82 |
| 拉柄移动／后止点／前推／前止点 | — | 5.13 / 5.36 / 5.48 / 5.82 |

机械音效复用项目内 PKM 现有开盖、换箱、铺链、合盖与拉柄声音，按动作源时间调度。装箱后被打断的换弹使用既有持久化待完成状态，继续铺链／合盖或拉栓，不重复提交弹药。

弹箱模式隐藏整个原厂弹匣及内表面；旧、新箱链在对应交接时刻显隐。原厂模式隐藏弹箱和弹链。枪匠草稿只影响外观，确认后的选项驱动容量与动作。库存图标、枪匠预览和掉落枪使用相同网格与配件状态。灰阶改造图标新增分类、原厂弹匣和弹箱三张，PNG 与 UE Texture 均已保存。

本轮制作范围是双供弹外观、换弹动作及改造接入，没有新增 PKM 的运行时抛链物理系统。

## 作者源与已保存资产

- 最终可编辑母版：`LMG201_BeltFeed_Animated.blend`。包含最终机匣开口、拆分表面和 14 条动作。
- `LMG201_BeltFeed_Editable.blend` 是开口最终裁切前的中间母版；后续修改优先打开 Animated 母版。
- 导出：`Exports/SK_LMG201_BeltFeed.fbx` 与 `Exports/A_LMG201_*.fbx`。
- 主网格：`/Game/Weapons/LMG201/BeltFeed08/SK_LMG201_BeltFeed`。
- 独立骨架：`/Game/Weapons/LMG201/BeltFeed08/SK_LMG201_FeedSkeleton`，兼容原生手臂公共骨架。
- 动作：`/Game/Weapons/LMG201/BeltFeed08/Animations/A_LMG201_*`，新增 `reload_belt` 和 `reload_belt_empty`。
- 原有独立瞄具、脚架、枪口及光学配件继续引用 `Production20260927`。
- PKM 动作来源：`/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_reload`、`A_PKM_reload_empty`；网格来源 `Accessories14/SK_PKM_Manny_Modular`。读取记录为 `pkm_installed_donor.json`，导出原件为 `PKM_Installed_Donor.fbx`。
- 延续原项目中上述资产的来源与许可记录；本轮没有重新下载第三方模型或提交 Meshy 生成。

`import_receipt.json` 记录主网格、骨架、8 个新材质和 14 个动作的实际保存结果；`skeleton_finish_receipt.json` 记录私人骨架兼容关系保存；`icon_import_receipt.json` 记录三张配件图标保存。

## 后台交付状态

当前模型、骨架、动作、材质、图标均已后台导入保存，枪匠配置与 C++ 接入源码已落盘；常规 `FPSGAMEEditor Win64 Development` 构建成功，记录为 `build_console_02.log`。

首轮常规构建在另一个功能的 `SteelGauntletPoseNode.cpp` 中因缺少 `SteelGauntletPoseCurves.inl` 中止，记录为 `build_console_01.log`；该生成文件随后已出现，重新构建成功。本轮没有修改该处并行工作。最终交付状态见 `DELIVERY.json`。

依照用户规则，本轮没有打开 UE GUI、运行游戏、追加视觉验收或玩法测试。导入成功不代表接触、遮挡或动作观感已获用户验收。

## 重制入口

1. `read_pkm_donor.py` 读取当前已安装的 PKM 源，仅当用户要求更换供体时重新读取。
2. `author_model.py` → `author_motion.py` → `finalize_model.py` 依次生成私有机构、适配动作及最终开口表面。
3. `import_assets.py` 将模型与动作导入私有目录，保留原生 UE 手臂。完成记录支持中断续导；完整重制后应另存旧回执再重建，不复用旧完成标记跳过导入。
4. `author_icons.py` 制作灰阶图标；`import_icons.py` 同步 PNG 和 Texture。
5. `configure_catalog.py` 是本轮目录配置写入记录；不作为启动时脚本执行。
6. 后台导入沿用 `../Hands03/Run-Import.ps1` 的命名互斥和 GUI 占用约束，原生构建使用 `Tools/Build/Build-Editor.ps1`。
