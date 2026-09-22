# 地牢房间内部改造 / 2026-09-21

最新近景细节与表面材质：根据四张实景图修正抽屉标签层级与比例，重做洞洞板孔缘、工具及插座细节，并更新漆面、钢材、握柄与木纹材质；已接入保存，见 [表面材质与近景细节记录](dungeon-workshop-surface-details-20260921.md)。

针对 low-poly 观感的组件重建：已依照工作间概念图制作连续锻造工具、铸造台钳、角钢台架、弧面薄壳灯具与重力成形抹布；具体修改和接入阶段见 [组件重新建模记录](dungeon-workshop-component-modeling-20260921.md)。历史截图不代表此轮模型。

工作间工具与灯光后续修改：已细化台面/挂墙工具、台钳、木台面、抹布、台灯和顶灯，并重组局部照明，见 [工具、灯具与使用痕迹细化](dungeon-workshop-tools-lighting-20260921.md)。本轮未新增截图，下方历史截图不代表最新效果。

工作间后续定向修改：已按用户实景图删除工作台大管组，细化左侧工具柜，将中间旧板件替换为公式白板，并细化右侧货架，见 [工作间定向细化](dungeon-workshop-detail-20260921.md)。本轮未新增截图；下方旧截图不代表最新工作间。

后续更新：用户确认优先复用 Fab 现有素材后，遗迹土坡、坡脚砂砾、碎石及门槛衔接已替换为局部适配的扫描资产，见 [Fab 土石改造记录](dungeon-ruin-fab-earthwork-20260921.md)。本文下方的初次实装计数和四张截图保留为该调整之前的记录；原两块生成土石仍保留，但已在地图中隐藏。

用户已选定 [维修间和遗迹侧穴概念图](Previews/DungeonRoomConcepts_20260921/index.html)，本轮已按此方向制作、导入并保存到 `/Game/GameMaps/L_Dungeon_Prototype`。交付包含 37 组自制网格、2 件 5080 生成母版的 3 个摆放实例、2 处局部灯光和 4 处表面痕迹；`room-install.json` 状态为 `map_saved`。制作阶段没有运行玩法、导航或性能测试；随后按用户“截图看一下”的请求补拍了四张 UE 实景截图，见文末。最终视觉验收由用户决定。

## 范围

目标地图仍为 `/Game/GameMaps/L_Dungeon_Prototype`，只调整维修开间与遗迹侧穴。已认可的走廊结构、瓷砖自然损耗段、其他机房和末端台阶继续沿用现有版本。本轮不修改运行时随机生成器、事件、存档或战斗逻辑。

## 维修间

- 在 6 × 4.2 米开间内制作 L 形工作台，增加独立木板台面、金属支腿和纵横连接梁、脚垫、紧固件、下层收纳。
- 制作有实际孔洞的工具板，配不同形态的手工具和空挂钩；拆修电机作为台面焦点，辅以台钳、零件盘、少量罐装耗材和搭落的布。
- 增加带脚轮、分层抽屉和拉手的工具车，右侧设置浅进深备件架，填充程度有变化。
- 复用原 5080 电柜与阀门组，调整到后墙位置，补齐服务管道、卡箍、支架、线管、插座、桥架和落下的线缆。
- 光线围绕工作台组织，降低原顶部暖光强度；污迹集中在推车、工作台、收纳架及阀门附近，保留中央通行留白。

## 遗迹侧穴

- 保留 6.5 × 7.5 米边界与原破口。入口保留现代混凝土，内侧补旧砌体、埋藏的石拱顶与连续土坡。
- 局部旧石板地面低约 18 厘米，以土坡缓接现代地板；左侧较密的土石堆积向接近路线逐渐降低。
- 石拱使用现有轮廓的独立副本，移向后部略偏右；保留现有雕像资产及朝向，底部接到新的低矮破损基座。
- 增加伸缩支撑柱、底板、调节环、螺纹、钢梁、木垫和临时施工灯，线缆沿入口侧边布置。
- 移除遗迹房原顶部灯具对应的网格片段与光源效果，改用入口环境光和侧向施工灯。其他灯具的几何及场景属性保留。

## 资产来源与制作

| 内容 | 来源与方式 |
| --- | --- |
| 工作台、工具板、推车、备件架、工具、管线、支撑、灯具 | 按已选概念及尺寸，用本地 Blender 独立制作 |
| 新表面 | 自行制作木材、漆面、金属、锈蚀、旧石、土、布与橡胶 PBR 表面；宏观色差保持克制 |
| 拆修电机 | 5080 本地 FLUX.2 三视图，TRELLIS.2 多视角生成，后续 Blender 尺寸、底部支点、减面及法线适配 |
| 土石砌体块 | 5080 本地参考图，采用暴露正面生成，隐蔽背面属于推断；与本地连续土坡结合，不作为精密结构模块 |
| 旧电柜、阀门、破口和雕像 | 继续复用已有资产，保留原包与来源 |

本轮没有引入新的 Fab 工厂包或付费图生 3D 服务。5080 原有 ComfyUI 未运行，已通过既有 Python 环境后台启动；未安装依赖、变更模型或取消其他任务。砌体块原排队中的多视角任务仅在尚未运行时撤回，保留该任务回执，随后改为适合嵌墙摆放的正面生成。

## 文件与接入

- 源目录：`SourceAssets/DungeonRoomInteriors20260921/`
- 规则结构源：`Authored/DungeonRooms_Authored.blend`
- 装配源：`Authored/DungeonRooms_Dressed.blend`（已保存；雕像沿用既有 UE 资产，源装配以锚点表示）
- 自制纹理及材质清单：`Authored/Textures/`、`Authored/material-manifest.json`
- 布置、灯光、贴花与替换范围：`Authored/room-manifest.json`
- 生成输入、工作流、回执、母版和游戏导出：`Generated/`
- UE 新资产目录：`/Game/Dungeons/AtmosphereV2/RoomInteriors/`
- 作者脚本：`Scripts/author_surfaces.py`、`author_rooms.py`、`assemble_room_source.py`
- UE 接入：`Scripts/import_room_assets.py`、`import_generated_phase.py`、`install_rooms.py`，均通过项目既有批次互斥桥执行。
- 导入回执：`Receipts/asset-import.json`
- 场景回执：`Receipts/room-install.json`；只有 `stage=map_saved` 表示本轮地图保存完成。
- 旧引用与变换保留于 `Receipts/previous-room-state.json`，旧资产不删除。

材质与网格采用新包路径，避免重建现有引用中的材质图。外部模型和源文件先制作，地图保存时处理两间房的指定 Actor，不重跑整个 V2 场景组装脚本。

本轮接入按结构、生成模型两阶段完成。结构接入期间修正了工具板与拱顶的表面朝向，并补齐台灯罩厚度，相关四个 Actor 外部包随重导入变脏；最终仅允许这些明确属于本轮的包与新道具一并保存。对应回执为 `bridge-room-final-save-02.txt`，返回 `ROOM_INTERIORS_COMPLETE_SAVED 2 generated masters; 3 instances`。该回执表示操作与地图保存完成，不代表运行或视觉验收通过。

V2 的 `Scripts/install_v2.py` 已补上房间改造阶段，以供后续主动全量重建时保留这轮布置；此次没有运行该全量入口。

## 交付边界

这是两间房的美术实装。分组几何与固定作者种子提供可复现的制作基础；“房间功能 → 状态 → 成组摆设”的运行时随机变化尚未接入。至少 1.2 米的通行留白是布置目标，未进行角色、碰撞或导航验收；最终由用户进游戏查看。

## 用户请求的实景截图

本次使用目标地图的实际材质与灯光，通过 UE SceneCapture2D 输出四张 1920 × 1080 PNG；临时相机随拍摄结束清理，没有改动场景美术或启动 PIE。截图不是概念图，也没有生成式重绘。

- [维修间入口](Previews/DungeonRoomInteriors20260921/01_workshop_entrance.png)
- [工作台及 5080 电机细节](Previews/DungeonRoomInteriors20260921/02_workshop_bench.png)
- [遗迹侧穴入口](Previews/DungeonRoomInteriors20260921/03_ruin_entrance.png)
- [遗迹土石堆与地面细节](Previews/DungeonRoomInteriors20260921/04_ruin_floor_bank.png)

拍摄回执：`SourceAssets/DungeonRoomInteriors20260921/Receipts/room-capture-state.json`。相机位置、视线方向和视角记录在该文件中，状态为 `complete`。

截图可见：维修间的功能物件已成形，但部分台面和道具仍显干净；遗迹墙石、拱石及地砖仍偏规整，土坡与生成砌体的材质、几何衔接生硬，离写实自然的目标尚有差距。本次只交付截图，未因此追加美术修改。

定性读图使用项目 `Tools/deepseek-vision.ps1` 的 DeepSeek 自带图片通道，分别询问维修间及遗迹主体是否可见、有无黑屏或近景遮挡。原始文字保存在 `Receipts/capture-workshop-read.txt` 与 `capture-ruin-read.txt`；仅用于确认截图内容可辨认，不表示用户视觉验收或运行测试通过。维修间入口右缘可见门口墙体，主体仍可辨认。
