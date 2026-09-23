# 地牢散件第一批接入（7 件，2026-09-22）

用户从 [地牢美术资产候选](dungeon-art-pass-candidates-20260922.md) 中点名 7 件，本轮完成下载、归一化、UE 导入，**统一存放到一个内容根**，未摆放。

案例目录：[`SourceAssets/DungeonArtPass20260922`](../../SourceAssets/DungeonArtPass20260922/README.md) ｜ 来源与许可：[PROVENANCE.md](../../SourceAssets/DungeonArtPass20260922/PROVENANCE.md) ｜ 署名：[ThirdPartyNotices/DUNGEON_ART_PASS.md](../../ThirdPartyNotices/DUNGEON_ART_PASS.md)

## 1. 内容根（统一存放）

```text
/Game/Dungeons/ArtPass20260922/
├── Meshes/      SM_Prop_*        9 个静态网格
├── Materials/   M_Prop_*_<Slot>  12 个母材质
│                MI_Prop_*_<Slot> 12 个材质实例
└── Textures/    T_Prop_*_<Role>  37 张（≤2048）
```

命名规则：`SM_Prop_<Name>` / `M_Prop_<Name>_<Slot>` / `MI_Prop_<Name>_<Slot>` / `T_Prop_<Name>_<Slot>_<Role>`；唯一数据源 `Config/import_spec.json`。

## 2. 导入结果（独立进程读回）

| 网格 | 尺寸 (cm) | 碰撞 | 混合 | 材质槽 |
| --- | --- | --- | --- | --- |
| `SM_Prop_Lantern` | 22.0 × 28.6 × **32.0** | 三角面 | Opaque | 1 |
| `SM_Prop_Cobweb_1` | 58.6 × 58.2 × 22.0 | **none** | **Masked · 双面** | 1 |
| `SM_Prop_Cobweb_2` | 65.7 × 54.6 × 25.4 | none | Masked · 双面 | 1 |
| `SM_Prop_Cobweb_3` | 64.0 × 57.0 × 18.3 | none | Masked · 双面 | 1 |
| `SM_Prop_StepLadder` | 83.7 × 88.0 × **110.0** | 三角面 | Opaque | 1 |
| `SM_Prop_Rope` | **45.0 × 42.8** × 12.9 | 三角面 | Opaque | 1 |
| `SM_Prop_Extinguisher` | 22.9 × 16.3 × **55.0** | 三角面 | Opaque | 1 |
| `SM_Prop_Bucket` | 30.3 × 30.1 × **30.0** | 三角面 | Opaque | **4**（Base / interior / wood / metal） |
| `SM_Prop_OilBarrel` | 62.9 × 56.5 × **88.0** | 三角面 | **Masked** | 1 |

全部：pivot 在各自底面中心、底面 Z=0、Nanite 关闭、`CTF_USE_COMPLEX_AS_SIMPLE`；回执 `Receipts/import.json`、`Receipts/verify.json`（后者为独立进程读回，含混合模式与双面标志）。

## 3. 源结构是杂的，处理方式

七件的源格式各不相同，逐件确认后按统一规则收敛：

| key | 源 | 特殊处理 |
| --- | --- | --- |
| lantern | FBX + 完整 PBR 组（含 Opacity） | Opacity 不接入（会把灯罩打成镂空） |
| cobwebs | OBJ（**无 mtl**）+ 3 组 Colour/Alpha | 材质在 UE 端按 spec 重建；**按材质拆成 3 张独立卡片**，拆后各自归零 |
| ladder | 内层 zip 里的 `Stool.fbx`（文件名是 Stool） | 只有 Diffuse + AO，粗糙度用常数 0.85 |
| rope | **只有 `Rope2.blend`，无贴图** | 材质颜色/粗糙度从 Blender 的 Principled BSDF 读出（棕绳 0.20/0.13/0.05，粗糙度 0.85） |
| extinguisher | OBJ（无 mtl）+ spec-gloss 组 | 高光图不接入，粗糙度用常数 0.7 |
| bucket | FBX，**四套材质** | 逐槽对应四套贴图 |
| barrel | FBX + Unity 风格打包图 | AlbedoTransparency 带 alpha → **Masked**；MetallicSmoothness 取 R 通道作金属度 |

## 4. 本轮踩到的坑

1. **非均匀源缩放会让"等比缩放"失效**。最初的归一化把目标比例乘到源对象自身的 scale 上；源件带非均匀 scale（ladder、bucket）时结果就偏——阶梯底面浮空 1.5 m、水桶沉到地下 2.2 cm，而且阶梯的"1.1 m 高"实际只有 0.97 m。改为**先 `transform_apply` 烘入导入变换，再测量、再施加一次纯等比缩放**后全部归零。
2. **拆分后的 pivot 留在整包坐标系**。蛛网按材质拆开后，各卡片原点偏离自身几何最多 66 cm，摆放会很难用；拆完对每片单独重新居中（不动缩放）。
3. **UE 重导入会把槽名 `metal ` 规范化成 `metal_`**，精确匹配会漏；槽名比较改为只保留字母数字。
4. **masked 材质的 alpha 采样节点要显式创建**：alpha 图不属于常规采样的那几个角色，只在字典里查是找不到的。
5. **Python 变量遮蔽**：循环里用 `slot_key` 当局部变量，把同名函数遮住，报 `'str' object is not callable`。

## 5. 网络环境（本轮实测）

- **API 直连**、**S3 走代理**：直连 api.sketchfab.com 约 3 s 返回；S3 直连仅 28 KB/s，走 `127.0.0.1:7897` 为 1.7 MB/s（油桶 61 MB / 4.7 秒）。
- 代理隧道到 **api** 域名会 TLS 握手失败（curl exit 35），所以两条路分开用；`fetch_props.ps1` 的 `-Proxy` 默认空，需要时显式传入。
- **签名链接 300 秒过期**：一次中断后重试全部 403，表现为"文件 0 字节不动"。排查时先看 HTTP 状态，别误判为网络慢。

## 6. 未完成／边界

- **未摆放**：本轮只导入，场景里仍没有这些道具。
- 未做游戏运行、PIE、截图、性能与碰撞手感验收。
- 灯笼的玻璃（Opacity 图）与灭火器的 spec-gloss 高光未接入；需要时另做半透明/高光处理。
- 蛛网三张卡片与三组贴图的对应关系是按顺序假定的（源 OBJ 无 mtl 指明），若花纹对不上只是图案串位，不影响可用性。
- 候选清单里其余 15 件（B 组遗迹石作、C 组骨堆/烛台/麻袋等）尚未下载。
