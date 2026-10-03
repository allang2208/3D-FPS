# 唐刀剑身Ⅱ符文覆盖层修复

用户反馈表面优化后，共鸣、侵蚀、导魔三种剑身Ⅱ符文消失。

原因是四款刀刃开启 Nanite，SurfaceV2 又补齐了 Nanite 用途标记，刀刃走入 Nanite 渲染路径。三种符文仍通过 `M_SilverRuneSurfaceV2` 的半透明 OverlayMaterial 显示，该覆盖层与这条渲染路径不兼容。符文分类仍能识别 `M_TangDaoSurface`，目录中符文投射尺寸仍在，符文遮罩和材质没有被配重锤修复删除。实际资产读取见 `state_before.json`。

Epic 技术支持对 Nanite 覆盖层的说明与替代路径：[Overlay Material + Nanite](https://forums.unrealengine.com/t/overlay-material-nanite/2745196)。本项目使用普通静态网格绘制刀刃来保留现有半透明覆盖层，不修改引擎或共享符文材质。

已在现有 UE 桥的一次互斥批次中关闭四个刀刃资产的 Nanite，并实际保存：原装 `factory`、加长 `extended_edge`、轻刃 `feather_edge`、厚脊 `heavy_spine`。路径、网格几何、材质槽、4K PBR、刀的前后朝向、攻击配置与陨星锤体修复均保留。护手、握把、配重和世界整刀的渲染配置保持原状。

`import_tang_dao.py` 同步保留此刀刃策略，重新导入不会再次启用刀刃 Nanite。`apply_rune_repair.py` 是本次资产更新入口；`import_receipt.json` 的 `complete` 为 true，实际保存四个资产。执行结果为 `apply-bridge-01.json`，退出码 0。原资产备份在 `Before`。

没有运行游戏、触发测试、截图或验收渲染。符文显示效果由用户重新装备唐刀后自行测试。

后续用户确认符文仍未显示：本目录回执证明 Nanite 设置已保存，不能作为视觉故障已解决的证据。继续排查确认实际渲染数据也不含 Nanite，装配参数完整；后续转为唐刀专用刀身表面发光，见 [继续排查与修复](../RuneRepairFollowup20261002/README.md)。
