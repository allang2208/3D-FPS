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
#include "BlizzardDamage.h"
#include "HolyLightTargets.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::BlizzardProgress() const
{return Current.Skills.FindRef(TEXT("blizzard"));}
float UColdSteelStatusModel::BlizzardCooldown() const{return HasNoAbilityCooldown()?0.f:Current.BlizzardCooldown;}
float UColdSteelStatusModel::BlizzardCooldownDuration() const{return Current.BlizzardCooldownDuration;}
FBlizzardCast UColdSteelStatusModel::BlizzardStats(int32 AtLevel) const
{
    const auto& D=BlizzardSkill;const auto& T=D.Blizzard;
    const int32 L=FMath::Clamp(AtLevel<0?BlizzardProgress().Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    const int32 DamageLevel=L-1;
    FBlizzardCast C;
    C.Damage=FMath::FloorToFloat(T.DamageBase+DamageLevel*T.DamagePerLevel+Derived(TEXT("matk"))*(T.MagicBase+DamageLevel*T.MagicPerLevel)+Attribute(TEXT("int"))*(T.IntelligenceBase+DamageLevel*T.IntelligencePerLevel));
    C.RadiusX=(T.RadiusXBase+L*T.RadiusXPerLevel)*T.UnitsToCM;
    C.RadiusY=(T.RadiusYBase+L*T.RadiusYPerLevel)*T.UnitsToCM;
    C.Range=T.Range*T.UnitsToCM;
    C.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    C.Duration=T.Duration+FMath::FloorToFloat(Growth*T.DurationGrowth);
    C.TickSeconds=T.TickSeconds;C.ChillSeconds=T.ChillSeconds;C.ChillSlow=T.ChillSlow;C.ChillStacks=T.ChillStacks;C.bRequiresStaff=T.bRequiresStaff;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    float DamageFactor=MagicImplementMultiplier(),CooldownReduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            ColdSteelSpellCrafting::ApplyCriticalStats(C,*E,*Item);
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor*=(1+Craft(TEXT("magicDamagePercent"))+Craft(TEXT("iceDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent")));
            ColdSteelSpellCrafting::ApplyChainAndCastHaste(C,*E,*Item);
            C.PendantChillSlow=Craft(TEXT("iceChillSlowPercent"))>0?CombatChill::SlowPerStack:0.f;
            C.PendantChillSeconds=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
        }
    C.Range*=float(MagicRangeMultiplier());
    C.Damage=FMath::FloorToFloat(C.Damage*DamageFactor);
    C.ManaCost=SpellManaCost(TEXT("blizzard"),L);
    C.Cooldown=FMath::Clamp(C.Cooldown*float(FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown")))))*float(Rune.SkillCooldown*Rune.MagicCooldown),0.f,300.f);
    ApplySpellCastSpeed(C.CastSpeed);
    return C;
}
bool UColdSteelStatusModel::BeginBlizzardCast(const FBlizzardCast& Spell)
{
    if(Current.bBlizzardReserved||BlizzardCooldown()>0||!CanSpendMana(Spell.ManaCost)||(Spell.bRequiresStaff&&!HasEquippedStaff()))return false;
    SyncRuntime();auto P=Snapshot();const float Before=P.Mana;
    if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    P.bBlizzardReserved=true;P.BlizzardReservedMana=Before-P.Mana;
    P.BlizzardCooldown=P.BlizzardCooldownDuration=HasNoAbilityCooldown()?0.f:Spell.Cooldown;
    return CommitState(MoveTemp(P));
}
bool UColdSteelStatusModel::CommitBlizzardRelease()
{
    if(!Current.bBlizzardReserved)return false;
    SyncRuntime();auto P=Snapshot();P.bBlizzardReserved=false;P.BlizzardReservedMana=0;
    const bool Released=CommitState(MoveTemp(P));
    if(Released)NotifyMagicReleased();return Released;
}
bool UColdSteelStatusModel::ApplyBlizzardHit(APawn* Shooter,AActor* Target,const FBlizzardCast& Spell,FBlizzardRewards& Batch)
{
    if(UnknownSpell::IsCaster(Shooter))
    {
        const bool Applied=UnknownSpell::Hit(Shooter,Target,Spell.Damage,Spell.CriticalChance,Spell.CriticalDamageBonus,
            Spell.MagicDamageBonus,Spell.MagicPenetration,UBlizzardDamage::StaticClass());
        if(Applied)UCombatStatusFormula::GetOrAdd(Target)->AddChill(Spell.ChillStacks,Spell.ChillSeconds);
        if(Applied)++Batch.Hits;
        return Applied;
    }
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))return false;
    TGuardValue<FTrainingHit*> TrainingScope(ActiveTrainingHit,nullptr);
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,nullptr);
    bool Critical=false;
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,false};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const float Applied=UGameplayStatics::ApplyDamage(Target,Spell.Damage,Shooter->GetController(),Shooter,UBlizzardDamage::StaticClass());
    if(Applied<=0)return false;
    if(!Combat->IsDead())if(auto* Status=UCombatStatusFormula::GetOrAdd(Target))
    {
        Status->AddChill(Spell.ChillStacks,Spell.ChillSeconds);
        if(Spell.PendantChillSlow>0)Status->AddChill(1,Spell.PendantChillSeconds);
    }
    ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,Critical);
    if(!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {
        ColdSteelSpellRewards::RecordTrainingHit(Batch,*Combat,Critical);
    }
    return true;
}
void UColdSteelStatusModel::FinishBlizzardCast(const FBlizzardRewards& Batch)
{
    if(Batch.Hits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& T=BlizzardSkill.Blizzard;
    ColdSteelSpellRewards::AccumulateHitKillTraining(P,BlizzardSkill,T,Batch.Hits,Batch.Kills,Batch.bMultiHit);
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,Batch.CriticalHits,Batch.CriticalKills);
    StageTraining(MoveTemp(P));
}
