# 保留预览 World 时释放渲染场景

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-debug-validation/references/preview-scene-lifecycle.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 生命周期合同

详见[维护源](../../_shared/ue5-debug-validation/references/preview-scene-lifecycle.md)中的同名章节。

## 诊断与结论边界

详见[维护源](../../_shared/ue5-debug-validation/references/preview-scene-lifecycle.md)中的同名章节。

## 独立游戏退出时的 instanced skin 清理

UE 5.8 丘陵退出案例中，SkinningSceneExtension 的批次移除仍需读取旧 MeshObject / skeleton；组件先排入延迟销毁后再做场景更新会访问已释放资源。`FPSGameSceneLifecycle` 在 OnWorldBeginTearDown、ClearWorldComponents 之前，仅收集该 Scene 仍注册且有 proxy 的 InstancedSkinnedMeshComponent，批量移除并提交一次场景更新，再等待渲染命令完成。随后保留引擎正常组件注销；不把 flush 放进每帧，也不关闭风动或蒙皮来隐藏错误。

该修复基于本机引擎调用顺序；升级引擎先确认仍有相同的生命周期依赖。功能结果、正常 RequestExit 的进程退出码与用户中止分别记录。用户要求暂停而停止隔离测试进程，不算正常退出通过，也不算新出现的渲染崩溃。
