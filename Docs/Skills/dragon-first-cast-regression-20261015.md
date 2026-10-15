# 龙息重新进入与首次释放实测（2026-10-15）

用户明确要求本轮实机检查自动准备、首次可见火焰及进场放行。本记录的测试授权只用于本轮指定范围。

## 环境与入口

- 正常 `DayNight_Lighting` 地图、FPSGAME GameMode 与第一人称角色，单人独立进程，DX12/SM6、1280×720、屏幕外真实渲染。
- `GameLoadingMode=Quick`；独立 `ColdSteel_DragonEntryAudit_*` 档案、学徒长杖、25 项已学技能。复用实际 Transit 顺序队列及 `UFPSFireMagicComponent::Trigger`，每轮仅调用一次施法，不强制加载、编译或激活特效。
- 启动参数 `-DragonEntryAudit -ExecCmds="t.MaxFPS 60,fps.DragonEntryAudit"`。测试源 `Source/FPSGAME/Skills/DragonBreathEntryAudit.cpp`，只有显式命令和独立档案才启动；生产游戏不执行。
- 独立游戏模式默认以 Final 压缩大量贴图；初次 `normal` 试跑在进入测试前终止。后续显式使用 `-ForceTextureEncodeSpeed=FinalIfAvailable`，与编辑器试玩相同，保留相同测试配置／缓存，分别新建游戏进程。
- 初次两个单技能测试档被档案校验拒绝，未发生施法，不能作为龙息失败或通过证据；该测试选项已删除，最终采用完整 25 项配置。

## 发现与修正

`normal-editor-textures`：后台自动就绪、扣蓝、冷却和活动实例状态正常，输入未锁，但首次施法截图在 0.1/0.4/1/2 秒均没有火焰。该轮 `state_passed=true` 仅表示状态检查，视觉结果为失败，不能据此交付通过。

`diagnostic`：另一个新进程中 0.4 秒已显示火焰（GPU 读取在 1 秒才执行，没有借读回来制造这个通过结果）。GPU 温度场峰值 145.875、热单元 262731，燃料源粒子约 145，说明实际模拟能够生成火焰。旧诊断曾读未使用基材的 ShaderMap，这不能代表实际 MID；诊断已改为读取实际材质接口资源。

生产修正位于 `FPSDragonBreath.cpp`：原先隐藏组件只准备了模拟；现在以零显示强度实际准备体积渲染路径，并等待实际 MI/MID 的 ShaderMap／编译／PSO 后，才暂停隐藏并标记可用。相关参数仍为 R6，不调整颜色、厚度、伤害或输入规则。ShaderMap 轮询不等待全局任务；进场不依赖此状态。

## 最终复测

| 案例 | 普通首次释放 | 准备期间提前输入 |
| --- | --- | --- |
| 目录 | `final-normal-all` | `final-early-all` |
| 龙息等级 | 1 | 20 |
| 已学技能 | 25 | 25 |
| 输入放行（测试启动后） | 0.224 秒 | 0.247 秒 |
| 龙息自动就绪 | 79.691 秒 | 80.262 秒 |
| 首次施法输入 | 80.142 秒 | 79.305 秒，进入“火焰准备中” |
| 首次实际释放 | 80.542 秒 | 80.648 秒 |
| 放行后输入锁定帧 | 0 | 0 |
| 预建组件复用 | 是 | 是 |
| 首次火焰画面 | 0.4 秒截图明确可见 | 0.4 秒及 1 秒截图明确可见 |

两轮进程均正常退出（0），首次实际释放均有火焰，未通过第二次施法修复结果。提前输入案例从按下到就绪为 0.957 秒，准备期间魔法值保持 1600，随后同一个请求自动完成手势和释放，冷却为 38 秒；普通案例冷却为 45 秒。截图中的火焰仍为 R6。测试观察器没有创建备用龙息实例，也没有执行强制 GPU 刷新；两轮最终结果均未启用 `DragonVolumeDiagnostics`。

时间从正常世界的测试入口启动计，不包含引擎启动、地图读取、初次 DDC／贴图缓存生成；全队列的后台等待不等同于进场加载时间。独立进程中冰锥／冰墙等模型准备出现逐项超时，队列继续处理龙息；不宣称所有已学技能的模型准备或帧时间均通过。

全部日志、机器状态结果和原始截图在 `Saved/DragonFirstCastRegression20261015/`。最终两轮不启用 GPU 诊断读回。没有启动联机或做音频验收。

最终交付：正式 `FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 后台构建均成功，主 Editor DLL 与 Game EXE 已更新。日志 `final-editor-build.log`、`final-game-build.log`；合并的状态／视觉复核结果、二进制时间及 SHA-256 位于 `regression-result.json`。本次没有改动 R6 的 Niagara 或材质资产。
