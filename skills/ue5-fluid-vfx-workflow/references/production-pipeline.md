# 流体制作管线

仅在需要新源素材、选型或重制资产时读取。本文件描述制作方式，不要求运行预览或验收。路径相对 `D:/FPS3D/FPSGAME`，源能力与示例来自 2026-09-23～24 项目制作。

## 选路线

| 需求 | 默认路线 | 需要保留的边界 |
| --- | --- | --- |
| 枪口烟、爆燃余烟、蒸汽、冷雾 | 密度动画图集＋少量 Niagara 烟片 | 图集是流体形态来源，运行时不是体积求解；近景控制卡片感与透明覆盖 |
| 火球与持续火焰 | 燃烧场 RGB＋既有主体／外焰材质 | 温度和密度改变层次，不破坏主体轮廓、原图集及曝光约定 |
| 频繁水花 | 离线液体网格烘焙为法线／覆盖率图集＋水滴 | 烘焙水冠只播放形变，额外水滴做弹道；避免水冠双重上抛 |
| 涟漪、尾迹、腐液内部回流 | 既有表面材质上的有界解析场 | 不新建整片透明叠层或每滴碰撞事件；真实受击面仍由游戏几何决定 |
| 毒液弹与地面残留 | 现有网格形变／ISM＋贴花或表面材质 | 主体和危险边界稳定，随机变化用于装饰；不改变实际碰撞体 |
| 少量重点体积烟火 | OpenVDB → Animated SVT＋体积材质 | 是预计算体积播放；记录帧率、通道、空间变换、显存／流送与并发 |
| 少量复杂液体形变 | Mantaflow 网格 → Alembic Geometry Cache | 是动画网格缓存，不自动具备液体碰撞、浮力或动态交互 |
| 确有即时流场交互需求 | 局部 Niagara Fluids 2D／3D | 明确域尺寸、分辨率、同时活跃域数、更新成本、远景替代及结束释放 |

当前基础库已使用 Epic Niagara／Niagara Fluids／Water、原生 SVT、Blender Mantaflow。不要虚构独立“SVT 插件”。Zibra／FluidNinja 是可选后端，不作为默认依赖；只有任务涉及选型或采购时才查询最新兼容与许可，不把旧价格、营收门槛写成永久标准。

## 从模拟到可编辑源

- 在 `SourceAssets/<Effect><Date>/` 保存 `.blend`、作者参数和清单；运行资产在 `Content`，工具在 `Tools/Fluids`，制作说明在 `Docs/Fluids`。优先复用已有合法图集／缓存；仅改采样或通道时使用已有导出分支，不重算模拟。
- 写明单位、轴向、域边界、分辨率、帧区间、FPS、预热区间、种子和导出变换。Blender 源为米、UE 使用厘米；只在既定导出／导入／Actor 层转换一次，不能叠乘 100。
- 制作贴图需要的离线渲染属于生产导出，和用户未授权的预览／验收渲染分开。能直接投影密度场时复用数值导出。
- 保留源资产及必要缓存，不因缓存体积大主动删除。来源包括原创参数、Epic 母版、项目既有商业包，分别记录；素材可用于游戏不等于允许公开原文件。

## 图集数据合同

每张数据图集记录：排列、单格大小、完整／有效帧数、播放方式、帧率、边界留白、各通道含义、压缩、sRGB、过滤与 mip 策略。生成器和材质共同读取同一份帧清单。

- 密度／温度／法线数据按线性数据处理，颜色贴图另论。序列用统一归一化范围，避免每帧自动增益造成抽动。
- 枪口密度当前读取 `T_MuzzleSmokeMantaflowV14` 的 R；燃烧场 `T_FireballCombustionFields` 为 R 火焰积分、G 火焰加权温度、B 烟密度。
- 水花 `T_RiverSplashPacked` 为 RG 视空间法线 XY、B 泡沫着色权重、A 覆盖率。B 不是物理泡沫浓度，空像素不应保留有光照作用的法线。
- 一次性事件按粒子年龄播放并钳制末帧；循环火焰先处理接缝，再用独立相位错开。水花随机选择完整变体，不随机跳起始帧破坏喷出与回落时序。
- 相邻帧插值须正确处理覆盖率、法线和最后有效帧；每个 tile 保留采样边界。Niagara 已做 SubUV 时，采样另一张图集前先恢复格内 UV，不能把原图集尺寸硬改为新图集尺寸。
- mip 策略按图集选择：枪口／火球近景数据图当前无 mip；自然水花有 mip 并单图固定驻留。两者都是具体资产方案，不推广成全项目关闭 mip／流送。
- 液体缓存的零顶点帧必须导出透明图块，缺失缓存应明确失败；不能把缺失当空帧，也不能渲染模拟域的方盒回退。详细修复见 [透明问题](transparency-and-visibility.md)。

## VDB／SVT 与液体网格

- 从实际 VDB 网格名、类型和变换建立导入映射，不假设每个缓存都有相同通道。Foundation 这一份映射是 Attributes A = density／flame／shadow／temperature，B.xyz = velocity；其他缓存需另取实际布局。
- SVT 材质分别表达消光、散射和温度发光；继承项目实际使用的 Substrate／体积材料接口，不叠加两遍曝光补偿。固定体积边界、帧率和单次／循环行为一起接入。
- Foundation 的 SVT Actor 已在 Actor 层做米→厘米；Geometry Cache 在既定导入环节转换。改变任一层要同步记录，不能凭画面大小补第二次缩放。
- 液体 Geometry Cache 保存帧率、时间范围和材质槽；游戏碰撞按用途另用简化几何。动态表面播放不意味着物体已支持浮力或流固耦合。
- 当前丘陵为 DynamicMesh，没有 Landscape。Epic Water Custom 资产仍是可用入口，不代表当前河道已迁成 WaterBody；迁移还涉及水位、河岸、地形修改、水面查询与生命周期。

## 作者脚本必须保留后续维护能力

新外观可用独立版本资产；已有正式路径的局部修复可增量改当前资产并保留本次原件。第三方母版不直接修改。节点用稳定标识定位，已知图不符合预期时停止该目标，保留其他资产。

Niagara 模板要读取其生命周期、SimTarget、LocalSpace、Renderer、User 参数和 Dynamic Parameter 约定，再接入；外部包发射器的生命周期不能盲设为主体的 `Self`。新粒子的出生帧就写入大小、颜色、朝向、UV、速度与寿命，不能等下一帧更新补齐。

保留原有材质输入和曝光／预乘规则。当前项目曾因删除 rooted 材质表达式触发断言；增量重接时复用已标记节点，必要时保留已断开的旧节点，不在效果任务中顺带清理整张图。编译和保存必须针对本次目标，并同步原始生成器，防止全量重建退回旧效果。

## 作者脚本与构建窗口的已知坑（2026-09-24 高炉烟实战）

- VectorVM CPU 自定义 HLSL：表达式里**不能引用 `Engine.Environment.DeltaTime`**（帧率用 SpawnRate 标准模块）；无 `smoothstep` 内建（手写 smooth(low,high,v)）；`sqrt/sin/cos/exp/frac/saturate/lerp` 可用。
- 幂等重跑：`trim()` 会删除生成的 SetVariables 模块——重跑前必须**无条件退役**上一轮写进资产的赋值 tag（`Fireball.Assignments.*`、`FluidContact.<emitter>.<script>.i`），否则 assignments 按 tag 找回已删模块名直接编译失败。局部变量名不得遮蔽模块别名（`import unreal as u` 配 `u=` 局部变量＝整个函数别名被吞）。
- Unity 批量编译：跨 .cpp 的同名匿名 namespace 符号会并进同一翻译单元（C2374/C2086）——文件级符号一律带文件前缀。
- Windows PowerShell 5.1 语义的 `Get-Content -Raw` 按 ANSI 解码无 BOM UTF-8：`-replace`＋回写会把源文件全部 CJK 变乱码且**不可无损逆转**；源文件文本处理一律用 Python 或编辑工具，不用 PS 管道改写。
- 构建窗口：`Build-Editor.ps1` 同时检测 `UnrealEditor.exe` 与 `UnrealEditor-Cmd.exe`（含他人会话的 commandlet），占用即 `throw`——该 throw 会穿透 `&` 调用杀死等待脚本，序列里必须 try/catch 接住再走重试；轮询用 1s＋连续多次空采样（10s 会漏掉快速重启窗口），不强关他人进程。
- **NS 资产名不得是任何发射器名的前缀（2026-09-26 出铁口金流实战）**：`NS_FurnaceTapMetal`（发射器 `FurnaceTapMetalFlow` 的前缀）名下，编译可复现失败——报幻影 `SystemUpdateScript` Custom Hlsl「User.DetailReduction 尚未遭遇」valid=0；逐字节相同内容改名 `NS_FurnaceTapMetal2`/`NS_ProbeTap*` 即 valid=1；无文件/注册表/内存幽灵，声明修正与内容扰动均无效。机理未明，**绕行为准**：命名先对照发射器清单。复现探针 `Tools/Fluids/probe_tap_name_cache.py`，全链诊断归档 `SourceAssets/FurnaceTapMetal20260925/Probes/`。
- 作者层杂项（同轮实录）：VectorVM 无两参 `atan`（用 `atan2(y,x)`）；`put()` 整型输入必须显式 `/Script/Niagara.NiagaraInt32`；模块输入清单随引擎版本变化（5.8.2 的 SpawnBurst_Instantaneous 无 `Spawn Probability`）；f-string 内嵌 HLSL 助手函数必须写成 `{smooth(...)}` Python 求值，字面 `smooth(...)` 会原样漏进 HLSL；verify_source 的禁词扫描会命中脚本自身的字面量（用拼接规避自引用）。
- **NullRHI 材质编译通过≠真机能过（2026-09-26 出铁口金流实机教训）**：`ParticleSubUV` 等需要纹理绑定的采样节点缺纹理时，commandlet（-NullRHI）静默通过，真机 SM6 报「Missing ParticleSubUV input texture」→ 游戏内 Default Material、粒子全不可见。程序化材质取每粒子变化一律用 `DynamicParameter`（配 NS 写 `Particles.DynamicMaterialParameter`）或 `ParticleColor`，不引用任何需纹理输入的节点；交付前扫一遍用户会话日志的 `LogMaterial: Warning ... Failed to compile Material for platform`。
- **MaterialFactoryNew 空白材质必须手动补 usage flag（同轮第二实机教训）**：新建材质默认不带任何「Used with …」标记，真机报 `missing usage flag NiagaraSprites! Default Material will be used in game.`＝粒子渲染成白/灰马赛克；NullRHI 同样不检查。给 Niagara sprite 用的材质一律 `set_editor_property('used_with_niagara_sprites', True)`（其它宿主对应 `used_with_particle_sprites`/`used_with_niagara_ribbons` 等）；复制既有 MI/母材的做法天然带标记，新建才踩。验收扫日志关键字 `missing usage flag`。
- **NS 局部空间坐标契约（同轮实录）**：发射器 `bLocalSpace=True` 时粒子坐标＝组件局部系；若 NS 作者脚本已按构件网格局部系写坐标（manifest 锚点），C++ 组件必须**恒等变换**挂构件，再叠相对偏移＝双重错位。运行时挂 WorldSettings 的展示组件（锭池等）每次展示必须 `AttachToComponent` 到目标构件，否则 SetRelativeLocation 全落在世界原点附近。
- **真机验证闭环（2026-09-26 出铁口金流三轮实录，最终仍挂起）**：NullRHI 离线链只能证明"编译通过"，证明不了"真机可见"——该轮连续两轮被真机日志打回（SubUV 缺纹理→usage flag 缺失），第三轮编译层清零后用户仍报不成功（观感层，未及排查即挂起）。教训：①每轮交付后**第一时间扫用户会话日志**（`Saved/Logs/FPSGAME*.log` 搜本任务资产名＋`Failed to compile Material`＋`missing usage flag`＋`LogNiagara.*Warning`），日志干净≠效果正确；②请用户复测时**要求描述现象或截图**，"不成功"三个字无法定位观感层问题；③连续两轮同一资产被真机打回时，改用短批次编辑器接入（mcp_call_codex.ps1 批次互斥）在真实渲染环境自查一遍材质/坐标/时序，不再消耗用户复测轮次；④挂起案必须在任务文档写明：已排除层（本例＝编译层）、剩余怀疑层（观感/时序/可见性）、热退档路径与接手第一步。
