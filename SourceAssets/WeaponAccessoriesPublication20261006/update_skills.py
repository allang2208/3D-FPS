"""Append scoped production lessons to the project and personal skill copies."""
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROOTS = (PROJECT / 'skills', Path('C:/Users/allan/.codex/skills'))
NOTES = {
'ue5-weapon-workflow/references/attachment-fit-and-emission.md': '''# 瞄具开窗、镭射发光与逐枪接口

## 瞄具看起来黑而不透明

先看镜体与镜窗是否共用材质槽。若原模型依赖贴图 Alpha 的 Masked 开窗，用普通金属材质替换整个槽会封死镜窗；恢复原 UV 通道、遮罩和裁切阈值，保留分划独立材质。雨水动态材质也要继承同一遮罩，且全量与局部重导入共用制作助手，避免重导入复发。G18 对应 `Tools/Weapons/g18_holographic_material.py`。

## 镭射颜色与外壳碎点

光束偏淡时一起核对透明度、色彩比例与曝光补偿，不调整全局曝光来补一个配件。GPU Time 驱动细丝，实际束长通过实例数据传入，使墙面截断不改变纹理速度；保留深度遮挡和瞄具淡出。发射器外壳上的亮点先查材质发光遮罩：贴图红色或导入后变化的顶点色不能可靠指代镜口。用显式镜口 UV 遮罩或独立镜片材质限定发光，干湿版本共用定义，再判断是否真有几何破洞。

## 新外壳与旧支架接合

不能按面数最多的材质槽推断旧主体，再保留其余全部三角面；旧尾壳、线缆和开关可能位于别的槽。按部件身份选取真正要保留的安装结构。以当前运行枪体、挂接骨和组件变换还原配件空间，再制作局部贴合面。新旧壳的承接截面不同，靠包围盒交叠不能保证贴合；保持 Emitter／AimGuide、光轴、ID 和数值，逐枪改接口。

赐福镭射当前制作入口：`Tools/Weapons/BlessedLaser20261006/author_emitter.py` 与 `fit_mounts.py`，15 枪型装配 V2。`Model/MountRepair/Inputs` 中的旧挂点参数和 M16 夹具源仍是有效依赖，旧完整稿已归档；清理时按读取链区分输入和废案。

## 热成像瞄具的模型边界

电子显示面使用独立图像 UV，不能当作全息透明镜窗。模型阶段拆出镜身、夹轨座、显示面、倍率旋钮和相应接口；模型完成不等于倍率切换、隐身目标或火源高亮已实现。识别视觉隐身的目标遮罩要独立于透明隐身材质，并保留实体墙遮挡。`ThermalScope20261006` 当前仅模型已保存，1.5／3／8 倍和热目标识别仍待接入；第三方热成像项目仅为调研来源，使用前再核对许可与版本。
''',
'ue5-weapon-workflow/references/stocks.md': '''
## 可调式战术后托的肩部凹弧（2026-10-06）

用户指出肩垫缺少人体工学凹弧时，区分横截面圆润与沿高度的接触线：圆角矩形肩垫仍可能纵向近直线。让肩部中段向枪身内收，上下端圆润，并将肩垫、硬背板、包边和相邻托架置于同一个局部曲率场；长直边先补截面，前端安装面保持原位。只弯橡胶而不弯背板会产生跨空或厚度失配。

防滑沟槽随曲面变形，曲面 UV 按周长／弧长和物理平铺尺度展开。橡胶使用独立非金属材质，法线、粗糙度及少量底色变化来自同一模压颗粒源；金属涂层、裸金属和软垫分槽。九把枪分别保留真实前端接口，用实体过渡段接同一母体，不任意缩放整只后托去凑接口。

当前 `legendary_adjustable_tactical_stock` 为 V3，源入口 `Tools/Weapons/LegendaryStock20261006`，说明 `Docs/Weapons/adjustable-tactical-stock-20261006.md`。纯模型精修沿原资产路径、ID、数值与存档更新，交付图标同步重制。V1/V2 废稿在 `trash/weapon-accessories-20261006`，运行资产已保存；未进行 V3 游戏验收。
''',
'ue5-weapon-workflow/references/revolver-mechanical-binding.md': '''
## 展示路径缺少机构层与图标水平基准（RSH，2026-10-06）

装备栏／枪匠预览中的弹巢错位，不一定是模型拆分错误。先核对轻量展示初始化是否在加载私有机构 Profile 前返回；逆绑定网格直接播放供体姿态，会让枪身和弹巢分别处于两套装配坐标。展示初始化应清理上一枪 Profile，并加载本枪必要基础机构层，同时仍跳过音效和战斗资源。修改配方后更新图标缓存键。

水平图标的依据是实际枪管／机匣轴。为 ADS 调过的前后瞄点连线不能直接当作图标水平轴；RSH 使用本枪枪口安装旋转转换到 WPN_root 的物理坐标，不改实战 ADS 或挂点。图标生产沿用当前 UE 装配、机构层与材质，避免另用原始 FBX 粗绘一套近似外观。

本次没有发现需要重拆弹巢的依据。当前换弹机构、手部接触、补弹和声音仍共用原源时钟；离线接触计算与游戏体验分开记录。见 `Docs/Weapons/rsh12-mechanical-presentation-20261006.md`。
''',
'ue5-fps-arms-animation/references/food-and-drink-grasp.md': '''
## 持武器时腾出左手（2026-10-06）

消耗品不要直接复用施法的左手占用判断。按实际装备家族区分可让出的姿势（ADS、格挡、检视、弓的持弦）与必须等结束的动作（攻击、换弹、装备、施法）。背包暂时隐藏的武器仍拥有自己的手模；按装备归属解析，不能遍历可见网格来挑备用手臂。

共用入口为 `CanBeginConsumableUse`／`PrepareForConsumableUse`／`ConsumableHands`。先确认物品与动作资源，保留物品实例 ID，再关闭背包并让出姿势。取消拉弓保留已搭箭；清除瞄准按住意图，避免下一帧重新举枪。双持左枪先整组放低，再隐藏武器并饮用，最后恢复原握姿抬回；新增前置过渡不能提前触发扣物品、接触和吞咽音效。

食品、水和药水继续走同一接触事务。专用状态检查工具只在用户要求排查时使用；历史 83 项通过属于 2026-10-06 的隔离状态检查，不能代替游戏按键／画面与库存实测。详见 `Docs/Items/consumable-weapon-handoff-20261006.md`。
''',
'ue5-fps-arms-animation/references/quick-melee-contact-recovery.md': '''
## 播放提速要同步占用与命中（M4，2026-10-06）

先确认实际加载顺序：共用握姿 Profile 的 quick_melee 可能优先于旧动画路径。读取选中的片段长度和 RateScale，再区分出手慢、长收势和多余状态锁定；不要只调序列 RateScale，显式时间采样可能根本不消费它。

统一提速时保留源姿态与源时钟，播放时长为 `源长度 / 播放倍率`。近战组件的阶段／接触时间、武器忙碌时长和收势混合使用同一播放时长，显式动画及差量采样使用 `播放经过时间 * 播放倍率`。不要仅缩短状态或仅加快画面。确认改动归属时避免用跨枪共用的 `bUsingM4Infima` 标志扩大范围。

M4 Base／Drum／Angled／Vertical／Canted／Prism 六份源仍为 0.9 秒；当前 `A_M4_QuickCombat_` 家族在运行入口以 1.5 倍播放，实际占用 0.6 秒、接触约 0.111 秒。作者动作未改，无需重制差量；若将来修改源姿态或源时长则按动画共享流程重制 Profile。Editor/Game 构建成功，尚无本轮游戏手感验收。见 `Docs/Weapons/m4-quick-melee-timing-20261006.md`。
'''
}
for root in ROOTS:
    for relative, note in NOTES.items():
        path = root / relative
        current = path.read_text(encoding='utf-8') if path.exists() else ''
        if note.strip().splitlines()[0] not in current:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(current.rstrip() + '\n\n' + note.strip() + '\n', encoding='utf-8')
    entry = root / 'ue5-weapon-workflow/SKILL.md'
    current = entry.read_text(encoding='utf-8')
    route = '- 瞄具黑窗、镭射外壳碎光、新壳旧支架残留或热成像模型边界：[瞄具开窗、镭射发光与接口](references/attachment-fit-and-emission.md)。按材质遮罩、真实安装面和功能阶段分别处理。\n'
    if 'references/attachment-fit-and-emission.md' not in current:
        anchor = '- 制作或修改改造配件：'
        at = current.index(anchor)
        current = current[:at] + route + current[at:]
        entry.write_text(current, encoding='utf-8')
print('Updated five reference pages and one route in both skill roots.')
