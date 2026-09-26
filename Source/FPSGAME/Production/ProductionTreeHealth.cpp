#include "ProductionTreeHealth.h"
#include "ProductionResource.h"
#include "ProductionToolStats.h"
#include "ProductionHarvestAssets.h"
#include "HAL/IConsoleManager.h"

namespace
{
    /**
     * 树种基础生命（A、B、C、D）。标定参考：1 级未加点角色手持出厂伐木斧
     * （武器公式 ≈12 ＋ 角色物攻 ≈10 ＝ 22/挥）砍 A 树 3 挥、D 树 5 挥，
     * 与旧的「三次有效命中」手感接近；尺寸系数与改造再在其上浮动。
     */
    constexpr double BaseHealthByVariant[4]={60.,72.,84.,96.};
    /** 候选点缩放区间（`ATemperateHillsWorld::TreeCandidate`）与对应的生命系数区间。 */
    constexpr double PlacementScaleMin=.68,PlacementScaleMax=1.08;
    constexpr double SizeHealthMin=.85,SizeHealthMax=1.25;

    // 调平衡用：不必重编译即可整体缩放树木生命值。1 ＝ 出厂。
    static TAutoConsoleVariable<float> TreeHealthScale(
        TEXT("fps.Harvest.TreeHealthScale"),1.f,
        TEXT("树木生命值整体倍率（1 = 出厂）。只影响砍树需要的挥砍数，不改产出与掉落。"));
}

double ProductionTreeHealth::BaseHealth(int32 Variant)
{
    return BaseHealthByVariant[Variant>=0&&Variant<4?Variant:0];
}

double ProductionTreeHealth::HealthScale()
{
    return FMath::Clamp(double(TreeHealthScale.GetValueOnGameThread()),.05,100.);
}

double ProductionTreeHealth::MaxHealth(const FProductionResource& Resource)
{
    // 未知树种（含以后新增的第五种）按 A 树结算，不因为目录没登记就变成砍不动。
    double Health=BaseHealth(ProductionHarvestAssets::TreeVariant(Resource.Mesh));
    const double Size=FMath::Abs(Resource.Transform.GetScale3D().Z);
    const double T=FMath::Clamp((Size-PlacementScaleMin)/(PlacementScaleMax-PlacementScaleMin),0.,1.);
    Health*=FMath::Lerp(SizeHealthMin,SizeHealthMax,T);
    return FMath::Max(1.,Health*HealthScale());
}

double ProductionTreeHealth::StrikeDamage(const FProductionToolStats& Stats)
{
    // 自卫伤害面板就是伐木伤害：改造、附魔、强化与角色物攻都已经在里面。
    const double Panel=Stats.Damage.Total();
    // 「所需有效命中」改造折算成伐木伤害倍率：出厂 3 挥 → 2 挥 ＝ ×1.5，正好抵掉一次挥砍。
    // 这样工作台与浮窗的「所需有效命中」在标定伤害下仍然逐次对应实际挥砍数。
    const int32 Factory=FMath::Max(1,FProductionResource::RequiredHits);
    const double Factor=double(Factory)/double(FMath::Max(1,Factory+Stats.HarvestHitsAdd));
    return FMath::Max(1.,Panel*Factor);
}

int32 ProductionTreeHealth::SwingsToFell(double RemainingHealth,double Damage)
{
    if(RemainingHealth<=0.)return 0;
    return FMath::Max(1,FMath::CeilToInt(RemainingHealth/FMath::Max(1e-6,Damage)));
}