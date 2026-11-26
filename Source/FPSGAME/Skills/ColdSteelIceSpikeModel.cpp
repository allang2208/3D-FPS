#include "ColdSteelSpellRewards.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "ColdSteelSpellCrafting.h"
#include "ColdSteelSpellFeedback.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../Combat/RangedAttackQuery.h"
#include "FPSIceWall.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "IceSpikeDamage.h"
#include "FPSMagicPreview.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::IceSpikeProgress() const
{return Current.Skills.FindRef(IceSpikeSkill.Id);}

FIceSpikeCast UColdSteelStatusModel::IceSpikeStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?IceSpikeProgress().Level:AtLevel,1,IceSpikeSkill.MaxLevel);
    const auto& T=IceSpikeSkill.IceSpike;FIceSpikeCast C;
    C.DamageBase=T.DamageBase+L*T.DamagePerLevel;
    C.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;
    C.MagicContribution=Derived(TEXT("matk"))*C.MagicMultiplier;
    C.Count=T.CountBase+(L-1)/T.CountLevelStep;
    // The base cooldown shortens with level on the fireball's curve.
    const float Growth=float(L-1)/FMath::Max(1,IceSpikeSkill.MaxLevel-1);
    C.Cooldown=FMath::Max(T.MinimumCooldown,FMath::Lerp(T.Cooldown,T.MinimumCooldown,Growth));
    C.HoverDuration=T.HoverDuration;
    C.Speed=T.Speed*T.UnitsToCM;C.Range=T.Range*T.UnitsToCM;
    C.Gravity=T.Gravity*FPSMagicPreview::GravityScale();
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    double DamageFactor=1,CooldownReduction=0;
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    // Only the active staff contributes spell crafting. The immutable cast survives weapon swaps.
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.Count+=int32(Craft(TEXT("iceSpikeCountDelta")));
            ColdSteelSpellCrafting::ApplyCriticalStats(C,*E,*Item);
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));
            C.Range*=1+Craft(TEXT("magicRangePercent"));C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            ColdSteelSpellCrafting::ApplyChainAndCastHaste(C,*E,*Item);
            C.ChillSlow=Craft(TEXT("iceChillSlowPercent"))>0?CombatChill::SlowPerStack:0.f;C.ChillDuration=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
            if(ColdSteelSpellCrafting::HasStaffSpecialty(*Item,TEXT("ice")))
                DamageFactor+=Craft(TEXT("iceDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    C.Range*=float(MagicRangeMultiplier());
    C.Count=FMath::Max(1,C.Count);
    // The wand hook multiplies every magic spell, so the two spells stay on one damage factor.
    C.Damage=FMath::FloorToFloat(FMath::FloorToDouble(C.DamageBase+C.MagicContribution)*DamageFactor*MagicImplementMultiplier());
    C.ManaCost=SpellManaCost(TEXT("iceSpike"),L);
    ColdSteelSpellCrafting::ApplyCooldownMultipliers(C.Cooldown,CooldownReduction,SetEffect(TEXT("cooldown")),
        Rune.SkillCooldown*Rune.MagicCooldown);
    ApplySpellCastSpeed(C.CastSpeed);
    return C;
}

bool UColdSteelStatusModel::BeginIceSpikeCast(const FIceSpikeCast& Cast)
{
    if(Current.bIceSpikeReserved||IceSpikeCooldown()>0){Message=TEXT("冰锥尚未就绪");return false;}
    if(!CanSpendMana(Cast.ManaCost)){Message=TEXT("魔法不足");return false;}
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Cast.ManaCost;
    P.bIceSpikeReserved=true;P.IceSpikeCooldown=HasNoAbilityCooldown()?0.f:Cast.Cooldown;
    P.IceSpikeCooldownDuration=P.IceSpikeCooldown;return CommitState(P);
}

void UColdSteelStatusModel::ApplyIceSpikeHit(APawn* Shooter,const FHitResult& Hit,const FIceSpikeCast& Cast,FIceSpikeRewards& Batch,FEclipseBowShot* EclipseShot)
{
    if(UnknownSpell::IsCaster(Shooter))
    {
        const bool Applied=UnknownSpell::Hit(Shooter,Hit.GetActor(),Cast.Damage,Cast.CriticalChance,Cast.CriticalDamageBonus,
            Cast.MagicDamageBonus,Cast.MagicPenetration,UIceSpikeDamage::StaticClass(),ColdSteelSkills::IsCriticalHit(Hit));
        if(Applied&&Cast.ChillSlow>0)UCombatStatusFormula::GetOrAdd(Hit.GetActor())->AddChill(1,Cast.ChillDuration,Cast.bRefreshChillDuration);
        if(Applied)++Batch.Hits;
        return;
    }
    AActor* Target=Hit.GetActor();
    if(auto* Wall=::Cast<AFPSIceWall>(Target);Wall&&Shooter&&Shooter->IsPlayerControlled()&&Shooter->HasAuthority())
    {
        UGameplayStatics::ApplyPointDamage(Wall,Cast.Damage,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,UIceSpikeDamage::StaticClass());
        return;
    }
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Shooter,Target))return;
    FFireballRewards Rewards;Rewards.Victim=Target;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    bool Critical=false;
    const CombatFormulaRuntime::MagicHit Context{Cast.CriticalChance,Cast.CriticalDamageBonus,Cast.MagicPenetration,Cast.MagicDamageBonus,&Critical,ColdSteelSkills::IsCriticalHit(Hit)};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    StarMarrow::FHitRecovery CrystalRecovery(Shooter,Target,Cast.StarMarrow);
    FEclipseBowImpact EclipseImpact(EclipseShot, Target);
    const float Applied=UGameplayStatics::ApplyPointDamage(Target,Cast.Damage,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,UIceSpikeDamage::StaticClass());
    EclipseImpact.Confirm(Applied);
    CrystalRecovery.Finish(Applied);
    Batch.KillRewards.Append(Rewards.Kills);
    if(Applied<=0)return;
    if(Cast.ChillSlow>0&&!Combat->IsDead())UCombatStatusFormula::GetOrAdd(Target)->AddChill(1,Cast.ChillDuration,Cast.bRefreshChillDuration);
    ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,Critical);
    if(Target->ActorHasTag(TEXT("Summoned"))||Target->ActorHasTag(TEXT("NoSkillTraining")))return;
    ColdSteelSpellRewards::RecordTrainingHit(Batch,*Combat,Critical);
}

void UColdSteelStatusModel::FinishIceSpikeCast(const FIceSpikeRewards& Batch,bool bElementalArrow)
{
    if(!bElementalArrow&&!Current.bIceSpikeReserved)return;
    SyncRuntime();auto P=Snapshot();if(!bElementalArrow)P.bIceSpikeReserved=false;
    if(bElementalArrow)StageElementalArrowTraining(P,Batch.Hits,Batch.Kills);
    const auto& T=IceSpikeSkill.IceSpike;
    ColdSteelSpellRewards::AccumulateHitKillTraining(P,IceSpikeSkill,T,Batch.Hits,Batch.Kills,Batch.Hits>=2);
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,Batch.CriticalHits,Batch.CriticalKills);
    ColdSteelSpellRewards::AccumulateKillExperience(P,Batch.KillRewards,*this);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Batch.KillRewards)RewardedVictims.Add(K.Key);
}
