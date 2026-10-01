# 百目炉渣黑雾接入修复与竖劈眩晕 V18

用户反馈游戏内没有黑烟，并要求竖劈命中造成 2 秒眩晕。

## 定位

当前磁盘只有 V17 密度纹理；`NS_SlagBlackMist` 与 `M_SlagMistView` 尚未保存。当前编辑器启动日志分别出现 SlagBlackMist 和 SlagMistViewComponent 的 CDO Constructor Failed to find。上一轮资产制作因编辑器正在 PIE 而被保存接口拒绝，这次请求开始时该阻塞仍存在。

先完成原 V17 作者脚本的三项实际资产保存，沿用正式引用路径，避免产生第二套运行资源。保存完成以 `BlackMistV17/asset_installation.json` 为记录；修复版本复制回执至 `BlackMistFixV18/asset_installation.json`。运行组件在首次激活/创建时补充一次缺失引用解析，覆盖编辑器先加载角色类、后制作资源造成的空模板缓存。

## 竖劈眩晕

新增 `SlamStunSeconds=2`，只在下劈的实际伤害命中后调用现有 `UCombatStatusFormula::AddStun`。使用现有攻击命中去重；一次竖劈对同一玩家只触发一次，窗口仍为 0.84–1.00 秒。若伤害调用期间攻击者被格挡反击、控制或杀死，则保留原中断流程；零伤害及已死亡玩家不附加眩晕。状态免疫、输入锁、移动封锁、HUD 提示及到期恢复沿用现有眩晕系统。

普通横扫和激光不新增眩晕。横扫基础倍率 1.25、激光每跳倍率 0.8、下劈伤害倍率 1.4 保持当前源码值；网格、绑定、蒙皮、三个已接入攻击及动画不改动。

## 交付状态

后台产物分开记录：资产保存为 `asset_installation.json`；玩法模块 Editor 基础 DLL 常规构建为 `build_installation.json`。资产制作进程可能在旧 DLL 启动阶段报告待创建资源缺失，保留 commandlet 退出码与日志，不能将其描述成无错误启动；三项实际保存由作者脚本逐项保存并在全部完成后写回执。

依照用户规则保留运行中的编辑器，关闭时机仅询问当前用户。未自动启动 UE、游戏、PIE、截图、渲染或测试；运行表现由用户测试。

本轮最终落盘：用户保存关闭 UE 后，三项资产通过无界面 commandlet 实际保存，退出码 0。常规 `FPSGAMEEditor -Module=FPSGAME` 构建成功，UBT 报告目标已是最新；没有执行 Clean/Rebuild 或运行测试。实际基础 DLL 的生成时间由 `BlackMistFixV18/build_installation.json` 记录，不能把本次构建调用时间写成 DLL 重生成时间。源码与同一基础 DLL 包含竖劈眩晕、缺失模板首次激活解析、V17 数值与 V16 死亡下沉修复。交付汇总为 `BlackMistFixV18/installation_complete.json`。
