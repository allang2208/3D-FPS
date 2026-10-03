# 登山包骨骼挂载（2026-10-02）

> 2026-10-03 修正：下文为 Manny 初版制作记录，旧挂载参数不再用于 Jason。
> 原 OBJ 提取时多反转了一次三角序，且挂载忽略了 UE 导入后的 Y 轴反射。
> 当前采用修正面朝向的静态图标源与 Jason 肩背蒙皮的骨骼背包；制作和恢复入口见
> `Docs/JasonEquipmentRepair20261003.md`，发布配置由 `Tools/PlayerBody/publish_jason_equipment.py` 更新。

Fab/Megascan「Soviet Military Backpack」接入第三人称躯体：装备 `ue_mountain_backpack`（装备槽 14）时
在第三人称模式下挂到 Manny `spine_03` 骨骼。

## 源与产物

| 项 | 位置 |
| --- | --- |
| 源 GLB | `D:\FPS3D\VaultCache\FabLibrary\Soviet_Military_Backpack_...\glb\russianmilitarybackpack.glb`（68MB，内嵌 4K PBR） |
| 提取 | `extract_glb.py`：stdlib 解析 GLB → `soviet_backpack.obj`（cm、Z-up、高 56cm 烘焙缩放、翻转手性三角序）+ 3 PNG |
| 导入 | `build_backpack.py`（`run_ue.ps1 -Script`）：`/Game/Characters/SovietBackpack20261002/` 下 SM + M_SovietBackpack + T_BaseColor/Normal/MR |
| 材质 | BaseColor→BC、Normal（TC_NORMALMAP）、MR 纹理 G→Roughness、B→Metallic（glTF 打包约定） |

## 贴合方案（GitHub 调研结论）

刚性背包的主流做法＝**骨骼 socket 挂静态网格**（Weber Systems 等框架同款：BackpackSocket + StaticMesh），
背带布料模拟/LeaderPose 蒙皮是带肩带形变需求时的升级路径，刚性包不需要。本项目实现为
`player_body.json` → `outfits.<item>` 条目扩展：

```json
"ue_mountain_backpack": {
  "world_static_mesh": "...SM_SovietBackpack...", "attach_bone": "spine_03",
  "attach_location": [0,-30.34,9.07], "attach_rotation": [0,0,3.59], "attach_scale": [1,1,1]
}
```

偏移求解：`rel = inverse(spine_03 组件空间参考姿态) * 期望位姿`（期望：组件空间 y=-19 背面外、
z=122 包体中心、面向 +Y 与角色同向）。`FPSPlayerBodyComponent::ApplyOutfit` 新增
`world_static_mesh`/`attach_*` 字段支持，走 `OutfitStaticMeshes` 数组参与显隐/阴影策略
（第一人称 OwnerNoSee，第三人称可见）。

## 装备栏图标

背包图标走 `UColdSteelWeaponIcons` 实时渲染通道（与材料拾取物同款的静态网格通道，
不画单独贴图）：

- `FPSBodyEquipment::StaticOutfitMesh(Definition)` 解析 `player_body.json` 的
  `outfits.<def>.world_static_mesh` —— 图标棚与身体挂载共用同一显示源。
- `UColdSteelWeaponIcons::Supports` 对任何带 `world_static_mesh` 的装备自动为真；
  `Prepare` 路由到 `ColdSteelEquipmentIcon.cpp::PrepareEquipment`（`MaterialMesh`
  组件 + 3/4 展示角 yaw30/pitch22 + 正交 91% 填充 + `SCS_SceneColorHDR` 透明底）。
- 目录底图：`Tools/UI/build_weapon_catalog_icons.ps1 -Definitions ue_mountain_backpack`
  → `Content/ColdSteelData/Icons/ue_mountain_backpack.png`（320×320）。
- `items.json` 同步 `ue_icon` 供快捷栏/工具提示等非 Supports 通道读取；`icon_fallback`
  保留为最终兜底。
- 取景细节：旋转后 AABB 会让圆角装备的填充率只到约七成；`PrepareEquipment` 直接遍历
  LOD0 顶点投到相机平面取真实剪影（CPU 顶点缓冲不可得时退回 AABB）。
- 2026-10-02 出图验收：`Icons/ue_mountain_backpack.png` 320×320 RGBA 透明底，
  剪影 (16,14)-(301,310)，垂直填充 0.93 / 水平 0.89，边缘无裁切，Megascan PBR 正常。

## 迭代

- 改偏移：直接改 `player_body.json` 的 `attach_*`（位置 [x,y,z]、旋转 [pitch,yaw,roll]、缩放），重启进程生效。
- 换模型：重跑 `extract_glb.py` + `build_backpack.py`，然后重跑上图标命令。
- 正反判断：若背带朝外了，`attach_rotation` 的 yaw 加 180。

## 挂载修正（2026-10-02 第二轮）

首版参数因两处错误跑偏：des.rotation 猜成 yaw+90（把 +Y 背带面甩到侧面），且
one.inverse()*des 在此 Python API 里语序与 C++ 相反——正确骨骼相对变换是
des.make_relative(bone)（或 des * bone.inverse()，已用 rel*bone==des 实测验证）。

实测骨架约定（SKM_Manny_PlayerSkin 参考姿态，组件空间）：面朝 +Y（ball_l 在
foot_l 的 +Y），背为 -Y，左右为 ±X（hand_r 在 -X）。spine_03 位于 (0,4.3,113.4)，
自身旋转 (p,y,r)=(86.4,-90,-90)。

背包网格轴：+Z 上、X 横向、-Y 外侧正面（7277 顶点满幅壳层）、+Y 背带面（1838 顶点
集中凸起）。贴背平面在网格 +Y≈+4~8（顶点密度分界）。

最终：des 无旋转、包心组件空间 (0,-13,125)，解得
attach_location=[12.64,-16.49,0]、attach_rotation(pitch,yaw,roll)=[-90,3.59,0]。

背带从包顶 +Y 探向身体（顶点极端 +27.4 → 组件 y≈+14，越过肩线压到胸前），
包顶 z≈152 与锁骨齐平——形成背带搭肩效果。微调改 player_body.json 即可，
JSON 运行时直读不用重编。
