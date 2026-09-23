# 地牢铁门细化与浅积水材质 — 2026-09-22

## 范围与现状依据

用户截图中的机房格栅门原来由直方杆、横杆与少量锁件构成，整体缺少门扇接缝、五金连接和明确的材质层次。
当前作者链里的四处积水使用 `M_WetFloor`：不透明深色、固定粗糙度 0.095 的平面；没有水面运动与透明边缘。
制作输入读取回执位于 `SourceAssets/DungeonGateWater20260922/Sources/scene-inputs.json`。此读取仅用于接入已有对象。

本次保留现有机房开口、主体位置与四处积水位置，重做两个视觉网格。原静态门的玩法、房间动线与其他布景保持原有接入方式。

## 铁门

- 以原三个立柱位置和 3 m 高度为基准，分出左侧门扇、右侧固定网片和上方气窗；门扇有明确的边框及间隙。
- 方管框做毫米级倒角，细网格改成圆钢丝；横纵钢丝在不同深度真实接触。
- 增加钢丝端部焊点、局部交叉点焊痕、框角焊缝、锚固片与六角螺栓。
- 门扇增加三组分段合页、销轴、锁体、锁扣、拉手和锁孔；下方增加带折边的防踢板。
- 材质区分深色涂层、裸钢、焊缝与暗孔。顶点色分开控制边缘磨损、底部潮湿积垢及接缝锈蚀，复用项目原创 Services 纹理。
- 表面磨损以门边、操作件、焊口及近地面为主；锈蚀提高粗糙度并降低金属度，裸露钢边保留金属反射。
- 维持静态三角面碰撞，细钢丝与五金使用常规 Static Mesh，不启用 Nanite 简化。

## 从喷泉借鉴的部分

读取了现有喷泉技能、V3 水面作者脚本、V8 自然溢流脚本及 V9 精修记录。当前喷泉水面实例的父级仍为 `M_FountainWaveWaterV3`。

沿用的原理：

1. 使用真正逐像素的 `WorldPosition` 计算波纹，不使用每物体常量 `ObjectPositionWS` 充当表面位置。
2. 用波函数的梯度构建水面法线，让反射随水纹发生细微变化。
3. 复用 V8 已有的原创 256² RGBA 噪声，两个低速采样打散同步运动。
4. 将落点涟漪单独控制，四处积水有不同相位与强弱。

针对室内浅积水重新处理的部分：

- 新建 `M_Dungeon_ShallowPuddle`，不修改喷泉共享材质和实例。
- 透明、逐像素表面光照，水的 Specular 默认 0.255、中心 Roughness 默认 0.075。反射由场景照明提供，不使用喷泉的户外发光 Cubemap。
- 保留原水面 0.9 cm 标高；波纹主要作用在法线，没有 WPO 起伏，不让薄水膜上下穿地。
- 不规则但连续的水岸由多圈顶点提供渐隐权重；岸边粗糙度升高，配合 DepthFade 减轻硬边与相交痕迹。
- 透明水膜让地砖保留可见性，取消原来不透明深色片的覆盖方式。
- 轻微滴水涟漪约每 4.7 秒一轮，各水滩错开相位；不带喷泉白沫、水柱、落水飞沫和流水声。
- 无积水碰撞，不投射水面阴影，不新增 CPU Tick、Niagara 或原生模块。

## 参数与制作入口

| 对象 | 入口 |
| --- | --- |
| 尺寸、位置与相位 | `SourceAssets/DungeonGateWater20260922/Config/design.json` |
| 精确模型制作 | `Scripts/author_geometry.py` |
| 可编辑母版 | `Authored/DungeonGateWater_Source.blend` |
| 水法线 | `Scripts/puddle_normal.hlsl` |
| 材质与 FBX 导入 | `Scripts/import_assets.py` |
| 两个现有 Actor 的网格替换 | `Scripts/install.py` |
| UE 资产 | `/Game/Dungeons/AtmosphereV2/GateWater/` |

水参数：`WaveStrength`、`DripStrength`、`CenterOpacity`、`ContactFadeCm`、`CoreRoughness`、`WaterTint`。铁门参数：`FinishColor`、`FinishRoughness`、`EdgeWear`、`RustAmount`、`MicroNormalStrength`。

完整房间源由 `SourceAssets/DungeonWorkbenchKit20260921/Scripts/assemble_room_source.py` 追加当前覆盖层。全图重建的 `DungeonAtmosphereV2_20260921/Scripts/install_v2.py` 最后运行本轮接入，避免恢复旧格栅和不透明积水片。

## 交付边界

必要的模型制作、材质编译、导入及地图保存由脚本回执记录。未运行 PIE、截图、渲染、游戏回归或性能测试；用户自行体验本轮材质和近景效果。不将作者脚本执行或资产保存表述为视觉验收通过。

## 用户反馈后的积水棋盘格修复

用户随后明确要求排查地面积水全部显示马赛克的问题。实际 Actor 与材质槽引用正确；根因是本轮两个噪声采样节点错误使用 `SAMPLERTYPE_LINEAR_COLOR`，而复用的喷泉噪声纹理采用 `TC_MASKS` 压缩。引擎报告 `Sampler type is Linear Color, should be Masks`，使整个积水材质回退到默认棋盘格。

修复将现有 `M_Dungeon_ShallowPuddle` 的两个采样节点改为 `SAMPLERTYPE_MASKS`，保留共享噪声纹理、透明水面图表、参数及关卡引用。源制作器同步改正采样类型，并处理 `recompile_material` 返回的错误，避免再将编译失败的材质记录为制作成功。

定向修复回执：`SourceAssets/DungeonGateWater20260922/Receipts/puddle-sampler-repair.json`。修复前编译返回上述错误，修复后错误列表为空，材质已保存；没有启动 PIE 或截图渲染。修复脚本为 `Scripts/repair_puddle_sampler.py`。
