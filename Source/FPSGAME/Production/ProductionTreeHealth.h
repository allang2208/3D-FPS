#pragma once
#include "CoreMinimal.h"

struct FProductionResource;
struct FProductionToolStats;

/**
 * 树木生命值（2026-09-25 用户要求：树木像怪物一样有血量，斧头按伤害扣血，血量归零才倒下）。
 *
 * 口径（唯一权威，浮窗、图鉴、提示栏与结算都读这里，不各自换算）：
 *  - 生命上限 ＝ 树种基础生命（A–D）× 实例尺寸系数；尺寸系数由候选点缩放（.68–1.08）映射到 .85–1.25；
 *  - 一次挥砍的伐木伤害 ＝ 工具伤害面板（含改造、附魔与角色物攻）× 「所需有效命中」改造折算倍率。
 *    出厂 3 挥改成 2 挥（`harvest_hits_add=-1`）即 ×1.5，形态上等于多打半次；
 *  - 树不吃暴击与弱点，挥砍数与提示栏一致，不做随机浮动；
 *  - 剩余生命以**比例**存进角色档：调整基础生命不会作废旧档，也不需要迁移遍历。
 *
 * 只有树木与岩块走生命值口径（2026-09-30 起岩块同样按伤害扣血，命中数结算退役；
 * 表土仍按「一挥一层」的固定挖掘）。结算分支按 `MaxHealth>0` 分流。
 *
 * 性能：全部是常量表与一次 CVar 读取，不新增 Actor、Tick、射线、资源加载或存档往返；
 * 调用点只有「一次挥砍」与「0.15 s 一次的瞄准提示」。
 */
namespace ProductionTreeHealth
{
    /** 树种基础生命（下标＝`ProductionHarvestAssets::TreeVariant`，A–D）。出厂伐木斧约 3–5 挥；改这里调平衡。 */
    FPSGAME_API double BaseHealth(int32 Variant);
    /** 树木生命上限（≥1，已含尺寸系数与整体倍率）。非树木资源不会调用本函数。 */
    FPSGAME_API double MaxHealth(const FProductionResource& Resource);
    /**
     * 树桩生命上限（2026-09-28 用户要求"树桩也有生命数值，砍尽掉一块木材"）：
     * ＝ 同一棵树立满了生命的一半，出厂斧 A 树桩 2 挥、D 树桩 2–3 挥。
     * 进度按比例存 `FColdSteelTreeGrowth::StumpHealthRatio`，与树一样调参不废旧档。
     */
    FPSGAME_API double StumpMaxHealth(const FProductionResource& Resource);
    /**
     * 岩块生命上限（2026-09-30 伤害驱动统一）：基础 60 ＝ 出厂十字镐标定伤害约 20/挥 × 旧的
     * 「三次有效命中」；矿石岩块与普通石块同血，与旧口径逐次对应。岩块尺寸来自 PCG、
     * 没有树那样的固定缩放带，因此不做尺寸浮动。
     */
    FPSGAME_API double RockMaxHealth();
    /** 一次挥砍的伐木伤害（≥1：不会出现砍不动的树）。 */
    FPSGAME_API double StrikeDamage(const FProductionToolStats& Stats);
    /** 剩余生命还要几挥（向上取整，至少 1；生命已归零返回 0）。 */
    FPSGAME_API int32 SwingsToFell(double RemainingHealth,double Damage);
    /** 树木生命值整体倍率（CVar `fps.Harvest.TreeHealthScale`，默认 1）：调平衡不用重编译。 */
    FPSGAME_API double HealthScale();
    /** 岩块生命值整体倍率（CVar `fps.Harvest.RockHealthScale`，默认 1）：调平衡不用重编译。 */
    FPSGAME_API double RockHealthScale();
}