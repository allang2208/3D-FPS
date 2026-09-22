#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSkillRules.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/RuneSwordCombatTuning.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "Engine/GameInstance.h"

FDashAttackCast UColdSteelStatusModel::DashAttackStats(int32 AtLevel) const
{
    const auto& D=MasteryDefinition(TEXT("dashAttack"));const auto& T=D.DashAttack;
    const int32 L=FMath::Clamp(AtLevel<0?MasteryProgress(D.Id).Level:AtLevel,1,D.MaxLevel);
    FDashAttackCast C;
    C.DamageMultiplier=T.DamageBase+L*T.DamagePerLevel;
    C.ReadySeconds=FMath::Max(.01f,T.ReadySeconds*(1.f-(L-1)*T.ReadyReductionPerLevel));
    C.StaminaCost=T.StaminaCost;
    C.DistanceCM=FMath::Max(0.f,T.Distance);C.BounceRatio=0.f; // 距离直接使用厘米，不套用旧版范围换算。
    C.RangeBonusCM=(T.RangeBase+L*T.RangePerLevel+T.RangeFlat)*T.UnitsToCM;
    C.KnockbackBonusCM=(T.KnockbackBonus+L*T.KnockbackPerLevel)*T.UnitsToCM;
    // 当前下劈固定为前方左右各30度；也覆盖热更新前已缓存的旧120度定义。
    C.ArcDegrees=60.f;
    const auto* Item=Equipped();
    if(Item&&!ActiveProductionTool()&&ColdSteelInventory::IsMeleeWeapon(*Item))
    {
        const auto Stats=ColdSteelMelee::Evaluate(*Item,this);
        C.Damage=FMath::FloorToFloat(Stats.Damage*C.DamageMultiplier);
        // 使用当前 UE 兵器的基础有效射程；原技能额外距离只换算一次。
        C.RangeCM=(RuneSwordCombatTuning::ScaledReach(Stats.BaseReach)+C.RangeBonusCM)*Stats.Modifiers.Range;
        C.KnockbackCM=Stats.KnockbackCM+C.KnockbackBonusCM;
        const auto* Enhance=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();
        const double CostDelta=Enhance?Enhance->CraftEffect(*Item,TEXT("skillStaminaCostDelta")):0.;
        C.StaminaCost=FMath::Max(0.f,float((T.StaminaCost+CostDelta)*Stats.Modifiers.Stamina*ColdSteelMelee::TemporaryModifiers(this).Stamina));
    }
    return C;
}

void UColdSteelStatusModel::TrainDashAttack(int32 Hits,int32 Kills)
{
    const auto& D=MasteryDefinition(TEXT("dashAttack"));
    const int32 XP=Hits*D.HitExperience+(Hits>=2?D.MultiHitExperience:0)+Kills*D.KillExperience;
    if(XP<=0||MasteryProgress(D.Id).Level>=D.MaxLevel)return;
    SyncRuntime();auto P=Snapshot();ColdSteelSkills::AddExperience(P,D,XP);CommitState(P);
}
