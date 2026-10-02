# 主神空间训练靶（2026-10-02）

圆环靶面 + 木质三脚架训练靶，走 asset-model-workflow 的规则几何分支
（GeometryScript 程序化建模，经 `run_ue.ps1` 后台 commandlet/桥接执行）。

## 产物

| 资产 | 说明 |
| --- | --- |
| `/Game/Props/PracticeTarget20261002/SM_PracticeTarget` | 靶面 Ø96cm（背板 r48 木圈 + 白/红递缩圆盘叠出 5 环 + 靶心），A 字三脚架，4 材质槽，碰撞 `CTF_USE_COMPLEX_AS_SIMPLE` |

材质槽直接绑定游戏现成贴图材质（经 AssetRegistry 依赖探针确认均有 BaseColor+Normal+Roughness/ORM）：

| 槽 | 部件 | 材质 |
| --- | --- | --- |
| 0 | 木架 + 背板 | `/Game/Dungeons/AnatomyTheatre20261001/Materials/M_Theatre_Wood` |
| 1 | 白环（r45/r27 盘） | `/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_Canvas` |
| 2 | 红环（r36/r18 盘） | `/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_RedPaint` |
| 3 | 靶心（r9 盘） | `/Game/Dungeons/AtmosphereV2/RoomInteriors/Materials/M_Room_YellowPaint` |

GeometryScript primitives 用 `uv_mode=UNIFORM` 保证纹素密度一致、贴图不拉伸。
第一版纯色材质 `M_PracticeTarget_*` 已在重建时删除。

网格尺寸：包围盒 ±32.4 / ±63 / 99.6cm（x/y/z 半幅），靶心高 150cm，地面原点。

## 接入

- `AFPSPracticeTarget`（`Source/FPSGAME/Props/`）：StaticMesh(BlockAll) 承命中（枪械/箭矢 ECC_Visibility 扫掠、近战 ECC_Pawn、爆炸径向），
  命中点浮出伤害数字（上浮 48cm、1.1s 渐隐），头顶牌滚动窗口 DPS / 累计 / 击数（5s 窗口、4s 空闲重开节）。
  伤害入口是 `OnTakePointDamage`/`OnTakeRadialDamage`/`OnTakeAnyDamage`——`TakeDamage` 同帧先派类型化委托再派 Any，按 `GFrameCounter` 去重。
  命中受击晃动：按弹着方向反向倾倒的衰减正弦。
- **靶心 = 要害/暴击区**：`AFPSPracticeTarget::IsBullseyeHit` 判命中点是否落在靶心正面（网格本地 y=0/z=150、r≤10.5、x≥7；
  与靶心圆盘 r9、x 7.8..9.0 的几何同步，留容差），挂进 `ColdSteelSkills::IsCriticalHit`——步枪要害倍率与暴击伤害
  加成自动生效，爆头音效同步触发；靶心命中的浮空数字走猩红+放大配色。
- `AFPSGAMEPlayerController::SpawnHubPracticeTarget`：`DayNight_Lighting` BeginPlay 自动在出生点前方 550cm 贴地生成，
  面向出生点，`GodSpace.PracticeTarget` 标签去重。

## 重跑 / 迭代

```
& D:\FPS3D\FPSGAME\SourceAssets\WeaponSurface20260930\run_ue.ps1 `
  -Script D:\FPS3D\FPSGAME\SourceAssets\PracticeTarget20261002\build_mesh.py
```

脚本幂等：先删旧 `SM_PracticeTarget` 重建；4 个材质"已存在且有表达式→复用"，要改色/粗糙度需先删材质再跑。

## 本次记录的 API 事实（UE 5.8.2 commandlet 实测）

- `unreal.DynamicMesh()` 直接构造；`GeometryScript_Primitives.append_box/append_cylinder`，
  `GeometryScriptPrimitiveOptions.material_id` 指定段材质槽（先 `GeometryScript_Materials.enable_material_i_ids`）。
- `GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh, "/Game/path/SM_X", options)` 直接落资产。
- `unreal.OrientedBox` 的 `axis_x/y/z` 为只读；`center`/`extent_*` 可写。斜撑用 `append_box` + Rotator 变换替代。
- **UE Rotator→quaternion 对 primitive 变换的实测约定**：正 roll 把局部 +Z 倒向 +Y，正 pitch 把 +Z 倒向 -X
  （与右手定则直觉相反，按本行实测符号写腿倾斜角）。
- `DynamicMesh` 无 `release_mesh`（那是 Vibe3D ModelingService 的 handle 概念），GC 自收。
- `UTextRenderComponent` 文本可读面法线为本地 +X（顶点 TangentZ=(1,0,0)），朝相机用 look-at 旋转即可。
- `sm.set_material(i, mat)` 写静态槽；`body_setup.collision_trace_flag = CTF_USE_COMPLEX_AS_SIMPLE` 让低模直接当命中体。
