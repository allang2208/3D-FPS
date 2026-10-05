# M25 连续软体死亡挂接

2026-10-05 连续软体系统随后发布时，已将此挂接并入 `M25Damage.cpp`。以下保留 M25 初次发布的依赖说明，不需重复应用补丁。当前制作与保存范围见 [通用死亡标准](../continuous-soft-corpse-standard-20261005.md)。

`soft-corpse-hook.patch` 保存本机 M25 对独立全怪物软体死亡系统的挂接。它不是完整的软体实现；应用前需先恢复 `UMonsterCorpseRagdollComponent::TryStartSoftDeath`、相关数据类型和当前网格的软体绑定。

本机该行和已保存资产保持原样；本轮公共 M25 源码使用原死亡动画。后续系统发布时再应用挂接，避免把未公开 API 直接加入当前公共编译链。地牢刷新不在本次接入范围。
