# 女神石像套件导入：同作者 5 件（2026-09-22）

用户在同作者（noe-3d.at）作品里继续找可商用的神像，本轮**只下载并导入为资产，不摆放**。案例目录：[`SourceAssets/DungeonStatueSet20260922`](../../SourceAssets/DungeonStatueSet20260922/README.md)。已接入的 Diana 单独记录在 [女神石像接入](goddess-statue-integration-20260922.md)。

## 1. 筛选

用 Sketchfab Data API v3 的 `user` + `q` 组合检索扫作者全目录：

| 阶段 | 数量 |
| --- | --- |
| 作者目录（翻页取回并去重） | 819 件 |
| 可下载且可商用（CC0 / CC-BY） | 75 件 |
| 神像／女性像题材（24 个关键词定向检索） | 24 件 |
| **选定** | **5 件** |

选定 5 件：**Venus**（CC0）、**Flora**（CC-BY）、**Muse**（CC-BY）、**Magna-Mater-Brunnen**（CC0）、**Barockstatue**（CC-BY）。

未纳入的说明：同作者另有 **5 件 CC0 斯芬克斯**（女首狮身，非神祇）与多处**群像**（`Allegorie - Feuer/Wasser`、`Quellnymphen`、`Herkules und Kalliope`、`Ehrengrab Johannes Benk` 等），以及男性/名人像（`Rossbändiger`、`Johann-Strauß-Denkmal`），题材不是单尊女神，留作后续备用。作者目录里绝大多数是动物扫描、墓碑与圣人像，且 CC-BY-NC 占多数（246 件），可商用比例不高。

## 2. 下载

- 鉴权与链接方式同 Diana：[数据 API 取预签名链接 + **必须显式走系统代理**](../../SourceAssets/DungeonStatueSet20260922/PROVENANCE.md)（`curl` 不读 WinINET 设置；直连 20–36 KB/s，走 `127.0.0.1:7897` 为 1.5–10 MB/s）。
- source + glb 共 10 个包、约 1.3 GB，**尺寸全部与 API 申报值一致**，SHA-256 记入 `Receipts/download.json`。
- 5 件的原包结构一致：`<Name>_C.obj` + `.mtl` + **8192² 漫反射图集**；导入用 source 包里的原图。

## 3. 加工与朝向（本轮主要工作量）

| 步骤 | 说明 |
| --- | --- |
| 源检查 | 逐件导入 OBJ、统计三角面（与 Sketchfab 申报值**完全一致**）、渲染四视图判断朝向与比例 |
| 立正 | Muse 的源导出**长轴沿 Y**（其余四件沿 Z）；该件需绕 X 立起 |
| 缩放与 pivot | 立像 2.0 m、坐像（大母神）1.8 m；底面中心为 pivot、底面 Z=0 |
| 朝向统一 | 全部统一到**正面朝 Blender −Y**（UE 中 yaw 0 即朝 +X，与 Diana 一致） |
| 贴图 | 8192² → 4096² PNG |
| 导出复核 | FBX 回读：三角面数与源一致、底面 Z=0、pivot 居中、法线未平面化 |

### 3.1 踩坑：OBJ 导入自带的 −180° 会让朝向整体差 180°

**现象**：按渲染判定写入 `yaw_deg` 后，`0` 与 `180` 两件的结果**完全一样**；而 `±90` 那两件生效。

**定位**：写最小实验（`Scripts/test_rotation_routes.py`，比较顶点校验和）后确认——**Blender 的 OBJ 导入器把 −180° 绕 Z 留在对象的 `rotation_euler` 上，并没有烘进网格**（基线读数 `euler=(0, 0, −180)`）。脚本随后直接覆盖 `rotation_euler` 写朝向，等于把导入自带的那 180° 丢掉或替换掉，于是所有件都整体差 180°，且 `0` 与 `180` 在数值上等价、无法区分。

**修正**：导入后先 `transform_apply(location=True, rotation=True, scale=True)` 把导入变换烘进网格，**再**叠加立正与朝向旋转。修正后逐件按 `from_-Y` 视图核对，五件正面都在 −Y。

**附带结论**：立正 Muse 用 +90° 会让模型头朝下（因为烘入 −180° 后它的头朝 −Y），需要 −90°；立正方向改号后朝向会再翻 180°，该件 `yaw` 取 180。

最终配置（唯一数据源 `Config/statues.json`）：

| key | 源上轴 | 立正旋转 | yaw |
| --- | --- | --- | --- |
| venus | Z | — | −90° |
| flora | Z | — | −90° |
| muse | **Y** | 绕 X **−90°** | 180° |
| magnamater | Z | — | 180° |
| baroque | Z | — | 180° |

## 4. UE 导入结果

内容根 `/Game/Dungeons/StatueSet20260922`；策略与 Diana 一致（单槽 → MI、Nanite 关闭、无简单碰撞 + 三角面碰撞、材质参数化）。回执 `Receipts/import.json`。

**编辑器内独立读回**（`Scripts/verify_assets.py`，另一个会话的编辑器开着期间用远程执行跑，未打扰对方）：

| key | 网格 | 尺寸 (cm) | 槽 0 | MI 父级 | 贴图 sRGB | Nanite | 简单碰撞 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| venus | `SM_Statue_Venus` | 56.3 × 71.8 × **200.0** | `MI_Statue_Venus` | `M_Statue_Venus` | true | false | 0 |
| flora | `SM_Statue_Flora` | 95.4 × 60.6 × **200.0** | `MI_Statue_Flora` | `M_Statue_Flora` | true | false | 0 |
| muse | `SM_Statue_Muse` | 94.9 × 85.8 × **200.0** | `MI_Statue_Muse` | `M_Statue_Muse` | true | false | 0 |
| magnamater | `SM_Statue_MagnaMater` | 98.1 × 71.8 × **180.0** | `MI_Statue_MagnaMater` | `M_Statue_MagnaMater` | true | false | 0 |
| baroque | `SM_Statue_Baroque` | 77.8 × 53.4 × **200.0** | `MI_Statue_Baroque` | `M_Statue_Baroque` | true | false | 0 |

（"简单碰撞 0" 指 box/convex/sphere/sphyl 计数全为 0，与 Diana 导入时自动带 1 个凸包不同；碰撞按三角面走。）

## 5. 命名与调度约定

- 资产名沿用 Diana 约定：`SM_Statue_*` / `M_Statue_*` / `MI_Statue_*` / `T_Statue_*_BaseColor`。
- 两个运行器（`run_headless.ps1` / `run_in_editor.ps1`）从 Diana 案例复制而来：先检查有没有别的 FPSGAME Unreal 进程、取与 MCP 桥同名的批次互斥；编辑器开着就自动改走远程执行，`-WaitForFreeEditorSeconds` 可排队等别的会话释放编辑器。
- 本轮期间另一个会话多次占用编辑器，全程未结束他人进程、未发送跨会话协调消息。

## 6. 未完成／边界

- **未摆放**：本套不写地图；关卡内目前仍只有 Diana 一件（破损支护室石质空腔）。
- 未做游戏运行、PIE、截图、性能与碰撞手感验收。
- 5 件都只有漫反射贴图，无法线／粗糙度；近看质感依靠项目光照。**Muse 源网格存在同一顶点最大 106.4° 的法线断层**（源件本身如此，非导出造成），近看可能有接缝感。
- 作者目录仍有可选素材（斯芬克斯 5 件、群像若干）未纳入。
