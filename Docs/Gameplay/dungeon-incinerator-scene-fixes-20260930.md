# 焚化厅铭牌与栏杆修订 V2

后续状态：用户要求扩大灰渣坑，当前由 [灰渣接收区 V3](dungeon-incinerator-ash-station-20260930.md) 将其扩大至 4.4 × 5 m 并加入接灰装置、中文提示牌；保留本版的铭牌单面制作和栏杆翻下规则。下文保留当时的问题定位。

用户反馈：液压缸下方墙侧铭牌闪烁；栏杆体积/翻越接入不完整；下行楼梯用途不明确。截图保留在 `SourceAssets/DungeonIncineratorHall20260929/SceneFix20260930/Receipts/user-label-flicker.png`。

## 定位与制作

### 铭牌

V1 的 `mesh_helpers.py::plaque` 先生成带正面的金属盒体，又在其正面外偏移 0.0004 m 添加一张文字面。0.4 mm 的双层可见面给深度冲突留下条件，和用户指出的小铭牌闪烁相符；未启动游戏独立复现，不能仅凭单帧截图断言所有闪烁成因。

V2 将标签 UV 直接写到金属底板的唯一正面，不再创建重叠文字面。红圈对应的检修铭牌由原来离墙 12.6 cm 的位置改为贴墙安装，保留 4 mm 金属板、4 mm 支座和两枚固定螺钉。三套炉门共用修订网格，一次接入覆盖三处。门体、手轮与液压管路继续沿用 V1 造型及已保存材质。

### 栏杆

V1 栏杆虽然有封闭圆管几何，但作为一整组零散管件使用复杂碰撞；缺少适合角色与翻越简单查询的连续护栏体。翻越组件 `UFPSTraversalComponent::FindTarget` 首先在脚下约 50 cm 高度做简单射线，再沿上沿、两侧手位、厚度、落点和胶囊路径逐层判断。细圆管、管间空隙和楼梯斜段使这种查询不连续。

V2 制作 15 段护栏：扶手宽 8 cm，立柱 8 × 8 cm，补中横档、踢脚板、底座与锚栓。每一段都附带从底部到上沿的封闭 UCX 凸棱柱；斜楼梯段按原坡度制作，保持楼梯口开放，取消台阶口重复堆叠的 2 cm 短段立柱。

网格使用 `SimpleAndComplex`：角色/翻越的简单查询命中连续体，复杂查询仍使用实体杆件三角面。现有 `FPSBallisticsComponent` 子弹采用复杂射线，所以不把栏杆间所有空洞变成子弹墙。沿用现有翻越动画和输入。

**用户随后明确选择“允许从观察台翻下，仅调整这类栏杆”。** 原因是默认站立翻越 `MaxLandingDrop=60 cm`、空中翻越 `AirMaxLandingDrop=200 cm`，观察台离地 240 cm、灰渣坑深 120 cm，仅修正碰撞并不能开放这些动作。

已为本厅栏杆 Actor 添加 `Traversal.GuardrailDrop` 标记。原生翻越在命中带此标记的 Actor/Component 时，允许搜索 300 cm 内的下方落点；普通表面仍使用原来的 60 / 200 cm 规则。高度、朝向、触手范围、双手上沿、胶囊宽度的可站立落点，以及抬升、跨越、下落整条扫掠仍必须满足。

超出普通落差范围时，`FFPSTraversalTarget::bReleaseIntoFall` 将翻越终点设在栏杆另一侧的上方。原动作完成撑过、松手和收手后，执行器切回 `MOVE_Falling`，由正常角色重力和碰撞处理落地；不会在短暂的动作收尾内把角色插值下移数米，也不会传送到地面。普通小落差翻越继续直接接步行。此次只给焚化厅修订栏杆添加标记，不批量开放其他场景的墙体或护栏。

原生改动限于 `FPSTraversalComponent`、`FPSTraversalRules` 和 `FPSTraversalExecution`。目标结构末尾追加一个反射布尔值，后台完整 Editor 目标构建后再保存带标记的地图；不使用 Live Coding 写入结构布局变化。

### 下行楼梯

这是先前主动设计的灰渣/检修坑出入口，不是误生成楼梯，也没有计划作为地下二层。坑尺寸约 2.8 × 3.8 m，低于主地面 1.2 m，设 8 级回到地面的踏步。当前尚无接灰设备、检修任务或足够用途提示，因此其功能表达确实不完整。本次未擅自填坑，也未扩大为两层结构。

## 保存范围

- 作者目录：`SourceAssets/DungeonIncineratorHall20260929/SceneFix20260930/`。
- 可编辑源：`Authored/Incinerator_Nameplate_Railings_V2.blend`；保留编辑网格、语义顶点组、导出网格和 UCX。
- 新包：`/Game/Dungeons/IncineratorHall20260929/SceneFixV2/Meshes/SM_Incinerator_FurnaceDoorKit_V2`、`SM_Incinerator_Railings_V2`。
- 导入器只切换焚化厅内三处炉门和一组栏杆的网格引用，保持 Actor 变换、场景布置、灯光、两车与配电柜。旧网格保留；修改前地图在 `Backup/`。
- 设备配置通过 `post_install_script` 衔接本批修订，避免以后重建样板/重装设备时恢复旧铭牌与栏杆。
- `Receipts/install.json` 中 `stage=scene_fix_assets_and_map_saved` 才表示地图和新资产实际落盘。制作回执不等于运行验收。

本轮实际完成：`Receipts/install-v2-stdout.log` 记录两组新网格及 4 个 Actor 引用保存；`Receipts/build-guardrail-drop.log` 记录常规 Editor 构建 `Result: Succeeded`（22.46 秒，原生日志 `Saved/BuildEditor/build-20260930-005944.log`）；其后的 `Receipts/install-v2-guardrail-stdout.log` 记录在新二进制下再次保存地图和栏杆专用标记，退出码 0。构建过程中仅编译既有 audit 翻译单元作为正常依赖，没有执行这些测试。

没有主动启动编辑器、PIE、截图、渲染或运行测试；修订后的闪烁、栏杆碰撞和翻越手感由用户实机测试。
