# 病区观察窗接缝 V8

用户要求继续排查观察窗上沿闪动，并参考 Skill 中的既有经验。本轮依据 `asset-model-workflow` 的硬表面接缝记录和 `ue5-debug-validation` 的实际网格取证要求，读取作者逻辑、回读现有 FBX，再从独立 UE 后台进程读取保存后的资产几何。未打开编辑器、地图、PIE 或运行游戏。

## 原因与遗漏

V7 的混凝土退让条件为 `not glass and not interactive`，因此只覆盖固定门洞，没有覆盖观察窗。五组观察窗的上、下、左、右封口仍与金属窗框内表面共面。旧 FBX 的 20 条边、共 120 个采样点均接近 0 mm 间距，与截图中的宽条带闪动相符。V6 的校对仅覆盖瓷砖和后门设备槽，没有测量混凝土封口与窗框之间的接缝。

同时发现胶条外封面与窗框内表面、中梃上下端面与胶条内表面也互相共面。网格闭合、单个网格没有重复三角面，并不能排除跨网格装配时的共面。

## 已保存修正

- 所有固定框统一采用结构开口退让规则；五组窗洞四边的混凝土向金属框实体内部退让 5 mm，底部退让限于地面以上。
- 胶条外封面嵌入金属框 3 mm，中梃上下端面嵌入胶条 3 mm，隐藏原来共面的接合端面。
- 保留窗框可见开口 3.4 × 1.33 m、材质、玻璃位置与破碎逻辑。后门 V7 的 5 mm 退让保留。
- 仅导出和重导 `SM_Ward_Walls`、`SM_Ward_Frames`、`SM_Ward_WindowGaskets`。原地图继续引用相同资源路径，无需改写地图；没有 C++ 改动或本轮 DLL 构建。

后台导入成功退出（0），`Receipts/install-v8-commandlet.log` 记录三份 `WARD_MESH_SAVED` 及 `WARD_WINDOW_REVEALS_V8_SAVED`。随后另起后台 commandlet，从磁盘重新加载 UE 资产，读取实际静态网格三角面，完成同范围复核：

| 项目 | 修正前 FBX | 修正后 FBX / 已保存 UE 资产 |
| --- | --- | --- |
| 五组窗框四边与混凝土间距 | 约 0 mm | 约 5 mm |
| 胶条外封面埋入窗框 | 0 mm | 约 3 mm |
| 中梃端面埋入胶条 | 0 mm | 约 3 mm |
| 可见窗框开口 | 3.4 × 1.33 m | 不变 |
| 两处后门的两侧与顶部间距 | 约 5 mm | 约 5 mm |
| 三份网格重复 / 零面积三角面 | 0 / 0 | 0 / 0 |

几何统计保留 UE 厘米坐标转换后的双精度数值。若先转成 Blender float32 米坐标，远离原点的极小倒角面会被检查脚本误判为零面积；已修正这处取证精度问题，未为此更改模型。

证据位于 `SourceAssets/DungeonIsolationWard20260929/`：

- `Receipts/window-reveal-v8-before.json`：旧 FBX 的定位依据。
- `Receipts/window-reveal-v8-fbx.json`：修正后的 FBX 几何复核。
- `Receipts/window-reveal-v8-ue-saved.json`：独立进程回读 UE 资产后的几何复核。
- `Receipts/window-reveal-v8-saved-triangles.json`：保存包 SHA256、材质、Nanite、碰撞设置与实际三角面数据。
- `Receipts/window-reveals-v8.json`、`Receipts/delivery.json`：落盘状态。
- `Authored/WardWindowRevealFixV8.blend`：本轮三组模型的可编辑源文件。
- `SourceBackup/BeforeWindowRevealV8/`：修改前三份 UE 资源、FBX、脚本和配置。

本轮只做用户要求的接缝几何排查。没有游戏画面或渲染验收证据，重新进入“废弃隔离病区 · 主体样板”后的视觉结果由用户确认。
