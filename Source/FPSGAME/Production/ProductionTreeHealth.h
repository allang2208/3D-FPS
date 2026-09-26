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
 * 只有树木走生命值口径。岩块与表土仍是原有命中数口径（`FProductionResource::MaxHealth==0`），
 * 以后要让岩块也吃伤害，把上限填上即可，结算分支已经按上限分流。
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
    /** 一次挥砍的伐木伤害（≥1：不会出现砍不动的树）。 */
    FPSGAME_API double StrikeDamage(const FProductionToolStats& Stats);
    /** 剩余生命还要几挥（向上取整，至少 1；生命已归零返回 0）。 */
    FPSGAME_API int32 SwingsToFell(double RemainingHealth,double Damage);
    /** 生命值整体倍率（CVar `fps.Harvest.TreeHealthScale`，默认 1）：调平衡不用重编译。 */
    FPSGAME_API double HealthScale();
}