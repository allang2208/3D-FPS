#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "BlizzardDamage.h"
#include "HolyLightTargets.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::BlizzardProgress() const
{const auto* P=Current.Skills.Find(TEXT("blizzard"));return P?*P:FColdSteelSkillProgress();}
float UColdSteelStatusModel::BlizzardCooldown() const{return HasNoAbilityCooldown()?0.f:Current.BlizzardCooldown;}
float UColdSteelStatusModel::BlizzardCooldownDuration() const{return Current.BlizzardCooldownDuration;}
FBlizzardCast UColdSteelStatusModel::BlizzardStats(int32 AtLevel) const
{
    const auto& D=BlizzardSkill;const auto& T=D.Blizzard;
    const int32 L=FMath::Clamp(AtLevel<0?BlizzardProgress().Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    FBlizzardCast C;
    C.Damage=FMath::FloorToFloat(T.DamageBase+L*T.DamagePerLevel+Derived(TEXT("matk"))*(T.MagicBase+L*T.MagicPerLevel)+Attribute(TEXT("int"))*(T.IntelligenceBase+L*T.IntelligencePerLevel));
    C.RadiusX=(T.RadiusXBase+L*T.RadiusXPerLevel)*T.UnitsToCM;
    C.RadiusY=(T.RadiusYBase+L*T.RadiusYPerLevel)*T.UnitsToCM;
    C.Range=T.Range*T.UnitsToCM;C.ManaCost=T.ManaCost;
    C.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    C.Duration=T.Duration+FMath::FloorToFloat(Growth*T.DurationGrowth);
    C.TickSeconds=T.TickSeconds;C.ChillSeconds=T.ChillSeconds;C.ChillSlow=T.ChillSlow;C.ChillStacks=T.ChillStacks;C.bRequiresStaff=T.bRequiresStaff;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    const auto* Player=RuntimePawn();
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    float DamageFactor=MagicImplementMultiplier(),CostFactor=1,CooldownReduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+Craft(TEXT("critChancePercent"))+Craft(TEXT("magicCritPercent")));
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+Craft(TEXT("magicPenetrationPercent"));
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor*=(1+Craft(TEXT("magicDamagePercent"))+Craft(TEXT("iceDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent")));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
            C.PendantChillSlow=Craft(TEXT("iceChillSlowPercent"));
            C.PendantChillSeconds=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
        }
    C.Damage=FMath::FloorToFloat(C.Damage*DamageFactor);
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor)*float(Rune.MagicCost));
    C.Cooldown=FMath::Clamp(C.Cooldown*float(FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown")))))*float(Rune.MagicCooldown),0.f,300.f);
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
    return CommitState(MoveTemp(P));
}
bool UColdSteelStatusModel::ApplyBlizzardHit(APawn* Shooter,AActor* Target,const FBlizzardCast& Spell,FBlizzardRewards& Batch)
{
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
        Status->AddChill(Spell.ChillStacks,Spell.ChillSeconds,Spell.ChillSlow);
        if(Spell.PendantChillSlow>0)Status->AddChill(1,Spell.PendantChillSeconds,Spell.PendantChillSlow);
    }
    if(auto* Player=Cast<AFPSGAMECharacter>(Shooter))Player->NotifyConfirmedWeaponHit(Target,Applied);
    if(!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {
        ++Batch.Hits;if(Combat->IsDead())++Batch.Kills;
        if(Critical){++Batch.CriticalHits;if(Combat->IsDead())++Batch.CriticalKills;}
    }
    return true;
}
void UColdSteelStatusModel::FinishBlizzardCast(const FBlizzardRewards& Batch)
{
    if(Batch.Hits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& T=BlizzardSkill.Blizzard;
    ColdSteelSkills::AddExperience(P,BlizzardSkill,Batch.Hits*T.HitExperience+Batch.Kills*T.KillExperience+(Batch.bMultiHit?T.MultiHitExperience:0)+(Batch.Kills>=2?T.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,Batch.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+Batch.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    StageTraining(MoveTemp(P));
}
