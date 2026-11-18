# 场景几何成本与 LOD 收敛（2026-09-23）

本页收敛为仓库内发布快照入口：[完整规则与逐条原因](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)。

- 共用规则在个人维护源修改，获授权发布时更新上述快照；工程专属增补仍写在对应工程文档。原因：同一规则保留两份正文会在后续修订时重新分叉。
- 当前入口已包含仓库内发布快照，换机时按快照清单恢复所需资料。原因：仓库相对链接不依赖个人目录，快照仍需与本次发布版本对应。
- 下列原章节名只保留旧链接定位，不代表额外执行步骤。原因：已存在的章节引用需要继续落到可识别的位置，执行规则仍以维护源为准。

## 1. 性能面板的 `all_rank_total` 是 LOD0 口径，看不出 LOD 效果

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 2. 组件数量不能单独确定瓶颈

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 3. UE 5.8 生成 LOD 链的正确调用

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 4. 大面积平铺件需要适合其包围体的 LOD 策略

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 5. 地板阴影取决于实际遮挡作用

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 6. 密集装饰资产不要铺满大范围——先看面数密度

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。

## 7. 交付口径

详见[维护源](../../_shared/ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)中的同名章节。
