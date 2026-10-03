# 图标异步回读与队列优化

用户授权继续优化。依据前一轮同步回读与队首等待的源码证据，本轮实现两项代码优化；没有运行游戏、截图或性能测试。

## 实现

- 新增 `Source/FPSGAME/UI/ColdSteelWeaponIconReadback.cpp`。原运行时 `ReadLinearColorPixels` 已移除，改为最终 Capture 后提交 `FRHIGPUTextureReadback`。只在 GPU 栅栏就绪后读取 staging，主线程不等待栅栏或 FlushRenderingCommands。
- staging 锁定、按行跨度复制和释放在渲染线程；线性半精度像素转 SRGB/反向透明度在工作线程；纹理创建、上传、图标缓存及 OnReady 通知仍在主线程。
- 保留 RGBA16f 输入、现有分辨率、`1-A`、有效像素门槛和图标缓存策略。每次回读绑定配方与尺寸，只有当前任务接收结果；失败或退出时取消接收并排入 GPU 资源释放，后台任务只持有自己的普通数据。
- GPU/转换阶段最多等待 10 秒，超时沿用失败回退，不阻塞或旋转一个正在回读的任务。资源等待阶段单轮上限保持约 10 秒；确认材质/纹理仍未就绪、且有另一项到达可重试时间时，约 2 秒即可让出队首。
- 延期任务按 2/4/6/8 秒冷却，再按排队顺序选择到期任务。全部冷却时不重复装配或捕获。这里的“可调度”指重试时间已到，不表示材质已经就绪。
- 调度上限改用单调墙钟，避免游戏 DeltaTime 被夹紧后，队首实际等待远长于标注时限。
- 离线目录图导出适配异步完成，用至多 30 秒墙钟循环给 GPU/工作线程执行机会；该作者工具原有的阻塞编译/流送等待仍只用于离线导出，没有在本轮执行。

## 观测

JSON 更新为 **schema 6**，增加冷却任务数、下次可调度时间、回读状态与已等待时间，以及已完成的渲染线程拷贝/工作线程转换耗时。未完成耗时导出 null。

新增主线程分段 `Icon.ReadbackSubmit`、`Icon.ReadbackPoll`、`Icon.PublishTexture`。`Icon.ReadbackReady` 完成标记保存拷贝、转换和总历时；后台两项是各自线程的墙钟耗时，不放进主线程嵌套分段，不等同 GPU 执行时间。读回总历时包含排队等待，不能作为整帧 CPU 成本。

界面沿用原图标诊断区域，补充冷却、GPU 回读、后台转换状态；规划见 `Docs/UI/icon-async-readback-plan-20260922.md`。

## 边界与接入

- 这轮目标是移除同步等待、降低图标队首延迟，尚未测量帧数收益。RenderThread staging 映射/复制、GPU 复制和主线程纹理上传仍然有成本。
- 那段约 35 ms 的持续慢帧仍等待新版分段导出归因。已知材质资产错误、缺失目录图和跨 World 加载采样本轮未处理。
- 用户保存关闭项目编辑器后，已完成常规 **FPSGAMEEditor Win64 Development** 构建：207 个动作，`Result: Succeeded`，总耗时 186.34 秒，已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。重新打开项目即可加载新版基础 DLL。未启动 UE 或运行测试，由用户测试。
- 构建参数：`-WaitMutex -NoHotReloadFromIDE -NoLiveCoding -MaxParallelActions=4`；日志为 `Saved/PerformanceDiagnosis20260922/build-editor-icon-async-readback-1.log`。构建中的既有 C4996/C4305 警告未扩大修复；未进行 Game/Shipping 构建或打包。
