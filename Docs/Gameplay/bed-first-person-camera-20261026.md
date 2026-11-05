# 床铺与坐椅第一人称镜头避让、进出衔接

用户要求开发上床、躺卧时的第一人称摄像机，参考站立待机低头看脚的视角，避免看到上半身开口和模型内部，并自然衔接。随后追加坐椅动作同步调整；本轮将相机处理接到全部已配置坐姿，不重做已制作的身体动画。

## 原有路径

`FPSPlayerFirstPersonBody.cpp` 的站立镜头使用向前偏移、低头附加偏移、躯干前方净距和半径 6 cm 的环境扫掠。家具期间该路径提前返回；`FPSFurnitureRestComponent::ApplyCamera` 随后直接使用动画眼点。床铺就位还会在动作前移动角色，因此原镜头没有保留下来参与这一段衔接。

## 本次实现

- 保留各身体已有的家具眼点轨迹和动画时钟。新增 `FPSFurnitureRestCamera.cpp`，调整本机家具第一人称的最终 POV。
- 从当前原生骨架绑定姿态缓存胸部前方／上方轴，使用实际躺卧骨姿态转到世界空间。身体资产切换时重建缓存，不把男性骨轴直接用于女性。
- 镜头沿胸口外侧避让骨盆、胸和颈部。直立阶段沿用 40 cm 躯干净距；躺平时过渡为 24 cm，朝身体看时增加到 32 cm。朝脚或胸口看时，镜头最多沿身体向脚侧移动 20 cm，越过颈口；抬头看房间时回收这段偏移。参数是相对骨骼中心线的制作值，不是实际蒙皮表面的碰撞测量。
- 坐姿保持原头部眼点高度，沿胸前方向避让；低头看腿时净距由 40 cm 平滑增加到 48 cm。座椅与沙发后靠仍按坐姿处理，不触发卧姿的向脚侧位移。
- 沿用 6 cm 球形环境扫掠，床架、墙与上铺仍限制可用镜头空间。没有修改身体网格、服装、裁切材料或站立低头配置。
- 上床／坐下前缓存最后显示的第一人称位置，在原 0.6 秒就位阶段平滑接到家具镜头；进入、坐卧保持和起身继续使用原眼点采样。退出后用 0.35 秒接回普通镜头的实时低头偏移。
- 10 月 26 日第一版保留鼠标自由转头；该行为已由下方 10 月 27 日的躯干相对转头范围替代。第三人称观察沿用原路径。

使用家具类型的 `lying` 标识覆盖 Bed、BedKing、Hospital、Ward、Bunk、ApartmentBed，不按床模型名称另写分支。休息阶段、占位、服务器时钟、进出床位置和第三人称动作未改。

坐姿覆盖 Chair、Chair50、Chair52、Chair53、Chair55、Bench、Sofa、SofaLeft、SofaRight、ApartmentSofa、ApartmentSofaLeft、ApartmentSofaRight。共用坐姿进出衔接，不新增第二套输入、动作时钟或动画资产。

## 落盘与构建

源码修改范围为 `FPSFurnitureRestComponent.h/.cpp`、新增 `FPSFurnitureRestCamera.cpp` 和 `FPSPlayerBodyCamera.cpp` 的调用。修改前副本位于 `Saved/TaskBackups/BedFirstPersonCamera20261026`。

床铺第一版构建记录位于 `Saved/BedFirstPersonCamera20261026`，当时 Game 构建成功，Editor 因编辑器占用未执行。用户随后保存并关闭编辑器。本轮没有使用热补丁更换组件布局。

追加坐姿后的备份位于 `Saved/TaskBackups/FurnitureFirstPersonCamera20261026`，本轮交付回执为 `Saved/FurnitureFirstPersonCamera20261026/delivery.json`。最初 Game 构建因共享 UI 源码更新后反射头尚未更新而失败，失败日志保留在 `FPSGAME-before-editor-console.log`，不将它当作成功结果。

随后共享工程已完成当前源码的常规 Editor／Game 构建，两个退出码均为 0。复用 `SourceAssets/WoodSteelLongbow20261026/BalanceV5/build-FPSGAMEEditor.json` 和 `build-FPSGAME.json` 所记录的共用构建：Editor 于 2026-10-26 22:57:12、Game 于 22:59:41（北京时间）完成。家具镜头及组件对象文件晚于本轮源码修改，最终 DLL／EXE 晚于相应对象文件。两目标产物分别为 `Binaries/Win64/UnrealEditor-FPSGAME.dll`、`Binaries/Win64/FPSGAME.exe`。

排队期间保留了既有烘焙、编辑器和其他原生编译；确认共用构建已覆盖本次修改后，撤下重复构建队列。未发送跨对话协调消息，未终止其他进程。

未启动编辑器或游戏，没有执行测试、截图、渲染或视觉验收。不同床型、身体、衣物及极端转头的最终效果由用户在游戏中体验。

## 2026-10-27：坐卧时的头部活动范围

用户反馈第一版仍可任意转动镜头，要求符合正常人的头部转动范围。本次将家具第一人称鼠标输入改为躯干局部坐标中的转头，参数作为游戏舒适度调校值，不作为医学活动范围测量。

- 坐姿：左右各 70°，低头 55°、抬头 35°；卧姿：左右各 60°，向胸／脚方向低头 45°、向头顶方向抬头 15°。角度均相对当前躯干的前方与上方，躺平的自然前视朝向天花板。
- 侧头越大，上下范围越小；到左右极限时上下范围为正视时的 60%，避免同时把左右与上下活动推到最大。边界前 12° 逐渐降低向外转头速度，反向输入立即响应，越界输入直接丢弃。
- 胸部姿态提供相机参考轴，0.12 秒响应滤去微小动作噪声。进入时用 0.6 秒从原视角过渡到限定范围；起身后用 0.35 秒消去剩余倾斜并接回普通镜头，期间保留新的鼠标输入。
- `FPSGAMEPlayerController::UpdateRotation` 在家具第一人称时消费局部转头输入，避免躺平视角被普通世界坐标俯仰上限截住；第三人称和非家具状态继续使用原控制器路径。
- 沿用上一版的镜头位置避让、眼点轨迹、床型与座椅覆盖，不改身体动画、休息时钟或联机状态。

本轮源码：`FPSFurnitureRestCamera.cpp`、`FPSFurnitureRestComponent.h/.cpp`、`FPSGAMEPlayerController.h/.cpp`。修改前备份在 `Saved/TaskBackups/FurnitureHeadLook20261027`；构建记录保存在 `Saved/FurnitureHeadLook20261027`。用户保存并关闭编辑器后，本轮常规 `FPSGAMEEditor` 与 `FPSGAME` 构建均已成功，退出码为 0，产物已更新到 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 和 `Binaries/Win64/FPSGAME.exe`。第一次失败日志另存为 `first-attempt-FPSGAMEEditor*`，最终结果见两目标的 `*-result.json` 和 `delivery.json`。未运行游戏或进行视觉测试，由用户体验。

构建所需的最小语法修正：`FPSImpactFXSubsystem.h` 将同一行的两个静态常量拆开声明，以消除 MSVC 导出类成员 C2487；`FPSImpactFXBleeding.cpp` 去掉 `FVector::ForwardVector` 后的函数调用括号，消除 C2064。两个常量的值和血液效果逻辑保持原值，修改前文件一同备份。
