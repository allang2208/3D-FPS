#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatItemFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "HolyLightDamage.h"
#include "HolyLightTargets.h"
#include "FPSHolyRenewalComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"

FColdSteelSkillProgress UColdSteelStatusModel::HolyLightProgress() const
{const auto* P=Current.Skills.Find(HolyLightSkill.Id);return P?*P:FColdSteelSkillProgress();}

FHolyLightCast UColdSteelStatusModel::HolyLightStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?HolyLightProgress().Level:AtLevel,1,HolyLightSkill.MaxLevel);
    const auto& T=HolyLightSkill.HolyLight;FHolyLightCast C;
    C.AmountBase=T.AmountBase+L*T.AmountPerLevel;
    C.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;
    C.IntelligenceMultiplier=T.IntelligenceBase+L*T.IntelligencePerLevel;
    C.WisdomMultiplier=T.WisdomBase+L*T.WisdomPerLevel;
    const double Base=FMath::FloorToDouble(C.AmountBase+Derived(TEXT("matk"))*C.MagicMultiplier+Attribute(TEXT("int"))*C.IntelligenceMultiplier+Attribute(TEXT("wis"))*C.WisdomMultiplier);
    C.ManaCost=T.ManaCost;C.Cooldown=T.Cooldown-(L-1)/T.CooldownLevelStep*T.CooldownStepReduction;
    C.Range=T.Range*T.UnitsToCM;C.AimRadius=T.AimRadius*T.UnitsToCM;
    C.ZombieMultiplier=T.ZombieMultiplier;C.Duration=T.Duration;C.Fade=T.Fade;
    C.TopWidth=T.TopWidth*T.UnitsToCM;C.BottomWidth=T.BottomWidth*T.UnitsToCM;C.Height=T.Height*T.UnitsToCM;C.DissolveRatio=T.DissolveRatio;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    double DamageFactor=1,HealFactor=1,CostFactor=1,CooldownReduction=0;
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+Craft(TEXT("critChancePercent"))+Craft(TEXT("magicCritPercent")));
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+Craft(TEXT("magicPenetrationPercent"));
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));C.AimRadius*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor=(1+Craft(TEXT("magicDamagePercent")))*(1+Chain*Craft(TEXT("chainSpellDamagePercent")));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
            C.RenewalStacks=Craft(TEXT("holyLightHoTStacks"));C.RenewalSeconds=E->CraftEffect(*Item,TEXT("holyLightHoTSeconds"),3);
            C.HealHasteStacks=Craft(TEXT("lightHasteStacks"));C.HealHasteSeconds=E->CraftEffect(*Item,TEXT("lightHasteDuration"),5000)/1000;
            const auto Data=CombatItemFormula::Read(*Item);const TSharedPtr<FJsonObject>* Effects=nullptr;FString Specialty;
            if(Data&&Data->TryGetObjectField(TEXT("_craftEffects"),Effects)&&(*Effects)->TryGetStringField(TEXT("staffSpecialty"),Specialty)&&Specialty==TEXT("light"))
                HealFactor+=Craft(TEXT("lightHealPercent"));
        }
    // Light healing never inherits damage-only, chain damage or critical modifiers.
    C.Healing=FMath::FloorToFloat(Base*HealFactor);
    C.Damage=FMath::FloorToFloat(Base*DamageFactor*MagicImplementMultiplier());
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor)*float(Rune.MagicCost));
    C.Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown"))));C.Cooldown*=Rune.MagicCooldown;
    return C;
}

bool UColdSteelStatusModel::BeginHolyLightCast(const FHolyLightCast& Spell)
{
    if(HolyLightCooldown()>0){Message=TEXT("圣光尚未就绪");return false;}
    if(!CanSpendMana(Spell.ManaCost)){Message=TEXT("魔法不足");return false;}
    SyncRuntime();auto P=Snapshot();if(!HasInfiniteMana())P.Mana-=Spell.ManaCost;
    P.HolyLightCooldown=HasNoAbilityCooldown()?0.f:Spell.Cooldown;P.HolyLightCooldownDuration=P.HolyLightCooldown;
    return CommitState(P);
}

bool UColdSteelStatusModel::ApplyHolyLightHit(APawn* Shooter,AActor* Target,const FVector& Origin,const FHolyLightCast& Spell,float Damage,FHolyLightRewards& Batch,bool bTrain)
{
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||HolyLightTargets::IsFriendly(Target))return false;
    FFireballRewards Rewards;Rewards.Victim=Target;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    bool Critical=false;
    // A locked spell has no aimed bone contact; it can randomly crit but cannot invent a headshot.
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,false};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const FVector End=Target->GetActorLocation();
    FHitResult Hit(Target,Cast<UPrimitiveComponent>(Target->GetRootComponent()),End,(Origin-End).GetSafeNormal());
    Hit.TraceStart=Origin;Hit.TraceEnd=End;
    const float Applied=UGameplayStatics::ApplyPointDamage(Target,FMath::FloorToFloat(Damage*(HolyLightTargets::IsZombie(Target)?Spell.ZombieMultiplier:1.f)),(End-Origin).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,UHolyLightDamage::StaticClass());
    for(const auto& K:Rewards.Kills)Batch.KillRewards.FindOrAdd(K.Key)=K.Value;
    if(Applied<=0)return false;
    if(auto* Player=Cast<AFPSGAMECharacter>(Shooter))Player->NotifyConfirmedWeaponHit(Target,Applied);
    if(bTrain&&!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining")))
    {
        ++Batch.Hits;if(Combat->IsDead())++Batch.Kills;
        if(Critical){++Batch.CriticalHits;if(Combat->IsDead())++Batch.CriticalKills;}
    }
    return true;
}

void UColdSteelStatusModel::FinishHolyLightCast(const FHolyLightRewards& Batch)
{
    SyncRuntime();auto P=Snapshot();const auto& T=HolyLightSkill.HolyLight;
    ColdSteelSkills::AddExperience(P,HolyLightSkill,Batch.Hits*T.HitExperience+Batch.Kills*T.KillExperience);
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,Batch.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+Batch.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    for(const auto& K:Batch.KillRewards){P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Batch.KillRewards)RewardedVictims.Add(K.Key);
}

bool UColdSteelStatusModel::ApplyHolyLightHealing(AActor* Target,const FHolyLightCast& Spell,FHolyLightRewards& Batch)
{
    if(!HolyLightTargets::IsFriendly(Target)||!HolyLightTargets::IsAlive(Target))return false;
    HolyLightTargets::Heal(Target,Spell.Healing);
    if(Spell.RenewalStacks>0)UFPSHolyRenewalComponent::Apply(Target,Spell.RenewalStacks,Spell.RenewalSeconds);
    if(Spell.HealHasteStacks>0)UCombatStatusFormula::GetOrAdd(Target)->AddHaste(Spell.HealHasteStacks,Spell.HealHasteSeconds);
    // A valid friendly target trains once, including a full-health self cast, as in the source.
    if(!Target->ActorHasTag(TEXT("NoSkillTraining")))++Batch.Hits;
    return true;
}
