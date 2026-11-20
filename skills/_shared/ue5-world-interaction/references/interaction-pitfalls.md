# 交互问题与环境声案例

按当前问题读取；以下引擎字段、参数与修复来自历史制作，不表示当前已测试。调试与运行检查仅按用户请求执行。 原因：日期化证据只对应当时的输入与修订，不能为当前状态补出不存在的结论。

# Failure Handling
- Symptom: overlap never triggers.
  - Locate: collision enabled state, overlap flags, collision channel responses.
  - Fix: enable overlap generation, set proper channel responses, verify component bounds.
- Symptom: trace path misses obvious targets.
  - Locate: trace channel/profile and ignore actor list.
  - Fix: align trace channel/profile and reduce self/owner ignore misuse.
- Symptom: interaction triggers multiple times.
  - Locate: missing in-progress guard and duplicated delegate bindings.
  - Fix: add state guard and ensure single bind per component.
- Symptom: client sees success but server rejects.
  - Locate: authority checks and RPC validation path.
  - Fix: move final validation to server and replicate authoritative result.
- Symptom: consumed pickup remains interactable.
  - Locate: lifecycle state and collision disable logic.
  - Fix: disable collision/interaction immediately after confirmed success.
- Symptom: spawned interactables leak over time.
  - Locate: spawner bookkeeping and reset cleanup path.
  - Fix: track spawned instances and destroy/disable stale instances on respawn cycle.
- Symptom: frame spikes near dense interaction areas.
  - Locate: per-frame trace/overlap workload and unnecessary ticking.
  - Fix: reduce polling frequency, gate traces by input/distance, disable idle tick.
- Symptom: a dig tool only reaches the ground right at the player's feet.
  - Locate: the tool is still using the melee/production reach (e.g. 3.2 m), so at eye height the ray only meets the ground at a steep downward angle.
  - Fix: give aiming tools their own trace length (project: `fps.Tool.DigReach`), keep the short reach for harvesting, and drive dig/refill from the crosshair ray.
- Symptom: a terrain edit raises the ground where it should sink (or the reverse).
  - Locate: the height delta is already signed (negative = sink) but the call site subtracts it again.
  - Fix: define the edit value as "the delta added to the generated height" and use `+` at every site (height lookup, mesh vertex, numeric normal); one extra negation turns every pit into a mound.
- Symptom: preview ghost or highlight survives after leaving the interaction mode.
  - Locate: cached component pointers kept in file-scope statics (reset by a Live Coding reload), instance buffer cleared but never hidden (or hidden but never cleared), no cleanup on the non-key exit paths.
  - Fix: clear instances + visibility + the rebuild signature cache on every exit path, re-resolve the component by name from a UPROPERTY host when the cache is empty, and add a cheap per-frame safety net while the mode is off.
- Symptom: a material change on the highlight has no visible effect.
  - Locate: material missing the "Used with Instanced Static Meshes" usage flag (the engine silently swaps in the default material), or an unlit emissive left at ~1.0 in a daylight scene.
  - Fix: set the usage flag and push the emissive into HDR range; check the one-line engine warning in the log.

## 持续环境声：喷泉 V9（2026-09-19）

- 水流采用已处理首尾交叉淡化的循环音源和持续 `UAudioComponent`；避免用定时重播或脚步水花模拟连续流动。两层用不同长度及实例相位，进出范围只淡入淡出并保留距离回差。
- 3D 单声道、距离衰减/低通与共享并发预算一起接入；声源不依赖画面可见性。并发替换用释放淡化，被拒绝后限频重试，EndPlay 停止组件。
- UE 5.8 衰减低通字段为 `bAttenuateWithLPF`。并发最大数量可用 `SetMaxCount`；`VolumeScale` 是私有字段，不能直接赋值。 原因：反射字段和访问权限决定合法接口，不能按相似名称直接写入私有属性。
- 记录作者、许可、实际下载版本和处理参数。公开 HQ MP3 与原始 WAV 分开说明；导出 PCM 不代表恢复原始无损质量。资产制作与编译完成不代表已试听。

## 村民交互轮廓与店内受光

村民网格的 Custom Depth/Stencil 由本地视角共享。在 `UResidentHighlightSubsystem` 中给附近店员分配不同的 stencil 槽，按每个视角分别选择焦点轮廓和需要调整亮部的店员。材质使用该视角的选择值，比较场景深度与自定义深度，保留柜台等遮挡物。店内材质只压所选店员的高亮，灯具仍按原亮度照亮地面和通道。

轮廓宽度按视口像素计算；把邻域坐标由 Viewport UV 转成 SceneTexture UV 后，双线性四点采样的纹素间距取 `GetSceneTextureBufferSize` 的倒数。分屏或非对齐画幅中，缓冲区尺寸可能不同于视口。需要复核时用相同入射亮度摆放两名目标、暗部和前景遮挡，分别选中单个、两个和零个目标，比较同一像素；远端 UDP 的装备或交互结果不能说明本机每台摄像机的像素表现。
