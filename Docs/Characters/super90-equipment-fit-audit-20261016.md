# Super90 源装备结构排查与贴合修复 — 2026-10-16

> 2026-10-17 更新：本文中的整件绕序重写及 ST6 扩展躯干方案已被用户否定并替换，不再作为生产基线。手套见 [本体与腕口修复](hardknuckle-cuff-repair-20261017.md)；ST6 已恢复最初衣袖并改用原生身体材质覆盖，见 [ST6 恢复记录](st6-native-body-reset-20261017.md)。以下保留为历史制作记录，保存回执不代表用户已认可效果。

按衣物标准工作流（`garment-quality-pipeline`）对 `ue_hardknuckle_gloves` 与 `ue_st6_sleeves` 做离线结构/贴合排查并落盘修复。图标合同已在同日另一文档收尾，本轮只动穿戴网格。

## 排查发现

- **ST6 衣袖 136 条 >6cm 长边**：集中在腕部手片延伸区（z≈-61~-52，权重跨 lowerarm_twist→hand→thumb_02），属源模型跨权重过渡的粗长边，为尖刺风险拓扑。
- **衣袖肩部覆盖缺口**：源衬衫为纯衣袖（无三角肌几何），肩口只到上臂中段；但 `world_covers` [0,1] 隐藏整段上臂皮肤——M4 皮肤三角肌区（z -20.5~-10.9）与 Body 皮肤 1 区（z 142~151.7）均露出，属几何缺口而非元数据问题。
- **前臂贴合**：衣袖外表在背侧前臂约 117 点没入皮下（源件即偏紧）。
- 手套结构干净（最长边 3.09cm，410 面小岛为护掌板设计）；野外手套 54 顶点 9 影响权重为源遗传，与本项无关。

## 修复（`fix_st6_sleeves.py`，M4 canonical 上执行后按原生骨骼重派生）

1. **长边细分**：原子化按面处理 1/2/3 长边、全局共享中点、权重/UV/法线插值，收敛至 ≤3.5cm 预算。
2. **最小间隙外推**：对每个衣顶按（轴心径向 + 角扇区）比较皮肤径向包络，凡衣面没入皮下即沿径向外推至皮肤 +0.22cm，共 1846 顶。
3. **三角肌肩壳**：取皮肤 region-0 三角肌网格沿自身法线外偏 1.2cm 成壳，下沿越过袖环并吸附至袖面成缝线，继承皮肤原权重（随手臂变形一致），内侧缘向躯干收 1.0cm。
4. **再细分 + 逐 profile 收尾**：延伸后再细分一次；Super90 及个别大骨架派生传输后再细分补刀，全部 ≤3.5cm。

## 验证结果（离线）

- 全 25 个 profile 结构审计干净：无非法坐标、无退化/重复面、无 >3.5cm 边、无未归一权重、无左右串权重、无零法线；`audit_equipment_structure.py` 的 components 输出改为信息项（肩壳为合法独立层，4 组件 6 开口环）。
- M4 隐藏皮肤覆盖 6982/6996（14 个残余点 gap ≤0.15cm，均处壳缘过渡）；Body 9475/9476（残余 4 点在腋下内缘 x≈16，被躯干遮挡）。
- 手腕搭接：袖端 z -55.3 与手套袖口带 -53.7~-59.7 重叠 ≥1.6cm，双覆盖。
- Blender 叠图（肩前/肩后/腕前/腕后）：肩壳贴合三角肌、袖体未膨胀、腕部设计开口由手套遮盖。

## 未做

未运行游戏、未做动画拉伸验收、未做实机视觉验收；Body/Jason 世界身观感由用户体验。审计脚本与修复脚本、覆盖检查脚本均在 `SourceAssets/BenelliM4Super9020261006/`。

## 追加：图标同步（同日）

几何变化后，`render_equipment_icons.py` 已按更新后的 `M4_ue_st6_sleeves.json` 重渲染：图标现带肩壳成完整肩部造型，成对展示、480×320、填充 0.9125 不变；手套网格未动，图标无需变化（为保持一致同批重出，图像与上轮一致）。正式 PNG 与作者副本/场景/回执均已更新。

## 追加：袖套补完为整衣（同日）

- **躯干壳**：Body_source.json 躯干+腋下带皮肤面经脊柱骨帧逆运回 M4 空间，+1.0cm 法线外偏成壳，保留领口/下摆开口；腋下皱褶区按主导骨选面补入并以皮肤法向做 0.9cm 间隙外推。canonical 23,768 顶点 / 46,905 面，衣体重心 z 94..160（Body 空间）。
- **派生**：dd_st6_torso.py 幂等重建（自动截回 6979 基线），25 档全出含 Super90（V7 骨架仅 spine_03，躯干权重全部坍缩到 spine_03，刚性随骨）；Bow 无颈骨走 spine 链兜底；缺失的非侧骨/腿骨统一兜到 spine_03。
- **结构审计**：25 档全 ok，10 开口环=领口/下摆/袖窿×2/腕口×2/肩壳分层，无长边/退化/串权重。
- **覆盖**：Body 躯干皮肤 11,725 顶点中仅 2 点距衣面 >2cm（肩缝交界、肩壳下缘内）；胸前采样有向偏移 +0.95cm、100% 在皮肤外侧。
- **引擎侧落盘**（-run=pythonscript -NullRHI 无头批次 
un_st6_shirt_batch.py）：
  - import_equipment_family.py 重建全部 25 份 SK_<profile>_ue_st6_sleeves（sha 变更触发）+ manifest 新增 Super90 条目 → SK_Super90_ue_st6_sleeves（绑定 SK_Super90_BareArmsV7，原 SK_Super90_ST6Sleeves 保留为过期资产）。
  - save_continuous_owner_shoulders.py 新增 SK_Jason_Owner_ue_st6_sleeves（肩缝 0.4 阈值切分：238 面→714，臂侧 OwnerHiddenArms 槽），Jason 世界体穿整衣。
  - SM_ue_st6_sleeves 拾取静态网格按整衣 FBX 重导（材质沿用 M_S90_sleeve_st6_generalist）。
- **目录**：items.json 改名 ST6 战术上衣、type 上衣、占格 3x3；modular_outfits part=shirt、world_covers [0,1,3,4]、rig_world_covers Jason [0,1,3,7,8,9,10,14]/Body [0,1,3,4]、owner_body_meshes+owner_body_hidden_materials{Jason:[1]}；publish_catalog.py/import_equipment_family.py 同步改，重跑不回退。
- **图标**：正视图整衣（对齐毛衣构图），RotX(-90) 正面朝相机，320×320、填充 0.9125、曝光校准 -1.82；作者副本/场景/回执更新。
- **未做**：实机穿搭观感、动画拉伸、图标观感由用户体验；compile 后旧存档实例迁移图标字段逻辑已就位。

## 追加：战术硬壳手套腕口衔接补环（同日第二轮）

- **问题**：手套腕口缘与皮肤隐藏区边界之间露出约 1-1.5cm 隐藏皮肤带（穿袖/无袖两种穿搭都会在腕部形成空洞）；腕部皮肤 sec1/sec2 分区边界在腕周各角向位置差异大（前上侧边界比袖口缘超前最多 ~5cm）。
- **修复（fix_glove_cuff.py，canonical 幂等重建 + 全档派生）**：取腕周缺口区皮肤面做成袖口环壳——按腕轴角向扇区选取 c_ax-2.2..b_ax+1.6 的皮肤面，+0.7 法线外偏、袖口侧内缘内收至 0.8×半径藏入袖口管、凹面区沿皮肤法线外推保证在皮外 +0.55；权重拷自皮肤臂骨行（限 arm/hand 骨系重归一），UV/法线/材质抄最近袖口面。canonical 6,891 顶点 / 13,490 面。
- **派生**：侧骨 frame 变换（沿用 author_equipment_family 机制），24 通用档 + Super90（v7→native warp）共 25 档重出。
- **结构审计**：25 档全部 ok；6 开口环 = 2 腕口缘 + 4 环壳缘（合法分层开口）；无长边/退化/串权重。
- **覆盖核验**：sec1/sec2 边界环 87 顶点/侧全部 <0.9cm 内有衣面；边界 1.5cm 内 374 个隐藏皮肤面 0 外露；Blender in-game 叠图（仅可见皮肤+手套）确认腕周连续，仅余袖口缘固有 V 凹口（源设计）。
- **引擎侧落盘**：run_queued_import.ps1 无头批次重建 25 份 SK_<profile>_ue_hardknuckle_gloves（含 manifest 新增 Super90 条目 → SK_Super90_ue_hardknuckle_gloves 绑 SK_Super90_BareArmsV7，原 SK_Super90_HardKnuckle 保留为过期资产）；RECIPES_SAVED 57，modular_outfits rig_meshes 25 档全指向新资产；SM_ue_hardknuckle_gloves 拾取网格按新几何 FBX 重导（GLOVE_PICKUP_SAVED）。
- **图标**：单只空右手套重渲染，320×320/0.9125，新袖口环在图标中可见；作者副本/场景/回执同步。
- **未做**：实机腕部观感与动作拉伸由用户体验。


## 追加：手臂黑构与躯干材质/领口排查修复（同日第三轮）

- **黑色结构根因**：源衣袖自身约 50% 面绕向与存储法线不一致；Body 皮肤源约 81% 躯干面绕向朝内，躯干壳继承内翻绕向/法线并把 +1.0cm 偏置推进体内；肩壳/腕带同类。UE 中这些面背面剔除/法线取反显示为黑色区块，并非贴图缺失（材质槽、贴图资产、UV 采样颜色均正常）。
- **修复链**：三个生产脚本统一加 reorient——连通域内 BFS 传播一致绕向，再按 out_ref（每顶点确定性外向参考：肩壳=臂轴径向、躯干=脊柱折线径向、腋下带=臂轴径向、腕带=腕轴径向）做带符号面积投票定向组件，最后按修正绕向重建平滑顶点法线。源面绕向不再信赖存储法线。
- **关键修正**：投票必须用 BFS 一致性之后的绕向（flip 标记作用于 fn），否则已整体翻转的组件会被误判为"已朝外"——左肩壳此前因此保持内翻。
- **领口**：颈口边界环挤出立领带（+1.3cm、内收 0.8x、上缘压平到环均值 25% 幅），权重/UV/外向参考继承边界顶点；canonical 24,181 顶点 / 47,721 面。
- **材质统一**：躯干壳 UV 不再抄 Body 皮肤 UV（落在未绘制区→黑），改按脊柱柱面展开映射到衣袖贴图布料窗 U0.05-0.30 / V0.62-0.95；全部衣面 material index 0 = sleeve_st6_generalist。
- **核验（离线）**：绕向渲染（背面染红+皮肤半透）显示躯干/肩壳/立领主体全部朝外，残红为开口缘内侧与折面合法背面；隐藏皮肤覆盖 6996/6996；25 档结构审计全 ok（10 开口环）；Body 档径向外向 77%（与 canonical 同水平，含合理内侧面）。
- **落盘**：SM_ue_st6_sleeves/SM_ue_hardknuckle_gloves 拾取 FBX 重导；装备栏贴图按整衣+立领重渲（320x320/0.9125/曝光校准）；items.json 3x3 保持；UE SK 重建走 run_st6_full_batch.py 无头批次（25 衬衫 SK + 25 手套 SK + RECIPES_SAVED 57 + 双拾取 SAVED，0 错误）。
- **owner 网格强制重建**：全量批次中 save_continuous_owner_shoulders 按源路径回执命中 ALREADY_SAVED 跳过（回执不比对内容），删除旧 SK_Jason_Owner_ue_st6_sleeves.uasset 及 LODPolicy 后单独重跑 → CONTINUOUS_OWNER_SHOULDER_SAVED（4 档 LOD 重建，38.2MB），modular_outfits owner_body_meshes/owner_body_hidden_materials{Jason:[1]} 引用保持不变。
- **未做**：实机观感、动画拉伸、领口/肩部实机验收由用户体验。

## 追加：Super90 视模整衣蒙皮爆裂修复（同日第四轮，实机截图反馈）

- **现象**：实机 FP 持枪视角整衣呈碎片状——肩/胸大片锐角三角碎片扇出（绑定态几何 dump 证明 LOD0-2 顶点/权重均正常，纯运行时绑定问题）。
- **根因**（两处叠加）：
  1. 躯干/领口共 15,583 顶点全部刚性绑到 V7 骨架的 spine_03——该视模骨架只驱动手臂链，spine 链不受姿态驱动，躯干壳被留在静态偏移位/拖离，与随手臂动的袖体之间撕成碎片。
  2. `lowerarm_aux_l/r`（1,707×2 顶点）不在 v7_to_native_warp 中，被"缺失骨→n3 兜底"错误地按脊柱帧放置——顶点落到胸区却绑在前臂骨上，形成胸-臂间碎片群。
- **依据**：同族已认可的链甲衫（Super90_ue_chainmail_shirt）权重全在 clavicle/upperarm/前臂链，零 spine 骨——V7 视模衣物躯干一律走肩带骨的既定约定。
- **修复（add_st6_torso.py / _refit_super90_st6.py）**：放置与绑定解耦——躯干仍按 spine_03 锚定帧放置（视空间内躯干形态正确，bounds 不变 [-50.9..50.9,-22.6..22.6,-63.9..-5.2]），绑定把 spine_03/pelvis/root 权重按横向位置平滑重分配到 clavicle_l/r（±20cm 窗渐变，胸中线 50/50 防中缝撕裂）；lowerarm_aux 不再吃 n3 兜底，经 old_name 回落到 lowerarm warp。Blender 渲染确认 Super90 档衣物形态完整。
- **目录字段保护**：import_equipment_family.py 尾部原以整表覆盖 items 条目，会抹掉 owner_body_meshes/owner_body_hidden_materials——改为 setdefault+update 增量写；本次被抹字段已回写。
- **落盘**：SK_Super90_ue_st6_sleeves 重建（sha 变更，仅该档重导），RECIPES_SAVED 57，0 错误。
- **未做**：实机观感由用户体验。

## Round 4 — Super90 运行时蒙皮爆炸修复 + 联机路径自查

### 症状
实机截图：整件衣物在前视图中撕成锐角三角碎片（典型蒙皮绑定错误，非几何错误）。

### 根因（两处叠加，均限 Super90 档）
1. **躯干 15,583 顶点全刚性绑 `spine_03`**：放置与绑定耦合。v7_to_native_warp 把躯干顶点写到 spine_03 锚定帧（放置正确），但运行时也绑 spine_03——V7 视模骨架只驱动手臂链，躯干被静态钉住，与随手臂动的袖体之间撕裂。
2. **`lowerarm_aux_l/r`（1,707×2 顶点）兜底错误**：不在 v7_to_native_warp 键内，被"缺失骨→spine_03"兜底按脊柱帧放置到胸区，权重却在前臂骨上——胸-臂间碎片群。
旁证：已认可 `Super90_ue_chainmail_shirt` 权重零 spine 骨、躯干全走 clavicle/upperarm；LOD0-2 dump 顶点/边界完全正常，证明纯绑定错误。

### 修复（`_refit_super90_st6.py`，幂等）
- 放置/绑定解耦：躯干仍按 spine_03 锚定帧放置（静态视空间形态不变），绑定把 spine_03/pelvis/root 权重按横向位置重分配到 `clavicle_l/r`（±20cm 平滑窗，胸中线 50/50 防中缝撕裂）。
- `lowerarm_aux` 删 n3 兜底，经 old_name 回落 lowerarm warp——顶点回前臂。
- 终态权重：15 骨全在肩臂链（clavicle 33,097 / upperarm 12,543 / lowerarm_aux 3,411 / twist 4,681 / hand 1,446 / thumb 227），**零 spine/pelvis/root**；≤4 影响、全归一；无缺失骨引用。

### 落盘
- `SK_Super90_ue_st6_sleeves` 重建（sha 变更仅该档），RECIPES_SAVED 57、0 错误；receipt sha 与 authored JSON 一致、uasset 10:51 落盘。
- `import_equipment_family.py` 尾部 items 条目改增量写（原整表覆盖会抹 `owner_body_meshes`/`owner_body_hidden_materials`）；被抹字段已回写。

### 联机路径自查结论
- **远程视角（bWorld）**：世界体 Profile rig_profile=Jason/Body → `rig_meshes` 取 SK_Jason_/SK_Body_ 变体（真脊柱链，不受本次 bug 影响）；`world_covers [0,1,3,4]`/`rig_world_covers Jason [0,1,3,7,8,9,10,14]` 隐藏皮肤——引用完整。
- **本地下半身（bLowerBody）**：`owner_body_meshes['Jason']`→`SK_Jason_Owner_ue_st6_sleeves` + `owner_body_hidden_materials['Jason']:[1]`——字段已恢复；缺该字段时代码按设计置 Shirt=nullptr 防重复手臂。
- **本地第一人称**：rig_meshes['Super90']→新资产（bOnlyOwnerSee 由源组件继承，远程不可见 FP 网格，line 371）。
- **dedicated server**：line 66 早退，不建渲染组件；装备状态经背包复制，modular_outfits 为各端静态数据，无需额外复制。
- cook：DirectoriesToAlwaysCook 已覆盖 `/Game/Characters/ModularOutfit20260924`（含 owner 子目录）。
- 已知孤儿资产（历史遗留，无引用，无害）：`SK_M870_ue_st6_sleeves`、`SK_Super90_ST6Sleeves`。M870/Super90 两视模共享 rig_profile='Super90' → 共用新资产，属既定设计。
- items.json 3×3/name/icon 完好；publish_catalog.py 不动 modular_outfits。
