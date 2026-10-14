# 篝火：本地其他火焰素材盘点（2026-10-12）

本地有其他现成火焰，不需要先购买新包。建议下一步优先比较 Realistic Starter VFX Pack Vol.2 的小火与 Military Trench 的篝火序列；本轮只盘点，未替换当前篝火、未修改共享原件，也未播放、渲染或视觉验收。

## 四个真实候选

| 优先级与来源 | 实际路径 | 本次读取的结构、材质和纹理 | 复用方式与限制 |
| --- | --- | --- | --- |
| 1：Realistic Starter VFX Pack Vol.2 | `/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_Fire_Small` | Cascade，LOD0 共 18 层，分为 6 组火、烟、光。`M_Fire_C` 使用 `T_Fire_F`（512×512、6×6 序列）与 `T_Fire_B`（128×128 遮罩）；另两组 `M_Fire_B` 使用 `T_Fire_D`（512×512、8×4 序列）。烟层为 8×8 图集。火焰材质均 Translucent、无折射。 | 优先复用原始序列、透明度链和少量火层到独立篝火 Niagara；无需重新画火形。不能把全部 18 层照搬为每个篝火，且近景单帧纹理分辨率有限。另一同包 `P_flamethrower` 有火、烟、火星和热扰动，喷射结构不适合原样用作篝火。 |
| 2：Military Trench | `/Game/MilitaryTrench/Particles/P_Fire` | Cascade，6 层：两层 Flames、Smoke、Embers、Sparks、Distortion。火层 `M_Fire_SubUV` → `T_Fire_SubUV`（1024×1024、6×6）和 `T_Fire_Tiled_D`（512×512）；烟为 `T_Smoke_SubUV`（1024×1024、8×8）。本次 T3D 确认了发射器实际 SubUV 尺寸。 | 自带站立火焰、烟、余烬层次，适合独立篝火来源。可保留火焰与少量烟，按现有共享调度控制表现；热扰动和火星不应默认整套复制。火焰材质是半透明序列，不是实心模型火体。 |
| 3：Dr.Game Free Spline VFX | `/Game/_SplineVFX/NS/NS_Spline_Fire` | Niagara，6 发射器：Fire_A、Smoke、Spark、Fire_B、FireBackUp、FireAdd。Fire_B／FireBackUp 的材质用 2048×2048 `T_Vfx_Stamp_FireFlame_88`／`T_Vfx_Stamp_FireFury_88`，材质参数 row=8、colum=8；其 renderer 是 1×1，因为帧动画在材质内完成。FireAdd 用 2048×2048 `T_Vfx_Stamp_GroundFireRea_1111`，renderer 11×11，帧混合开启。 | 图集可复用；整套有样条、距离场贴面、用户开关及其他 renderer，不能直接挂到篝火。项目先前曾因 Spline 火系观感更换方案，所以列为备选，不把“2K／序列帧”当作观感保证。 |
| 4：Vefects Free Fire（本地 Vault 原包 `PerfectFbbf41cddaf26V1`） | `/Game/Vefects/Free_Fire/Shared/Particles/NS_Fire_Medium`；同目录 `NS_Fire_Small` | 两系统各 6 发射器：两火舌、灰烬、灯、热扰动、火星。火舌用 `MI_VFX_Fire_01/02` → `M_VFX_Erosion`，256／512 尺寸遮罩加噪声，renderer 为 1×1。`BP_Fire` 实际引用 `NS_Fire_Big`。 | 现成系统完整，但主要仍是遮罩侵蚀火舌，和此前火把素材属于相近方案；不能声称替换后自然就写实。降低推荐级别。 |

这里只依据实际结构和依赖提出候选顺序，没有看过本轮候选在游戏中的动态效果，不将纹理名称中的 Realistic 或包名当作视觉结论。最终替换须按用户选择继续；当前火焰和石圈均保持原状。

## 其他已找到的素材

- Niagara Examples `/Game/NiagaraExamples/FX_Misc/NS_Fire`：实际 5 发射器，FlamesAndEmbers、Smoke、Lights、BaseLight、FlamesOnly。火焰 `MI_Flames` → `M_Flames`，两张 1024×1024 Hermite 噪声，1×1 renderer；烟为 8×8。不是火焰序列素材，不列为改善本次卡片观感的首选。
- EBS 原装 `/Game/EasyBuildingSystem/Effects/PS_CampFire`：4 个 Cascade 发射器；主火 4×4，火波和余烬 1×1，依赖两张 256×256 火纹理，主火 `Glow Power=50`。它确实存在，但不能仅因名为 CampFire 就判定更符合写实要求。当前石圈来自 EBS Stylized 模型，火焰候选本身不会改善该模型的低多边形轮廓。
- 引擎 NiagaraFluids 已有 `/NiagaraFluids/Templates/Gas/3D/Systems/Grid3D_Gas_Fire` 等 5 个名称含 Fire 的气体系统模板，目录和包真实存在，另有 Grid2D、Grid3D 火焰体积材质。该 3D 模板在本轮 Toolset 拓扑读取时遇到空集合，不把它计为已完整读取候选；实时网格模拟也不是现有篝火的直接替换项。
- `D:/FPS3D/VaultCache` 找到 Free Fire、Spline VFX、EBS 原包副本；`D:/FPS3D/EasyBuildingSystemV10` 也有 EBS 原件。DoorSystem 的 Vault 原包中还有 StarterContent `P_Fire`，不需要为它大规模导入整个包。`D:/FPS3D/资产` 的 ZIP 成员名检索未找到额外火焰；这只是检索结果，不代表本机所有未知目录都没有。
- 项目插件目录和已知引擎 NiagaraFluids 内容已纳入检索。未购买、领取或导入任何新包。

## 上一轮为何没有采用这些成品

上一轮先复用 EBS 篝火模型，并沿用项目已有的 RomanColumn 火把 Niagara 家族，随后用已有离线流体场制作了独立火体。此前只确认了 EBS 几个篝火模型和 `PS_CampFire` 类型，没有完整比较上述现成火焰的实际材质与序列；这是素材盘点遗漏，不能解释为“本地没有其他火焰”。

项目 9 月 22 日的火系制作记录已经包含 Realistic Vol.2、Military Trench 原始 T3D 与参数，说明这些来源早已存在。此次已重新从当前 uasset 导出，并读取当前材质、纹理及粒子结构。自制火体的完成和保存也不等于写实观感已获得认可。

## 读取证据与执行边界

- 工具：`Tools/Building/inventory_local_fire_assets.py`、`inventory_local_fire_sources.py`、`summarize_local_fire_inventory.py`。
- 当前 UE 依赖、材质、纹理和 Niagara 拓扑：`SourceAssets/Campfire20261012/local-fire-inventory.json`（255 条目录资产，9 个完成候选，另记录 1 个 NiagaraFluids 拓扑读取限制）。
- 当前 Cascade 原始文本：`SourceAssets/Campfire20261012/InventoryExports/{P_Fire_Small,P_Fire,P_Flamethrower,PS_CampFire}.t3d`；解析结果 `local-fire-cascade-profiles.json`。
- 磁盘来源与初始散列：`SourceAssets/Campfire20261012/local-fire-source-inventory.json`。
- 主工程 commandlet 在脚本执行前因 `QuadrupedAnimationTemplate.cpp:59` 的 SkeletalMeshComponent 类型转换崩溃，记录 `Saved/Campfire20261012/local-fire-inventory-cmd.log`；未改无关怪物代码。
- 随后通过 Temp 下不含 FPSGAME 模块的一次性宿主只读挂载 Content，正常读取结束，退出码 0；日志 `Saved/Campfire20261012/local-fire-inventory-isolated-cmd.log`。0 UE 错误、46 警告，包含读取器试探 renderer 索引超界及已有资产注册警告；它不是游戏运行验收。
- 没有调用资产保存、没有改任何 uasset，没有启动游戏、PIE、截图或渲染。临时宿主结束后先拆除 Content 链接再清理宿主缓存；不保留另一开发副本。
