# 焚化厅标牌与地面划线

用户要求先处理标识和地面划线。本批已在后台制作、导入并保存到 `/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject`。既有接灰区标牌、设备、栏杆及翻下规则继续使用。

## 布置

| 内容 | 数量 | 位置与文字 |
|---|---:|---|
| 炉号牌 | 3 | 三炉正面上方，01 / 02 / 03、「医疗废物焚化炉」、F-01 / F-02 / F-03 |
| 停用牌 | 3 | 炉号牌下方，「设备停用 / 禁止投料 · 禁止启动」 |
| 生物危害牌 | 1 | 东侧暂存位旁墙面，「医疗废物暂存 / 保持密闭 · 分类存放」及生物危害符号 |
| 入口牌 | 1 | 西侧入口门斗内壁，「废弃焚化处理厅 / 医疗废物处理区 / 非工作人员禁止进入」 |
| 投料位地面漆 | 3 处 | 各炉前约 4 × 4.77 m 范围内，黄线及对应炉号；入口留出推车通过缺口 |
| 主通道地面漆 | 1 处 | 中央东西向通道，两侧浅色边线、双向箭头、「保持通道畅通」 |
| 暂存位地面漆 | 1 处 | 东侧 2.7 × 2.5 m 预留位，黄线及「医疗废物暂存」 |
| 灰坑边缘地面漆 | 2 段 | 坑前与东侧顶面黄黑斜纹，西侧下行楼梯入口留空 |

地面漆为 UE 延迟贴花，直接作用于已有地板，没有共面薄片或额外碰撞。投射深度限定为上下各 2 cm，中心在地板上方 0.5 cm，不延伸到下沉坑底。线宽约 8.5–10 cm，带少量透明掉漆和擦痕，透出真实地板。

实体标牌在 Blender 制作，有 5 mm 牌体、7 mm 安装间隔、倒角、垫柱和紧固件。文字直接映射到实体正面，沿用上一轮铭牌闪烁修正，不叠加文字面。八块牌合为一个静态网格，保留各牌语义顶点组与可编辑副本，使用 Nanite，无碰撞。

## 源与接入

源目录：`SourceAssets/DungeonIncineratorHall20260929/Signage20260930/`。

- `Config/layout.json`：标牌位置、朝向、地面漆边界及投射深度。
- `Scripts/author_textures.py`：原创排版及掉漆纹理；Windows 字体只渲染为图像，不分发字体文件。
- `Scripts/author_signs.py`：Blender 建模、FBX 导出。
- `Authored/IncineratorHall_SignageV1.blend`：打包牌面贴图的可编辑源。
- `Authored/manifest.json`、`floor_paint.json`：模型与地面漆制作清单。
- `Scripts/install_signage.py`：导入、局部摆放与地图保存。
- UE 内容目录：`/Game/Dungeons/IncineratorHall20260929/SignageV1/`。

已保存 9 张纹理、2 个母材质、7 个地面漆材质实例、1 个标牌网格；地图新增 1 个标牌 Actor 和 7 个贴花 Actor。贴图开启流送与平均缩略层级；非二次幂作者尺寸在纹理构建时伸缩至二次幂，保留完整 UV 范围而不补边。没有新增 Tick、灯光或设备交互。

UE 5.8 的 `SetMaterialInstanceTextureParameterValue` 实现写入参数后始终返回 false；导入器不以该返回值判断失败。地面贴花按当前引擎源码的 local Z/Y 映射制作，俯投朝向为 pitch=-90、yaw=0。

重建链追加为主体 → 设备 → 铭牌/栏杆修订 → 接灰区 → 本批标识与地面漆。重复安装仅替换 `Incinerator.Signage.V1` 标签所属 Actor；首次编辑前地图备份在本批 `Backup/`。

`Receipts/install.json` 已记录 `stage=signage_and_floor_paint_saved`、`map_saved=true`；`Receipts/import-stdout-02.log` 记录保存成功和脚本正常退出。制作与保存结果不代表实机视觉验收。

未启动游戏、PIE、截图、预览渲染或测试；标牌可读性与地面划线效果由用户实机确认。
