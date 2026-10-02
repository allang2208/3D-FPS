# 背包装备：字段合同与夹层尺寸约定（2026-10-01）

适用于"背包装备"类物品（equipSlot=背包槽）的代码接入与新装备配置。占位阶段不做建模/贴图（无 `ue_icon` 时背包卡片显示名字文本）；资产制作后续走本技能的写实图标流程。

## 装备槽与字段合同

- `equipSlot:"backpack"` 只能进装备栏 14 号槽"背包装备"（`ColdSteelInventoryRules.cpp::CanEquip`，Keys[14]="backpack"）；`grid_w/grid_h` 是物品自身在背包里的占格（两代背包都是 3×3）。
- **主背包扩格**：`bagExtraCells`＝扩展格数，每 18 格撑出一行（`BagRows`＝4+extra/18）。"加一横列"就是 `bagExtraCells:18`（72→90）。
- **夹层尺寸约定＝长×宽（列×行）**：`bagCompartmentColumns`（横向格数，上限 18＝抽屉宽度口径）×`bagCompartmentRows`（纵向格数，上限 24）。**缺省 6×6**；`bagCompartmentCells` 只作"是否定义夹层"的开关（缺失或 ≤0＝无夹层），**容量一律＝列×行**，不再单独维护一个总数——用户口径："7×6 的背包，夹层横向七格、纵向六格"。
- 容量与网格全部由**装备中的**背包派生（`ColdSteelInventory::CompartmentGridOf/CompartmentGrid/BagRows`，扫 14 号槽读其 Data）；卸下背包＝夹层消失，运行中动态伸缩。
- **卸下规则（统一判据）**：卸下/换装背包时，容量收缩后所有物品必须仍能存放——扩展格里放不进新行数的物品随**同一事务**自动回落重排（优先落回原列底部，可堆叠先并堆），夹层里放不进新网格的物品自动搬进背包；任何一步装不下（连同放回的背包本体）＝"背包空间不足，无法卸下背包装备"，整体拒绝不发布半成品。即"无法存放 ⇒ 无法卸下"，能自动收纳就不打扰玩家。丢弃/存仓库装备中的背包仍一律拒绝（先清空）——这两条路背包彻底离开随身物品域，不做自动收纳。

## 现有两代背包

| 物品 | 主背包 | 夹层（长×宽） |
|---|---|---|
| `ue_portable_backpack` 便携背包 | +18（1 行，72→90） | 6×6=36（字段省略走缺省） |
| `ue_mountain_backpack` 登山包 | +18（1 行，72→90） | 5×6=30（显式 `bagCompartmentColumns:5,bagCompartmentRows:6`） |

## 占位物品定义模板

```json
"ue_xxx_backpack": {
  "id": "ue_xxx_backpack", "name": "某某背包", "category": "equipment", "type": "背包装备",
  "equipSlot": "backpack", "rarity": "uncommon", "stack_max": 1, "maxStack": 1,
  "price": 80, "grid_w": 3, "grid_h": 3,
  "bagExtraCells": 18,
  "bagCompartmentCells": 30,
  "bagCompartmentColumns": 5, "bagCompartmentRows": 6,
  "desc": "…", "icon_fallback": "包"
}
```

改 `items.json` 后要**重启进程**才进 PIE；F6 开发面板"服装与手套"组可发放测试。

## 行为合同（已实现，勿重复造）

- 夹层＝`Place 5`，独立格空间，转移规则在 `ColdSteelCompartmentRules.cpp`（目的地 0/1/5；网格作为参数传递，占用折行 `Owner` 带显式网格重载）。
- 快捷栏把背包+夹层的同类消耗品**视为一体**：`QuickItemCount` 显示合计，`ResolveQuickItem` 按"背包→夹层"优先解析消耗目标。
- UI：夹层区块标题/计数（"X / Y 格 · N 件"）/分隔线/整理按钮与"空间背包"同款版式，网格宽度随列数伸缩靠左对齐；键盘 F 轮换进夹层站，方向键按当前列数折行。
- 校验红线：`ValidateProfile` 必须先按整表算 `BagRows/CompartmentGrid` 再逐件校验（装备栏条目可能排在夹层物品之后）；凡按 `Cell/列数` 索引行数组的扫描（占用掩码、行上界、数组大小）必须与当前网格同源，否则越界崩溃。


## 装备件挂载与图标（2026-10-02 登山包修正）

- **组件空间朝向约定（SKM_Manny_PlayerSkin 参考姿态）**：角色面朝 **+Y**（ball_l 相对 foot_l 的指向），背为 -Y，左右为 ±X；spine_03 位于 (0,4.3,113.4)，骨系自旋 (pitch,yaw,roll)=(86.4,-90,-90)。
- **UE Python unreal.Transform 的 * 是 *a 语序**（与 C++ FTransform 相反）；骨骼相对变换用 des.make_relative(bone)（= des*bone.inverse()），写完用
el*bone==des 反向验证。one.inverse()*des 算出来的不是 SetRelativeTransform 要的东西。
- **JSON 挂载**：player_body.json 的 outfits.<def> 配 world_static_mesh+ttach_bone+ttach_location+ttach_rotation[pitch,yaw,roll]+ttach_scale；运行时 FPSBodyEquipment::ApplyOutfit 建 UStaticMeshComponent 挂骨（OutfitStaticMeshes）。
- **包体正/反面判定用顶点壳层密度**：满幅大平面=正面盖（苏联包 -Y 面 7277 顶点），集中凸起=背带面（+Y 面 1838 顶点）；贴背平面在网格 +Y≈+4~8（密度分界），背带极端 +27.4 探过肩线形成搭肩。
- **装备件图标**：FPSBodyEquipment::StaticOutfitMesh 读 world_static_mesh，Supports() 对配了该字段的装备自动成立；PrepareEquipment（ColdSteelEquipmentIcon.cpp）正面直拍 yaw-90、顶点剪影投影取景（圆角物体 AABB 取景只到 ~69% 填充，顶点投影到 91%+）。
