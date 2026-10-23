> 历史制作基线：以下记录 10 月 19 日的静态源。当前穿戴已升级为侧袋开口修正、六套贴身背带和有界惯性，入口见 `Tools/BackpackMotion/` 与 `Docs/Publication/Backpacks20261023/README.md`。旧图标及一次性几何试验已归档至 `trash/backpack-retired-20261023/`。

# 行军背包 ALICE 表面制作（2026-10-19）

> 2026-10-21 两侧侧袋已续修：增加窄袋口、内衬和实体包边，当前实际网格为 34,201 三角形、五个材质槽。当前源位于 `SourceAssets/BackpacksReview20261021/AliceBackpack_side_openings.blend`，导出和保存入口为 `Tools/BackpackHarness/export_alice_sides.py`、`save_alice_sides.py`。本页下面的 10-19 面数与四材质记录为历史基线；旧 OBJ 导入器已阻止覆盖当前版本。详情见 `Docs/Characters/backpacks-review-20261021.md`。

把 Fab 的 **ALICE Military Backpack - Argentinean Army** 接入 `ue_portable_backpack`，
并按 [布料与衣物表面标准](../../skills/ue5-fps-arms-animation/references/glove-clothing-surface-production.md)
补一套可烘焙的帆布 / 织带 / 皮革 / 金属表面。

## 来源与边界

| 项 | 位置 |
| --- | --- |
| Fab 缓存 | `D:\FPS3D\VaultCache\FabLibrary\ALICE_Military_Backpack_-_Argentinean_Army-a4aeb32a\obj\mochila_low_poly.obj` |
| 下载内容 | 仅 OBJ + thumbnail；**没有 MTL、没有贴图** |
| 原始网格 | 14,201 顶点 / 14,692 面；7 个材质组；UV 在位；约 4 个源单位 |
| 授权 | Fab Personal（免费档）；制作时未改动 Fab 缓存 |

最终游戏网格 **15,597 顶点 / 15,853 面**：帆布/织带/皮革拓扑不变，五金替换为真实倒角并开出四处可穿带的开口。
高模只用于法线烘焙，不进入 UE。

原始组到材质的拆分：

| 原组 | 面数 | 包装材质 |
| --- | ---: | --- |
| `LP_Mochila` 主包 | 3,242 | 帆布 |
| `LP_Tiras_Espalda` 背带 | 3,202 | 织带 |
| `LP_TirasAjuste` 调节带 | 1,624 | 织带 |
| `LP_Respaldo` / `LP_Respaldo2` 背垫 | 450 | 帆布 |
| `LP_Extras` 附件 | 1,383 | 皮革 |
| `HP_Hebillas` 五金 | 4,791 | 金属 |

## 制作链

1. `inspect_alice.py`：导入原始 OBJ，记录尺度、材质槽、UV 和世界包围盒。
2. `prepare_alice.py`：转 UE 轴向（背垫朝 +Y、五金朝 -Y），缩到 **46 cm 高**，包围盒中心为轴心；按语义合并 4 个材质槽。
3. `uv_atlas.py`：**每个材质单独 0–1 展开**；四组 UV 在 UV0 内重叠，但各自使用独立贴图。
4. `bake_alice.py`：程序化着色器 + Cycles 烘焙；本轮 **四种材质全部 4K**。
5. `extract_stitch_3d.py`：从真实几何折痕筛选缝线（角度 ≥55°、边长 ≥4 mm、同材质、排除金属），输出 3D 端点和面法线。
6. `build_highpoly_stitch.py`：在低模表面加 **3,248 枚真实缝线胶囊**（双排；单枚 3.2 × 1.1 × 0.9 mm），合成 144,612 面高模。
7. `bake_geo_normal.py`：把高模缝线几何以 **selected-to-active / tangent normal** 烘到低模 UV；Canvas/Webbing/Leather 全部 4K。
8. `build_beveled_final.py`：拆出金属，仅对 **232 条有实际长度的五金边**做 0.6 mm / 3 段倒角；修掉倒角产生的塌缩 UV 面，再把五金合回最终网格。
9. `build_buckle_openings.py`：把五金拆成 8 个独立零件，只对正面左右两枚释放扣和左右两侧的压紧扣开真实穿带口；开口贯穿扣体，保留侧扣中央的 177 面释放钮。
10. `make_stitch_masks.py`：在 4K 生成缝线与针脚遮罩。
11. `apply_4k_surface.py`：把高模法线（OpenGL 空间）与程序化织物/皮革法线相加并归一化，最后 **统一翻绿一次** 成 UE 的 DirectX 法线；同时把缝线压暗、针脚提亮、粗糙度和 AO 叠进 4K 贴图，输出 ORM。
12. `export_ue_obj.py`：先把 Blender Z-up 预转成 OBJ 的 Y-up，再 ×100 导出厘米 OBJ；UE 导入后恢复 Z-up，包围盒中心为轴心。
13. `build_alice_ue.py`：导入贴图、网格，创建 4 个材质并绑定槽位；法线和粗糙度再叠加平铺细节贴图。
14. `publish_alice.py`：写 `player_body.json` 的 `outfits.ue_portable_backpack` 和 `items.json` 的 `ue_icon`。
15. `render_icon.py`：用最终 4K 材质和倒角/开口五金透明渲染，裁切成 **320×320 RGBA** 图标；绕开此前会卡在 RHI 初始化的图标 commandlet。

## 五金倒角与开口

- 仅对长度 ≥2 mm、相邻面面积足够、夹角 ≥30° 的 **232 条五金边**倒角；不是全网格倒角。
- 倒角 **0.6 mm、3 段**；金属面从 4,790 增至 5,983。
- 倒角后 203 个 UV 面积塌缩面，按最近有效 UV 修复；没有删除大块几何制造孔洞。
- 五金现在是**真实轮廓倒角**，不再只靠法线贴图假装圆角；UV 仍使用原金属图集，倒角面继承相邻 UV。
- 共开 **4 处真实穿带口**，都贯穿扣体：
  - 正面左右两枚释放扣：12 × 7 mm 圆角窗口。
  - 左右两侧压紧扣：14 × 14 mm 圆角穿带口；中央保留原有的 177 面释放钮，形成“按片在框内”的开启结构。
- 开口后金属面 5,952，最终整包 **15,853 面 / 15,597 顶点**；开口内壁按最近有效金属 UV 修复，最终 UV 坏面 0。
- 金属法线仍为 4K 程序化拉丝/磨亮，没有叠加高模倒角法线，避免和真实倒角/开口重复。
- 这是**静态可穿带结构**，没有做扣具开合动画、弹簧或可交互绑定；视觉上能读出如何脱扣，但游戏里不会真的弹开。

## 法线处理

- 高模缝线法线是 **切线空间**，由低模 UV/tangent 烘焙；没有用 object-space 法线冒充。
- Blender 烘焙输出 **OpenGL**；在 `apply_4k_surface.py` 中与同样为 OpenGL 的程序化法线合成，最后只翻一次 G，写成 UE 使用的 **DirectX** `T_Alice_<材质>_Normal.png`。
- 同时保留 `T_Alice_<材质>_Normal_GL.png` 供 Blender 预览；两者 G 通道严格互补（和为 255）。
- 高模权重：Canvas 0.90、Webbing 0.90、Leather 0.82；Metal 0，五金靠真实倒角几何。
- 平铺 **DetailNormal** 仍在 UE 材质里按 5/7/5/4 次采样，补织纹和皮革粒面。

## 表面配方

| 区域 | 基础色（sRGB 均值） | 粗糙度 | 正常/凹凸 |
| --- | --- | --- | --- |
| 帆布 | 约 55/57/44，橄榄灰 | 约 0.54 | 经纬织纹 + 高模缝线 + 细节法线 |
| 织带 | 约 50/50/40，压暗橄榄 | 约 0.43 | 高频织纹 + 双排针脚 |
| 皮革 | 约 65/45/40，深棕 | 约 0.40 | 粒面 + 高模缝线 |
| 金属 | 约 70/72/73，发黑钢 | 约 0.20 | 真实倒角 + 4K 拉丝/磨亮；Metallic=1 |

- AO、粗糙度、金属度写入 **ORM**（R/G/B）；BaseColor 为 sRGB，Normal 为 DX 切线空间。
- 四种材质全部 **4K** BaseColor/Normal/ORM；DetailNormal/DetailRoughness 为 1K 可平铺细节。
- 缝线遮罩由几何折痕推断：Canvas 84 段、Webbing 618 段、Leather 128 段；不是原厂纸样。
- 干净底图备份在 `Textures/Base_4k_clean`；上一轮增强版在 `Textures/Base_v2_2k`；高模法线在 `Textures/GeoNormal`。
- 若重新跑 4K 烘焙，先删除 `Textures/Base_4k_clean`，否则 `apply_4k_surface.py` 会优先复用旧干净底图。

## UE 资产

- 网格：`/Game/Characters/PortableBackpackAlice20261019/SM_AliceBackpack`（15,853 面）
- 材质：`M_Alice_Canvas`、`M_Alice_Webbing`、`M_Alice_Leather`、`M_Alice_Metal`
- 贴图：`T_Alice_<区域>_BaseColor / Normal / ORM`，以及 `T_Alice_<区域>_DetailNormal / DetailRoughness`
- 高模：`AliceBackpack_highpoly.blend` 仅作烘焙源；最终倒角/开口网格在 `AliceBackpack_uv_bevel.blend`
- 网格包围盒原点 0，范围约 **48.33 × 46.0 × 39.43 cm**
- `items.json` 中物品名已改为 **行军背包**，描述同步注明正面与两侧搭扣开口。

## 挂载与图标

- `player_body.json` 的 `outfits.ue_portable_backpack` 已写入 `world_static_mesh`、`spine_03`、初始 `attach_*`。
- 初始挂载参数沿用修正后的苏联包（同轴向下）；**尚未在第三人称实测**。若前后颠倒，把 `attach_rotation` 的 yaw 加 180；位置/缩放按实际肩背关系微调。
- 图标：`Content/ColdSteelData/Icons/ue_portable_backpack.png`，本轮由最终倒角/开口网格 + 4K 材质透明渲染，裁成 **320×320 RGBA**；旧图标备份在 `SourceAssets/PortableBackpackAlice20261019/ue_portable_backpack_before_20261019.png`。
- 开口近景：`Preview/buckle_openings.png`（左侧压紧扣穿带口 + 正面释放扣窗口）。

## 质量边界

- 最终网格 15.9k 面，五金有了真实倒角轮廓和四处穿带口；帆布/织带的轮廓与厚度仍受原低模限制。
- 缝线仍只存在于法线贴图，近到极限不会有真实缝线的侧面轮廓。
- 没有做布料模拟、厚度壳或高模法线烘焙到倒角五金；五金细节来自实际倒角/开口 + 4K 程序化材质。
- 扣具开口是静态几何，没有弹簧、开合动画或交互绑定；尺寸与位置按视觉逻辑推断，不是原厂纸样。
- 4K 全材质会明显增加显存和加载体积；这是为了近景背包主动选择的质量档，不是全场景通用默认。
- 预览图是 Blender EEVEE 的检查渲染，包含 4K 底图、高模缝线、真实倒角和开口，不等于 UE 内最终光照。

## 重跑

```powershell
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\prepare_alice.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\uv_atlas.py
$env:ALICE_BAKE_RES='{"Canvas":4096,"Webbing":4096,"Leather":4096,"Metal":4096}'
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\bake_alice.py
Remove-Item Env:ALICE_BAKE_RES
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\extract_stitch_3d.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\build_highpoly_stitch.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\bake_geo_normal.py
python -X utf8 SourceAssets\PortableBackpackAlice20261019\make_stitch_masks.py
python -X utf8 SourceAssets\PortableBackpackAlice20261019\apply_4k_surface.py
python -X utf8 SourceAssets\PortableBackpackAlice20261019\make_detail_textures.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\build_beveled_final.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\build_buckle_openings.py
$env:ALICE_SRC_BLEND='D:\FPS3D\FPSGAME\SourceAssets\PortableBackpackAlice20261019\AliceBackpack_uv_bevel.blend'
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\export_ue_obj.py
Remove-Item Env:ALICE_SRC_BLEND
& SourceAssets\WeaponSurface20260930\run_ue.ps1 -Script SourceAssets\PortableBackpackAlice20261019\build_alice_ue.py
python SourceAssets\PortableBackpackAlice20261019\publish_alice.py
& 'E:\Program Files\Blender Foundation\Blender 5.1\blender.exe' -b --python SourceAssets\PortableBackpackAlice20261019\render_icon.py
```

运行/验收状态：**未测试**；按用户规则由用户自行在 PIE 与第三人称检查。
