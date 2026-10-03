# 主神空间喷泉补水与清泉赐福

主神空间 DayNight_Lighting 中现有 AColdSteelFountain 复用统一准星浮窗与 E 键互动。走近喷泉边缘、准星指向喷泉石材，在现有 250cm 视线距离内按 E，补满当前最大缺水度并获得清泉赐福。不按喷泉中心测距，不新增碰撞体、喷泉模型或地图实例。

清泉赐福持续 720 秒，饥饿和水分下降速度乘 0.9。再次饮水补满水分并刷新 720 秒，不叠加减速或累加时长。SAN 与食水归零后的每秒 10% 最大生命损血仍使用原规则；只恢复水分，饥饿已经归零时仍继续损血。

倒计时由 UFPSSurvivalComponent 的既有 0.25 秒调度推进，计时与消耗使用同一状态。最后一个跨越到期点的更新按赐福/普通两个时间段分别计算，耗尽损血时钟使用对应耗尽时刻。暂停、死亡、离线不消耗时间，切图和读档保留剩余秒数；重生随新的生存状态清除赐福。旧档追加字段默认 0，无赐福。

FountainBlessingSeconds 追加到既有 FFPSSurvivalState；复用档案存读、自动保存与拥有者复制。互动成功时同步档案并执行既有 SaveNow，避免之后的库存操作回写旧生存快照。互动沿用项目当前 TraceTarget 的本地/权威路径，不新增客户端 E 键 RPC。

左上复用 UStatusEffectsHUD 的 54×44px 效果卡片、现有共享冷钢字体和底色，水滴为目录图标字形；显示清泉赐福、12:00 至 0:00 倒计时和剩余进度。倒计时借用此无叠层效果的空白层数区域，悬停提示解释效果与刷新规则；无效果时隐藏。Snapshot 直接读取实际生存组件，不以额外显示计时器决定玩法。获得、读档恢复、拥有者收到状态和到期使用 OnChanged；其余沿用 0.1 秒显示刷新。不接管鼠标/键盘焦点，悬停仍通过既有左 Alt 鼠标模式。

实现范围：FPSSurvivalTypes/Component、ColdSteelWorldInteraction、PlayerController 的 E 分派、档案同步与合法性、StatusEffectsComponent/HUD、status_effects.json。无需修改喷泉资产或保存关卡。按用户规则只进行必要后台构建，不运行游戏、测试、截图或验收。

本轮源码、目录配置及基础二进制均已落盘。用户保存并关闭编辑器后，通过 Tools/Build/Build-SurvivalHUD20261003.ps1 完成常规 FPSGAMEEditor/FPSGAME Win64 Development 构建，两目标均返回 Result: Succeeded；分别链接 UnrealEditor-FPSGAME.dll 和 FPSGAME.exe。日志为 Saved/BuildSurvival20261003/FPSGAMEEditor-20261003-094755.log、FPSGAME-20261003-094802.log。最初 GetPawn() 的 TObjectPtr 自动类型推导错误已改为显式 APawn* 并补编译成功。新增生存状态字段未进行热补丁，本任务未启动、关闭或重启编辑器，未运行游戏、测试、截图或验收。
