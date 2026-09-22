# 工作间定向细化 / 2026-09-21

依据用户提供的工作间实景截图，完成“移除工作台管道、细化左侧工具柜、中间改为公式白板、细化右侧货架”四项修改。已保存至 `/Game/GameMaps/L_Dungeon_Prototype`，编辑器视角位于工作间入口。未进行游戏、碰撞、性能测试或截图渲染，实际效果由用户查看。

## 场景变化

- **工作台管道**：删除 `DGN_AV2_Workshop_Bypass` 大阀门管组；整理上方服务管道，取消朝工作台悬下的支路，保留沿墙和顶棚的连续路线。相邻电线管避开白板。
- **左侧工具柜**：抽屉面转向入口，使用分离的薄板柜体、六层抽屉面板和间隙。补拉手、锁孔、紧固件、侧面百叶、推把、脚轮支架与轮轴；一层抽屉略拉开，内有套筒。上表面补防滑垫、浅盘、垫圈和卡尺形工具，磨损集中在抽屉边缘及接触位置。
- **中间白板**：删除原 `DGN_AV2_Workshop_Electrical` 板状电柜，改为约 1.84 × 1.14 米的壁挂白板。铝框、角套、紧固件、笔槽、三支笔、磁扣及板擦为独立形体。板面为原创图文贴图，包含水泵流量、扬程功率、电机转速/转矩计算与简化水路图，并加轻微擦除残痕。
- **右侧货架**：立柱增加实际矩形孔隙、角钢截面、底脚和紧固件；层板增加折边与下方支撑，背侧补交叉撑。货物改为带标签的开口料盒、轴承和紧固件、滤芯、纸箱及盘线，保留空档。

白板示例数字统一为 `Q = 3.6 m³/h`、`D = 50 mm`、`H = 12 m`、效率 `0.62`；配套电机 `1450 rpm`、转矩 `1.25 N m`。板书使用 `pi/rho/eta` 等可读拉丁写法。图文作为环境叙事，不接入交互玩法。

## 制作与接入

- 原创本地 Blender 几何和程序化 PBR 表面；本轮未调用 5080 或新购/下载 Fab 素材。
- 9 个网格组、9 个独立材质；包括柜体、柜体五金、局部磨损、标签、货架、货物、白板框、板面和服务管线。
- 替换 5 个既有 Actor 的网格引用，增加 4 个细节 Actor，删除 2 个用户指定的旧物件。旧网格资产及修改前的路径和变换记录保留。
- 所有修改的 Actor 和组件显式调用 `modify()`，随后保存关卡及其需保存的外部 Actor 包。
- 新目录：`/Game/Dungeons/AtmosphereV2/RoomInteriors/WorkshopDetail/`。
- 没有改变遗迹、走廊、照明、已有拆修电机或运行时随机生成器。
- V2 安装入口追加本轮阶段，未来全量重建会再次应用这些修改；本轮没有运行全量重建。

## 可编辑交付与回执

根目录：`SourceAssets/DungeonWorkshopDetail20260921/`。

- `Authored/DungeonWorkshopDetail.blend`：本轮独立可编辑资产与已打包材质图。
- `Authored/DungeonRooms_WithWorkshopDetails.blend`：承接上一轮 Fab 土石装配的完整源副本；旧替换物件在此副本隐藏保留。
- `Authored/manifest.json`、`material-manifest.json`：网格、材质与场景绑定。
- `Authored/Textures/`：原创表面、2048² 白板贴图及标签图集。
- `Scripts/make_surfaces.py`、`author_workshop.py`：可重复制作来源。
- `Scripts/import_workshop.py`、`install_workshop.py`：通过现有批次互斥桥导入/安装。
- `Receipts/workshop-inputs.json`：修改前的指定房间状态和旧物件变换。
- `Receipts/asset-import.json`：`assets_saved`，9 个网格、9 个材质。
- `Receipts/scene-install.json`：18:47:59 保存，`map_saved`。

保存和导入回执不代表视觉、通行或性能验收；本轮未启动相关测试。
