# 病区 V5：暗红血迹与可击碎玻璃

后续修正见 [V6：各攻击入口、弹孔清理和窗框接缝](dungeon-ward-glass-frames-fix-v6-20260929.md)。下文保留 V5 制作记录；原先仅点伤害的限制已由 V6 扩展。

本轮范围：现有独立病区样板。源码、模型和材质作者版本为 `isolation_ward_breakable_glass_blood_v5_20260929`。实际构建/落盘状态以 `SourceAssets/DungeonIsolationWard20260929/Receipts/delivery.json` 为准；未执行游戏、PIE、截图、渲染或测试。

**已完成正式构建与游戏关卡接入落盘。** 普通 Editor 构建返回 Succeeded / target up to date，日志 `Saved/BuildEditor/build-20260929-141138.log`。后台 commandlet 退出码 0，`Receipts/install-v5-commandlet.log` 记录两套 V5 材质保存及 `WARD_SUBJECT_SAVED`。十二扇玻璃门 Actor、十片观察玻璃 Actor 和暗红随机血迹引用已写入样板地图。本轮没有打开编辑器或运行游戏，编译/保存结果不代表运行效果验收。

## 暗红血迹

保留 V4 的随机区域、种子、拖抹/散滴/积血轮廓和每次进入时重新生成的方式。材质换为 `M_WardProceduralBloodV5`：主体由鲜红改为暗红，多频噪声改变局部沉积厚度；较薄处略透底，浓处接近凝血色，干边粗糙度更高，只有少量内部区域保留湿润高光。无自发光，不改全局战斗血效。

## 破碎状态和命中入口

- 六个门口保留十二扇独立门。`AWardGlassDoor` 继承 `AColdSteelDoor`，继续使用原开启方向、铰链、碰撞防夹、E 交互和 6 秒回关。金属门扇改用 `SM_Ward_GlassDoorMetalV5`，玻璃成为其子组件。
- 五组观察窗保留中间金属条，拆成十片独立的 `AWardGlassWindow`。旧合并观察玻璃仅移出关卡，原资源仍留存。
- 总共二十二片 `UWardBreakableGlass`。真实武器链路保持 `ColdSteelSkills::ApplyHit → ApplyPointDamage → Actor::TakeDamage → ReceiveComponentDamage`。首次正值点伤害命中该玻璃组件时设置 Broken、隐藏完整玻璃、关闭其碰撞并触发表现。打中金属框/把手不会触发玻璃。
- 子弹命中破碎前的玻璃会结束本发弹道；破碎后后续射线通过空洞。没有额外改变穿透伤害、弹药消耗、怪物伤害或修炼公式。
- 门玻璃完整时跟随门扇，并同步现有门对 Pawn 的防夹响应。破碎后不再恢复玻璃阻挡；门框、把手、底板、横梁继续有实际碰撞，仍能交互。
- 原型属于当前单机房间，破碎状态存于本次世界实例；重新进入关卡恢复完整玻璃。没有扩展跨关卡持久存档或多人破碎复制。

## 碎片外观与预算

- 门片尺寸 142 × 250 × 1.2 cm，预制 176 个不规则 Voronoi 碎片；观察窗单片 165.5 × 128 × 1.6 cm，预制 96 个碎片。每块是闭合薄棱柱，面法线与断边颜色分开，UV1 保存片心、UV2 保存随机种子，导入使用全精度 UV。
- 受击时将玻璃组件的世界变换复制到独立表现代理，随后不再跟随门。共享材质通过 WPO 计算各片的受击扩散、旋转、重力、地面反弹、平落和淡出，法线同时旋转。
- 地面高度由每次破碎的一次偏离窗台的向下射线取得；之后使用该平面做解析反弹。碎片是装饰，不逐片查询碰撞、不阻挡 Pawn 或子弹；不会与途中所有物体做真实刚体碰撞。
- `UWardGlassFXSubsystem` 每世界最多保留六个可复用代理，超出则覆盖最早代理。每个代理一个碎片网格、一个 MID、一个 Niagara 和一个空间音源，4.1 秒后隐藏停播；无新增逐帧 Actor/Subsystem Tick。完整玻璃没有常驻碎片 RT 或模拟。
- 细碎闪片复用 `/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass`，声音复用 `/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0`。新代理拥有这一击的破碎反馈，普通命中 FX 对 `Glass.Broken` 跳过，避免空洞留下悬空弹孔或重复声音。

## NDD 复用边界与来源

借鉴用户提供的 Niagara Destruction Driver 的“完整碰撞体与装饰碎片分离、预制碎片数据驱动 WPO”思路。**本轮没有启用原 NDD 插件，也没有复制其运行时代码。** 针对这些平面玻璃，使用原创半平面 Voronoi 分割、UV 数据和解析运动，无需每片 RT。项目既有 Niagara 与音效沿用既有来源和许可。

固定提交的上游参考和 MIT 许可仍保留在 `SourceAssets/NiagaraDestructionDriver20260929/`，源码复用调查见 [前期调查](dungeon-ward-glass-destruction-options-20260929.md)。不将原创适配称为已移植完整 NDD，也不将碎片视觉称为可查询的刚体系统。

## 制作入口

- `Source/FPSGAME/Dungeons/WardBreakableGlass.h/.cpp`：玻璃组件、门/窗 Actor、碎片代理与共享上限。
- `Scripts/author_breakable_glass.py`：在既有门源上分离金属，制作两种完整片与碎片模型；可编辑文件 `Authored/WardBreakableGlassV5.blend`。
- `Scripts/GlassFragmentsV5.hlsl`、`author_glass_fracture_material.py`：碎片运动、表面与保存。
- `Scripts/BloodFinishV5.hlsl`、`author_procedural_blood.py`：暗红血迹的沉积/干湿材质。
- `Scripts/prepare_design.py`、`import_assets.py`、`install_subject.py`：配置、实际导入和地图接入；未来入池草稿包含这些 Actor/资源依赖。
- `SourceBackup/BeforeGlassBloodV5/`：前一版地图、配置、脚本与交付回执。

本轮游戏入口仍为“出征 → 废弃隔离病区 · 主体样板”，尚未加入随机房池。画面观感和实际交互由用户运行测试。
