# 温带丘陵河流初版

2026-09-13，UE 5.8.2。仅使用已经下载的免费资产，接入现有 `/Game/GameMaps/L_TemperateHills_Initial`。不使用付费河流插件。

## 当前实现

- 新建世界的种子决定排水路径与河宽；从原丘陵高度采样 16 m 网格，由地图边界向内进行优先级排水搜索，反向累计汇水量，再选取一条较长、靠近出生区域的干流。路径会避开出生点、返回传送门及其周围 60 m 候选区。
- 曲线平滑后计算单调下降的水面，河宽约 7–13 m，源头逐渐收窄；河床水深目标约 35–75 cm。初版是供步行涉水的浅河，不包含游泳、浮力、船只或完整支流网络。
- 地形高度、法线、碰撞和植被拒绝规则读取同一份河道数据。河床、湿鹅卵石带、较干的细碎石过渡融入原地形；非河流区域继续使用原 Normandy 草苔、草土、碎石材质。
- 河面沿曲线生成网格，UV 根据累计长度连续流动。网格在 64 m 地形格边界准确裁剪，河段卸载时销毁对应水面。水面没有碰撞和投影，实际行走碰撞来自河床。
- 河石复用现有第 1 层 PCG 岩石图：独立的种子盐与候选 ID，7.5 m 抖动候选网格，稀疏分布在浅水与河岸。沿用 120 m 生成半径和既有清理半径；不为每个鹅卵石生成 Actor。

## 加载与资源范围

- 河道规划在后台执行，结果是不可变纯数值数据，不访问 Actor/UObject。地形任务持有只读共享数据；切图后未结束任务可自行完成，无需阻塞等待。
- 水面材质与地表在 loading 的地面准备阶段异步加载；河石放入已有岩石准备阶段，并参与显示资源准备。选用资源沿用 GameInstance 的资源句柄保留机制。
- 保留最多 2 个地形后台任务、每帧 1 个地形提交；同格至多附带一个小型河面组件。河流附近地形为近处 1 m、远处 2 m 顶点间距，避免原来 8 m 的远处网格盖住浅河床；其余格沿用原精度。
- 仅导入 9 张 Quixel 贴图（颜色、法线、粗糙度各三组）及 1 个 Nordic 岩石模型。4K 源图保留，项目内新增贴图最大显示尺寸设为 2K。岩石使用普通静态网格和作者阶段生成的 3 档 LOD，不新增 Nanite 首次构建负担。
- 水面复用 Water Materials 的两张河流法线和泡沫纹理，项目独立材质支持流速、水色与岸边泡沫；不启用全图流体仿真。

以上为实现与调度预算，不是实测耗时、FPS 或不卡顿承诺。

## 素材来源与本地文件

下载库：`D:/FPS3D/VaultCache/FabLibrary`。源下载文件保持原样，导入输出仅位于 `/Game/WorldGeneration/TemperateHills/Rivers`。

| 来源 | 使用内容 |
|---|---|
| [Water Materials](https://www.fab.com/listings/063155ea-d9d2-4f29-b09f-33270b0bc861) | `T_River_Waves01_Normals`、`T_River_Waves02_Normals`、`T_Ocean_Foam` |
| [Shoreline Beach Rocks](https://www.fab.com/listings/1a759058-df60-438f-9745-133510946f09) | `wldgfhrlw`，鹅卵石地表的颜色、法线、粗糙度 |
| [Small Pebbles Ground](https://www.fab.com/listings/a0e6a70f-8d24-4481-af19-327f5e7e5bef) | `xbliajz`，细碎石过渡地表 |
| [Nordic Beach Rocks](https://www.fab.com/listings/80de6243-15d8-4a4e-892b-c8223df27330) | `ulznddxva`，High FBX 和配套贴图；开放底部埋入河床 |

免费领取不等于可以公开再分发原始素材；这些二进制及生成材质留在本机，Git 只发布项目源码、作者脚本和说明。复建需要拥有并恢复同一批 Fab 内容。

## GitHub 借鉴范围

1. [redblobgames/mapgen4](https://github.com/redblobgames/mapgen4)，Apache-2.0。[map.ts](https://github.com/redblobgames/mapgen4/blob/main/map.ts) 的 `assignDownslope/assignFlow` 展示由出水口建立无环排水顺序、逆序累计水量的思路。本项目以规则高度网格、边界出口、出生区域保护、单干流选择和河床采样独立实现，没有引入其 TypeScript、Voronoi 库或渲染器。
2. [bonahona/InstantRiver](https://github.com/bonahona/InstantRiver)，MIT，Copyright 2019 Bona Fyrvall。[RiverSystem.cs](https://github.com/bonahona/InstantRiver/blob/master/Assets/InstantRiver/RiverSystem.cs) 展示曲线横截面、沿程 UV 与网格带生成。本项目使用 UE DynamicMesh、角点切割平滑、网格裁剪与距离加载独立实现，没有移植其 Unity 源码或水 shader。
3. [Code1133/ocg](https://github.com/Code1133/ocg)，MIT。其 UE 编辑器生成器依赖 Water、PCG 等插件，可供后续编辑工具参考；本次未接入，因为目前地形在游戏开始时由 DynamicMesh 生成。

上述为算法与结构参考，不是完整移植，也没有第三方运行时代码依赖。

## 作者脚本与入口

`Tools/WorldGeneration/build_temperate_rivers.py` 导入默认 Fab 下载库内已解压素材，生成河流材质、地表混合、石材和 LOD，并更新现有 `DA_TemperateHillsStreaming` 的软引用。原始丘陵地图无需重新保存。作者脚本保存配置与已有河岸材质的本地备份到 `Saved/TemperateRivers/BeforeAuthoring-*`。

```powershell
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' 'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript -script='D:/FPS3D/FPSGAME/Tools/WorldGeneration/build_temperate_rivers.py' -unattended -multiprocess -NullRHI -nosplash -nop4
```

重启编辑器或游戏进程后，从原有丘陵传送门进入。原世界的种子、WorldId 保留；现有种子也会根据本次算法补上河道，因此河道范围内的地形会变化。世界存档仍只存种子与世界身份，尚无建筑／采集地形修改需要迁移。

进入丘陵时初始朝向改为朝向最近河段，出生位置仍在原来的干燥空地。可沿该方向前进接近河滩。

作者脚本已执行到 `TEMPERATE_RIVERS_AUTHORING_COMPLETE` 并保存配置。命令行编辑器仍因项目原有的 `GameFeatureData` AssetManager 注册配置问题返回 1；这是进程退出码，不将其报告为完整命令行运行通过。

最终作者进程还报告工具服务的 `127.0.0.1:8000` 端口已占用；素材导入、材质保存和配置接入已在同一进程完成，未更改其它进程的端口设置。详细日志为 `Saved/TemperateRivers-authoring.log`，作者输出清单为 `Saved/TemperateRivers/authoring.json`。

Editor 与 Game 的 Development 原生目标已完成构建，日志为 `Saved/TemperateRivers-build-editor.log` 与 `Saved/TemperateRivers-build-game.log`。本次构建不等于运行或画面测试通过。

按用户要求，本次不启动游戏、不执行性能采样、回归或视觉验收，实际效果和游玩由用户测试。
