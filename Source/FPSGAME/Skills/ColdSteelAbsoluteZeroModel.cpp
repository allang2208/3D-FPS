#include "../UI/ColdSteelStatusModel.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSpellRewards.h"
#include "ColdSteelSpellCrafting.h"
#include "ColdSteelSpellFeedback.h"
#include "AbsoluteZeroDamage.h"
#include "FPSIceArmorComponent.h"
#include "HolyLightTargets.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::AbsoluteZeroProgress() const
{return Current.Skills.FindRef(TEXT("absoluteZero"));}
float UColdSteelStatusModel::AbsoluteZeroCooldown() const
{return HasNoAbilityCooldown()?0.f:Current.AbsoluteZeroCooldown;}
float UColdSteelStatusModel::AbsoluteZeroCooldownDuration() const
{return Current.AbsoluteZeroCooldownDuration;}

FAbsoluteZeroCast UColdSteelStatusModel::AbsoluteZeroStats(int32 AtLevel) const
{
    const auto& D=AbsoluteZeroSkill;const auto& T=D.AbsoluteZero;
    const int32 L=FMath::Clamp(AtLevel<0?AbsoluteZeroProgress().Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    const int32 K=L-1;
    const float MAtk=Derived(TEXT("matk"));
    FAbsoluteZeroCast C;
    C.Damage=FMath::FloorToFloat(T.DamageBase+K*T.DamagePerLevel+MAtk*(T.MagicBase+K*T.MagicPerLevel));
    C.ShatterDamage=FMath::FloorToFloat(T.ShatterDamageBase+K*T.ShatterDamagePerLevel+MAtk*(T.ShatterMagicBase+K*T.ShatterMagicPerLevel));
    C.WallShardDamage=FMath::FloorToFloat(T.WallShardDamageBase+K*T.WallShardDamagePerLevel+MAtk*(T.WallShardMagicBase+K*T.WallShardMagicPerLevel));
    C.Radius=T.RadiusBaseCM+K*T.RadiusPerLevelCM;
    C.InnerRadius=FMath::Min(T.InnerRadiusCM,C.Radius);
    C.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    C.ChannelSeconds=T.ChannelSeconds;
    C.ArmorChannelSeconds=T.ArmorChannelSeconds;
    C.ChannelDamageReduction=T.ChannelDamageReduction;
    C.ArmorChannelDamageReduction=T.ArmorChannelDamageReduction;
    C.ExpandSeconds=T.ExpandSeconds;
    C.KnockbackBase=T.KnockbackBaseCM;
    C.KnockbackMax=T.KnockbackMaxCM;
    C.ToughnessDamage=T.ToughnessDamage;
    C.InnerChillStacks=T.InnerChillStacks;
    C.OuterChillStacks=T.OuterChillStacks;
    C.ChillSeconds=T.ChillSeconds;
    C.ChillBonusPerStack=T.ChillBonusPerStack;
    C.ChillBonusCap=T.ChillBonusCap;
    C.ShatterChillThreshold=T.ShatterChillThreshold;
    C.MaxDetonatedWalls=T.MaxDetonatedWalls;
    C.MaxShardsPerWall=T.MaxShardsPerWall;
    C.MaxFullShardsPerTarget=T.MaxFullShardsPerTarget;
    C.OverflowShardScale=T.OverflowShardScale;
    C.WallShardRange=T.WallShardRangeCM;
    C.WallShardSpeed=T.WallShardSpeedCM;
    C.WallShardConeDegrees=T.WallShardConeDegrees;
    C.bRequiresStaff=T.bRequiresStaff;
    C.CriticalChance=Derived(TEXT("crit"));
    C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1.f+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1.f;
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    float DamageFactor=MagicImplementMultiplier(),CooldownReduction=0.f;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            ColdSteelSpellCrafting::ApplyCriticalStats(C,*E,*Item);
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor*=(1+Craft(TEXT("magicDamagePercent"))+Craft(TEXT("iceDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent")));
            ColdSteelSpellCrafting::ApplyChainAndCastHaste(C,*E,*Item);
            C.PendantChillSlow=Craft(TEXT("iceChillSlowPercent"))>0?CombatChill::SlowPerStack:0.f;
            C.PendantChillSeconds=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
        }
    C.Damage=FMath::FloorToFloat(C.Damage*DamageFactor);
    C.ShatterDamage=FMath::FloorToFloat(C.ShatterDamage*DamageFactor);
    C.WallShardDamage=FMath::FloorToFloat(C.WallShardDamage*DamageFactor);
    C.ManaCost=SpellManaCost(TEXT("absoluteZero"),L);
    C.Cooldown=FMath::Clamp(C.Cooldown*float(FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown")))))*float(Rune.SkillCooldown*Rune.MagicCooldown),0.f,300.f);
    ApplySpellCastSpeed(C.CastSpeed);
    if(const auto* Pawn=RuntimePawn())
        if(const auto* Armor=Pawn->FindComponentByClass<UFPSIceArmorComponent>();Armor&&Armor->Remaining()>0.f)
            C.bIceArmorSynergy=true;
    return C;
}

bool UColdSteelStatusModel::BeginAbsoluteZeroCast(const FAbsoluteZeroCast& Spell)
{
    if(Current.bAbsoluteZeroReserved||AbsoluteZeroCooldown()>0||!CanSpendMana(Spell.ManaCost)||(Spell.bRequiresStaff&&!HasEquippedStaff()))return false;
    SyncRuntime();auto P=Snapshot();const float Before=P.Mana;
    if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    P.bAbsoluteZeroReserved=true;P.AbsoluteZeroReservedMana=Before-P.Mana;
    P.AbsoluteZeroCooldown=P.AbsoluteZeroCooldownDuration=HasNoAbilityCooldown()?0.f:Spell.Cooldown;
    return CommitState(MoveTemp(P));
}

bool UColdSteelStatusModel::CommitAbsoluteZeroRelease()
{
    if(!Current.bAbsoluteZeroReserved)return false;
    SyncRuntime();auto P=Snapshot();P.bAbsoluteZeroReserved=false;P.AbsoluteZeroReservedMana=0.f;
    const bool Released=CommitState(MoveTemp(P));
    if(Released)NotifyMagicReleased();
    return Released;
}

bool UColdSteelStatusModel::ApplyAbsoluteZeroNovaHit(APawn* Shooter,AActor* Target,const FAbsoluteZeroCast& Spell,float Distance,FAbsoluteZeroRewards& Batch)
{
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))return false;
    auto* Status=UCombatStatusFormula::GetOrAdd(Target);
    const bool bWasFrozen=Status&&Status->IsFrozen();
    const int32 PriorChill=Status?Status->ChillCount():0;
    const float ChillMul=1.f+FMath::Min(Spell.ChillBonusCap,PriorChill*Spell.ChillBonusPerStack);
    const float PrimaryRaw=FMath::FloorToFloat(Spell.Damage*ChillMul);

    TGuardValue<FTrainingHit*> TrainingScope(ActiveTrainingHit,nullptr);
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,nullptr);
    bool Critical=false;
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,false};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);

    const float Applied=Combat->ApplyHitWithToughnessScale(1.f,[&]()
    {
        return UGameplayStatics::ApplyDamage(Target,PrimaryRaw,Shooter->GetController(),Shooter,UAbsoluteZeroDamage::StaticClass());
    },Spell.ToughnessDamage);
    if(Applied<=0.f)return false;

    ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,Critical);
    const bool bTraining=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    bool bCountedKill=Combat->IsDead();
    if(bTraining)ColdSteelSpellRewards::RecordTrainingHit(Batch,*Combat,Critical);

    if(!Combat->IsDead())
    {
        if(!bWasFrozen)
        {
            const float Alpha=FMath::Clamp(Distance/FMath::Max(1.f,Spell.Radius),0.f,1.f);
            const float Push=FMath::Lerp(Spell.KnockbackMax,Spell.KnockbackBase,Alpha);
            if(Push>1.f)Combat->ReceiveMeleeKnockback(Shooter,Push);
        }
        const bool bTriggerShatter=bWasFrozen||PriorChill>=Spell.ShatterChillThreshold;
        if(bTriggerShatter&&Spell.ShatterDamage>0.f)
        {
            // Physical shatter damage consumes the existing Frozen x1.5 multiplier before thawing.
            TGuardValue<const CombatFormulaRuntime::MagicHit*> ClearMagic(CombatFormulaRuntime::ActiveMagicHit,nullptr);
            const float ShatterApplied=UGameplayStatics::ApplyDamage(Target,Spell.ShatterDamage,Shooter->GetController(),Shooter,UAbsoluteZeroShatterDamage::StaticClass());
            if(ShatterApplied>0.f)
            {
                ColdSteelSpellFeedback::NotifyHit(Shooter,Target,ShatterApplied,*Combat,false,false);
                if(bTraining&&!bCountedKill&&Combat->IsDead()){++Batch.Kills;bCountedKill=true;}
            }
            if(!Combat->IsDead()&&Status)Status->ConsumeFrostForShatter(Spell.ShatterChillThreshold);
        }
        else if(Status)
        {
            const int32 AddStacks=Distance<=Spell.InnerRadius?Spell.InnerChillStacks:Spell.OuterChillStacks;
            Status->AddChill(AddStacks,Spell.ChillSeconds,true);
            if(Spell.PendantChillSlow>0.f)Status->AddChill(1,Spell.PendantChillSeconds,true);
        }
    }
    return true;
}

bool UColdSteelStatusModel::ApplyAbsoluteZeroWallShardHit(APawn* Shooter,AActor* Target,const FAbsoluteZeroCast& Spell,float HealthRatio,int32 TargetShardIndex,FAbsoluteZeroRewards& Batch)
{
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))return false;
    const float Scale=TargetShardIndex<Spell.MaxFullShardsPerTarget?1.f:Spell.OverflowShardScale;
    const float DurabilityFactor=.65f+.35f*FMath::Clamp(HealthRatio,0.f,1.f);
    const float Raw=FMath::FloorToFloat(Spell.WallShardDamage*DurabilityFactor*Scale);
    if(Raw<=0.f)return false;

    TGuardValue<FTrainingHit*> TrainingScope(ActiveTrainingHit,nullptr);
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,nullptr);
    const float Applied=UGameplayStatics::ApplyDamage(Target,Raw,Shooter->GetController(),Shooter,UAbsoluteZeroShatterDamage::StaticClass());
    if(Applied<=0.f)return false;
    ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,false,false);
    if(!Combat->IsDead())
        if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))Status->AddChill(1,Spell.ChillSeconds,true);
    const bool bTraining=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
    if(bTraining)
    {
        ++Batch.WallComboHits;
        ColdSteelSpellRewards::RecordTrainingHit(Batch,*Combat,false);
    }
    return true;
}

void UColdSteelStatusModel::FinishAbsoluteZeroCast(const FAbsoluteZeroRewards& Batch)
{
    if(Batch.Hits<=0&&Batch.WallComboHits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& T=AbsoluteZeroSkill.AbsoluteZero;
    ColdSteelSpellRewards::AccumulateHitKillTraining(P,AbsoluteZeroSkill,T,Batch.Hits,Batch.Kills,Batch.bMultiHit);
    if(Batch.WallComboHits>0&&T.WallComboExperience>0)ColdSteelSkills::AddExperience(P,AbsoluteZeroSkill,T.WallComboExperience);
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,Batch.CriticalHits,Batch.CriticalKills);
    StageTraining(MoveTemp(P));
}
