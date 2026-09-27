# 精英房铁闸门适配

2026-09-26。复用用户认可的通道 `DGN_AV2_MachineGrille` 源制作函数与 GateWater 材质，将精英房的实心 Cube 封堵替换为分节焊接钢丝闸门。原通道门、固定起点、Boss 门和奖励门不改。

## 几何与尺寸

当前普通战斗房主门、侧门和通风配方门均为 300×280 cm。固定起点的 132×238 cm 门洞和独立奖励门不属于本次封门对象。不重写房间生成算法，也不重新切墙；使用布局清单中每个真实连接门的 `FloorCenter / OutwardNormal / Width / Height` 装配。

四个共享资产：闸门节片、左导轨、右导轨、顶部收纳罩。节片沿用 `DungeonGateWater20260922/Scripts/author_geometry.py` 的 `panel / box / rod / bead`，重新裁配尺寸与钢丝数量，保留 8 mm 竖向钢丝、7.6 mm 横向钢丝、约 12.5×13 cm 网格间距、点焊、圆角、Wear 顶点色及原 Paint / Steel / Weld / Dark 表面。不把整套带铰链的固定隔栅压扁拉伸，也不复制其纹理。

标准门洞的每节外廓为 304×74 cm；四节闭合时相邻搭接4 cm，底部入地2 cm，顶部超过门洞2 cm。各节分属独立滑道，分别从 -2 / 68 / 138 / 208 cm 抬升到底部282 cm，全部收纳后顶端356 cm，外罩顶端358 cm。相较最低365 cm房高保留7 cm；这为作者尺寸计算，不代表已进行现场管线、灯具或战斗碰撞验收。

滑道中心沿房内方向为25 / 32.2 / 39.4 / 46.6 cm；轨道为开口C形截面，锚固片接旧门框房内面。主体在旧32 cm厚门框之后安装，保留300 cm净宽。门楣收纳罩留底部入门槽，避免原300 cm整块门板向上移动316 cm直接穿过顶板。源与运行时尺寸共用 `Config/design.json` 生成的 `DungeonRoomGateDimensions.h`。

运行时对门宽、门高分别适配节片、导轨及罩体，进深不缩放。当前标准门实际为1:1；未来显著改变门宽/门高时，应改设计参数重新生成网格，避免大幅缩放改变钢丝粗细与间距，并为罩体预留 `门高 + 门高/4 + 8 cm` 顶部空间。这不是任意异形洞口的自动建模器。

## 遭遇接入

- `ADungeonRoomGate` 是由遭遇持有的无 Tick Actor，每个实际连接门一套；四节共用一个 ISM 网格。入口、出口、已连接侧门/回路均装配，未连接的静态封板仍归原生成器处理。
- `DungeonRoomEncounter` 在原有全组落地、存活预算、离场/死亡放行及清房逻辑上驱动闸门；门参数或资源不完整时整组闸门不启用，保留开放战斗。
- 1.4秒平滑升降；仅运动期间使用每帧更新，其余沿用20 Hz遭遇轮询。各节碰撞盒跟随实体运动，超过门洞后才关闭，不在开门指令瞬间解除碰撞。
- 导轨与收纳罩有各自独立碰撞，不用一个大盒覆盖门洞。全部碰撞不触发导航重建。
- 按实际四轨范围与玩家胶囊阻止夹门；玩家在下降期间回到扫掠范围则重新升起。清房/离场/死亡照常开启；重新生成与退出时销毁所属闸门。

## 制作与状态

- 源：`SourceAssets/DungeonEliteGate20260926/Config/design.json`、`Scripts/author.py`、`Authored/DungeonEliteGrille.blend` 和四份 FBX。
- 资产：`/Game/Dungeons/EliteGate20260926/Meshes/`。`Receipts/import.json` 已为 `meshes_saved`；后台导入日志 `Saved/elite-grille-import-20260926.log` 为0错误，未启动可视编辑器。直接引用原闸门材质，只补足所需实例化/Nanite用途标志。
- 代码：`DungeonRoomGate.*`、`DungeonRoomGateDimensions.h`、`DungeonRoomEncounter.*`。运行时导演直接创建，无需重存整张地图；下一次启动新构建并生成地牢时接入。
- Editor 常规构建成功（`Saved/elite-grille-build-editor-complete-20260926.log`，11.48秒增量收尾）。同步编译兼容修正后的最终 Game 常规构建成功（`Saved/elite-grille-build-game-complete-20260926.log`，61.97秒）。模型资产与两个构建目标均已落盘。

完整构建曾被同期代码的接口错误阻挡。本轮仅追加编译兼容改动：`ColdSteelForgingWidget.cpp` 改用 UE 的 `SetFillColorAndOpacity`、用局部原始指针接收 Label 输出后赋回 TObjectPtr、避免局部 Slot 名遮蔽；`FPSGAMECharacter.h` 给弓组件补已有武器组件同款 friend 声明；`ColdSteelSkillModel.cpp` 通过组件接口获取 Bow。保留这些文件的其他并行修改。其余同期弓近战访问修正沿用工作区已落盘版本，未覆盖。

没有执行游戏、PIE、截图、渲染、多种子或回归测试；交由用户体验。
