# 锁子甲袖口黑圈修正（2026-09-29）

用户持弓截图中袖口有一圈深色外露。活动 ChainmailSharedSway20260929 从 Interlace 母版继承了额外的 DarkBinding 实体卷边：宽 7 mm、最高高出锁子甲表面 0.75 mm。它与内衬共用深色材质，外凸轮廓容易形成类似内衬穿出的黑圈。

新家族 ChainmailInsetBinding20260929 只改这圈额外卷边：宽 2.2 mm，最外层位于原锁子甲表面以内 0.4 mm，端头向袖内退 0.8 mm。保留闭合截面，不删除内壁或端面；金属环与内衬本体、UV、原生蒙皮权重、拓扑以及前一轮 WristCoverage 腕部皮肤底面不变。

在 M4 作者母版处理这两个 96×6 的包边环，使用原有原生绑定矩阵传递位置增量与法线，其他顶点不移动。单手版本沿用原左右侧映射，21 个第一人称版本使用相同修改。复用当前共享摆动材质和顶点遮罩，保留无 Chaos 的现有运动方式。第三人称 Body 不改。

制作／导入／发布入口：
- Tools/ModularOutfit/build_chainmail_inset_binding.py
- Tools/ModularOutfit/import_chainmail_inset_binding.py
- Tools/ModularOutfit/publish_chainmail_inset_binding.py

源数据与保存回执在 SourceAssets/ChainmailInsetBinding20260929；UE 资产另存于 /Game/Characters/ModularOutfit20260924/ChainmailInsetBinding20260929。全部保存后只替换锁子甲第一人称引用，不覆盖旧资产或手套家族。

按用户请求排查并调整了外凸包边。未做修改后的游戏运行测试；截图不能排除特定动作下其他局部穿模，实际弯腕效果由用户测试。
