# Slate 文字绘制非法写入修复 · 2026-10-13

## 场景与证据

用户报告 EXCEPTION_ACCESS_VIOLATION writing address 0x0000000400000008。对应 Saved/Crashes/UECC-Windows-C3B011C346DAE28AF73DA7B3729A16A8_0000，记录时间 12:03:31，崩溃记录的引擎版本为 5.8.3-58210709。用户后续确认触发操作为“打开铁匠工作面板”。正常预期是打开铁匠面板后仍能绘制配方下拉框；实际在 GameThread 的 Paint 阶段崩溃。日志尾部为同时打开的背包；本轮不启动游戏复现。

离线读取现有转储及本机 Slate 二进制：

- 首帧 Slate+0x9454f 为画刷复制中的 `lock inc [rax+8]`，转储 RAX=0x400000000，与用户错误地址准确吻合。
- 上层 Slate+0x44a4e9 对应 STextBlock 更新计算样式时复制 StrikeBrush；再上层 Slate+0x4314d1 位于 STextBlock::OnPaint。父调用含 SButton 与 SMenuAnchor。
- 文本控件 0x2b80f872a10 的外部 StrikeBrush 指针为 0x2b80f8821c0，其引用计数字段已失效。首要问题是被 Slate 保留的文字仍引用无效画刷，不能据此归咎于 GPU 或木工切割几何。
- UComboBoxString::HandleGenerateWidget 只保留生成对象的 TakeWidget()。打铁 GenerateRecipeOption 返回未挂入根控件树的 USizeBox/UTextBlock，Labels 也仅为弱引用；GC 后 Slate 仍可绘制并访问 UTextBlock 的 StrikeBrush。此实现与转储故障路径及用户确认的铁匠面板触发操作吻合。

证据与修改前备份：Saved/SlatePaintCrash20261013。原崩溃文件保留原位。

## 修复与 UI 合同

- 打铁配方选项复用枪械组装/普通制作已经使用的 UColdSteelGunRecipeOptionWidget。它是拥有自身 WidgetTree 的 UUserWidget，TakeWidget 生成的 SObjectWidget 在 Slate 使用期间持有 UObject，选中项和展开列表共用这条生命周期路径。
- 面板仅用弱引用数组记录选项，以便 DPI 改变时更新字号/行高；生成新行及 DPI 改变时移除失效引用。不新增永久持有缓存或每帧重建。
- 保留 14px 居中单行文字、标准操作高度、现有配方选择事件及打铁材料/工件/结算合同；本次不改变布局和存档/联机数据。
- 修改限于 ColdSteelForgingWidget.h/.cpp，保留其他并行修改；不修改引擎或用空画刷掩盖悬空引用。

## 构建与交付边界

源码与两个目标均已落盘：常规 Editor 构建成功（Editor-build-ready2.log，退出码 0），UnrealEditor-FPSGAME.dll 与 UnrealEditor-ColdSteelNet.dll 已链接；Game 构建成功（Game-build-ready2.log，退出码 0），FPSGAME.exe 已链接。日志、产物时间与散列见 Saved/SlatePaintCrash20261013/delivery.json。没有打开 UE、启动游戏、强制 GC 或运行自动测试。离线崩溃定位属于本次用户要求的修复工作；编译成功不代表实机崩溃已复测消失，交由用户再次打开铁匠工作面板确认。

构建期间遇到并行代码的 UHT 阻塞，按最小范围处理：

- ColdSteelShopWidget.h：为反射事件 SaleQuantityCommitted 的参数补名称，不改变签名类型。
- FPSStatusReplicationComponent.h：原先逗号并列属性声明已由并行修改拆开，本轮保留现状，没有修改此文件。
- ColdSteelInventoryRequestTypes.h / ColdSteelShopModel.cpp：RPC 请求不能包含 TMap，交易明细改用包含物品 ID 与数量的反射结构体数组，并同步组装请求的单处调用；保留既有服务器交易检查与结算。

第一次和第二次失败日志分别为 Editor-build.log、Editor-build-02.log。第三次 Editor-build-03.log 记录 NurseZombie 的不存在成员调用及 FPSWeatherManager 的变量遮蔽；开始修改前并行代码已经修正这两处，本轮保留修正，不覆盖源码。已有其他构建运行时等待其结束，不中断进程或跨对话协调。

Editor-build-final.log：铁匠面板修改进入编译；整轮因并行修改过程中的 ColdSteelPickupStudio.h / MonsterBTNodes.h 与生成代码行号不一致、地牢头文件更新时序而失败。地牢缺失声明在读取时已补上，未覆盖相关源码，仍需重新生成反射代码并完成构建。

恢复构建前曾发现 FPSGAME 编辑器重新启动（PID 66176，LiveCodingConsole PID 63644），按用户要求保留现场，没有启动第二个编辑器或强制关闭进程。用户再次确认关闭后，继续常规构建；其间的导航/裂隙斩新反射类型及参数重名错误由并行源码修正，保留最新源码后完成了上述 Editor 链接。
