# M25 连续软体死亡挂接

`soft-corpse-hook.patch` 保存本机 M25 对独立全怪物软体死亡系统的挂接。它不是完整的软体实现；应用前需先恢复 `UMonsterCorpseRagdollComponent::TryStartSoftDeath`、相关数据类型和当前网格的软体绑定。

本机该行和已保存资产保持原样；本轮公共 M25 源码使用原死亡动画。后续系统发布时再应用挂接，避免把未公开 API 直接加入当前公共编译链。地牢刷新不在本次接入范围。
