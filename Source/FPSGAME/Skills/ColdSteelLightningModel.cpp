#include "ColdSteelSpellRewards.h"
#include "../Weapons/Bow/EclipseBowMark.h"
#include "ColdSteelSpellCrafting.h"
#include "ColdSteelSpellFeedback.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../Combat/RangedAttackQuery.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "LightningDamage.h"
#include "../Production/ThunderHammerRunes.h"
#include "../Production/ThunderHammerPommel.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::LightningProgress() const
{return Current.Skills.FindRef(LightningSkill.Id);}

FLightningCast UColdSteelStatusModel::LightningStats(int32 AtLevel,bool bApplyFocus) const
{
    const int32 L=FMath::Clamp(AtLevel<0?LightningProgress().Level:AtLevel,1,LightningSkill.MaxLevel);
    const auto& T=LightningSkill.Lightning;FLightningCast C;
    C.DamageBase=T.DamageBase+L*T.DamagePerLevel;
    C.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;C.IntelligenceMultiplier=T.IntelligenceBase+L*T.IntelligencePerLevel;
    const double Matk=Derived(TEXT("matk")),Intelligence=Attribute(TEXT("int"));
    C.Count=T.CountBase+(L-1)/T.CountLevelStep;C.Cooldown=T.Cooldown;
    C.Range=T.Range*T.UnitsToCM;C.AimRadius=T.AimRadius*T.UnitsToCM;C.ChainRange=T.ChainRange*T.UnitsToCM;
    C.StunSeconds=T.StunBase+L*T.StunPerLevel;C.ChainDecay=T.ChainDecay;
    C.Duration=T.Duration;C.Fade=T.Fade;C.Segments=T.Segments;C.Jitter=T.Jitter;
    C.ElectrifyStacks=T.ElectrifyStacks;C.ElectrifyDuration=T.ElectrifyDuration;C.ElectricBonusPerStack=T.ElectricBonusPerStack;
    C.OverloadStacks=T.OverloadStacks;C.OverloadStun=T.OverloadStun;C.OverloadRange=T.OverloadRange*T.UnitsToCM;
    ThunderHammerRunes::Configure(C,ActiveProductionTool()?ActiveProductionTool():Equipped());
    C.OverloadDamage=FMath::FloorToFloat(T.OverloadBase+Matk*T.OverloadMagic+Intelligence*T.OverloadIntelligence);
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    double DamageFactor=1,CooldownReduction=0;
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.Count+=int32(Craft(TEXT("lightningChainTargetsDelta")));
            ColdSteelSpellCrafting::ApplyCriticalStats(C,*E,*Item);
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            const double Area=1+Craft(TEXT("magicRangePercent"));C.AimRadius*=Area;C.ChainRange*=Area;
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            C.StunExtensionSeconds=Craft(TEXT("electricStunExtendMs"))/1000;
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            ColdSteelSpellCrafting::ApplyChainAndCastHaste(C,*E,*Item);
            if(ColdSteelSpellCrafting::HasStaffSpecialty(*Item,TEXT("electric")))
                DamageFactor+=Craft(TEXT("electricDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    C.Range*=float(MagicRangeMultiplier());
    C.Count=FMath::Max(1,C.Count);
    C.Damage=FMath::FloorToFloat(FMath::FloorToDouble(C.DamageBase+Matk*C.MagicMultiplier+Intelligence*C.IntelligenceMultiplier)*DamageFactor*MagicImplementMultiplier());
    C.ManaCost=SpellManaCost(TEXT("lightningStrike"),L,bApplyFocus);
    ColdSteelSpellCrafting::ApplyCooldownMultipliers(C.Cooldown,CooldownReduction,SetEffect(TEXT("cooldown")),
        Rune.SkillCooldown*Rune.MagicCooldown);
    if(bApplyFocus)ApplySpellCastSpeed(C.CastSpeed);
    return C;
}

bool UColdSteelStatusModel::BeginLightningCast(const FLightningCast& Spell)
{
    if(LightningCooldown()>0){Message=TEXT("闪电尚未就绪");return false;}
    if(!CanSpendMana(Spell.ManaCost)){Message=TEXT("魔法不足");return false;}
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    P.LightningCooldown=HasNoAbilityCooldown()?0.f:Spell.Cooldown;P.LightningCooldownDuration=P.LightningCooldown;
    return CommitState(P);
}

bool UColdSteelStatusModel::ApplyLightningHit(APawn* Shooter,AActor* Target,const FVector& Origin,const FLightningCast& Spell,float Damage,FLightningRewards& Batch,bool bTrain,const FHitResult* DirectHit,FEclipseBowShot* EclipseShot)
{
    if(UnknownSpell::IsCaster(Shooter))
    {
        const bool Applied=UnknownSpell::Hit(Shooter,Target,Damage,Spell.CriticalChance,Spell.CriticalDamageBonus,
            Spell.MagicDamageBonus,Spell.MagicPenetration,ULightningDamage::StaticClass(),DirectHit&&ColdSteelSkills::IsCriticalHit(*DirectHit));
        if(Applied)UCombatStatusFormula::GetOrAdd(Target)->AddStunWithExtension(bTrain?Spell.StunSeconds:0.f,Spell.StunExtensionSeconds);
        if(Applied)++Batch.Hits;
        return Applied;
    }
    if(Shooter && Shooter->HasAuthority() && Damage>0)
        if(auto* Pane=UWardBreakableGlass::IntactPane(Target))
        {Pane->BreakAt(Pane->GetComponentLocation(),Pane->GetComponentLocation()-Origin);return false;}
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||RangedAttackQuery::IsFriendlyUnit(Shooter,Target))return false;
    FFireballRewards Rewards;Rewards.Victim=Target;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    bool Critical=false;
    // Only a real beam trace against this target can grant a guaranteed weakpoint critical.
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,DirectHit&&DirectHit->GetActor()==Target&&ColdSteelSkills::IsCriticalHit(*DirectHit)};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const FVector End=Target->GetActorLocation();
    FHitResult Hit(Target,Cast<UPrimitiveComponent>(Target->GetRootComponent()),End,(Origin-End).GetSafeNormal());
    if(DirectHit&&DirectHit->GetActor()==Target)Hit=*DirectHit;
    Hit.TraceStart=Origin;Hit.TraceEnd=End;
    StarMarrow::FHitRecovery CrystalRecovery(Shooter,Target,Spell.StarMarrow);
    FEclipseBowImpact EclipseImpact(EclipseShot, Target);
    const float Applied=UGameplayStatics::ApplyPointDamage(Target,Damage,(End-Origin).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,ULightningDamage::StaticClass());
    EclipseImpact.Confirm(Applied);
    CrystalRecovery.Finish(Applied);
    Batch.KillRewards.Append(Rewards.Kills);
    if(Applied<=0)return false;
    ThunderHammerPommel::ConfirmElectricDamage(Shooter,Spell,Applied);
    // The bell extends an existing stun; overload splash receives only the bell,
    // not the direct lightning strike's native stun.
    if(!Combat->IsDead()&&(bTrain||Spell.StunExtensionSeconds>0))
        UCombatStatusFormula::GetOrAdd(Target)->AddStunWithExtension(bTrain?Spell.StunSeconds:0.f,Spell.StunExtensionSeconds);
    ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,Critical);
    if(bTrain&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {
        ColdSteelSpellRewards::RecordTrainingHit(Batch,*Combat,Critical);
    }
    return true;
}

void UColdSteelStatusModel::FinishLightningCast(const FLightningRewards& Batch,bool bElementalArrow)
{
    SyncRuntime();auto P=Snapshot();const auto& T=LightningSkill.Lightning;
    if(bElementalArrow)StageElementalArrowTraining(P,Batch.Hits,Batch.Kills);
    ColdSteelSpellRewards::AccumulateHitKillTraining(P,LightningSkill,T,Batch.Hits,Batch.Kills,Batch.Hits>=2);
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,Batch.CriticalHits,Batch.CriticalKills);
    ColdSteelSpellRewards::AccumulateKillExperience(P,Batch.KillRewards,*this);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Batch.KillRewards)RewardedVictims.Add(K.Key);
}
