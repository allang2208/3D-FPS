#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatItemFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "LightningDamage.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"

FColdSteelSkillProgress UColdSteelStatusModel::LightningProgress() const
{const auto* P=Current.Skills.Find(LightningSkill.Id);return P?*P:FColdSteelSkillProgress();}

FLightningCast UColdSteelStatusModel::LightningStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?LightningProgress().Level:AtLevel,1,LightningSkill.MaxLevel);
    const auto& T=LightningSkill.Lightning;FLightningCast C;
    C.DamageBase=T.DamageBase+L*T.DamagePerLevel;
    C.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;C.IntelligenceMultiplier=T.IntelligenceBase+L*T.IntelligencePerLevel;
    const double Matk=Derived(TEXT("matk")),Intelligence=Attribute(TEXT("int"));
    C.Count=T.CountBase+(L-1)/T.CountLevelStep;C.ManaCost=T.ManaCost;C.Cooldown=T.Cooldown;
    C.Range=T.Range*T.UnitsToCM;C.AimRadius=T.AimRadius*T.UnitsToCM;C.ChainRange=T.ChainRange*T.UnitsToCM;
    C.StunSeconds=T.StunBase+L*T.StunPerLevel;C.ChainDecay=T.ChainDecay;
    C.Duration=T.Duration;C.Fade=T.Fade;C.Segments=T.Segments;C.Jitter=T.Jitter;
    C.ElectrifyStacks=T.ElectrifyStacks;C.ElectrifyDuration=T.ElectrifyDuration;C.ElectricBonusPerStack=T.ElectricBonusPerStack;
    C.OverloadStacks=T.OverloadStacks;C.OverloadStun=T.OverloadStun;C.OverloadRange=T.OverloadRange*T.UnitsToCM;
    C.OverloadDamage=FMath::FloorToFloat(T.OverloadBase+Matk*T.OverloadMagic+Intelligence*T.OverloadIntelligence);
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    C.MagicDamageBonus=(1+SetEffect(TEXT("magicDamage")))*Rune.MagicDamage-1;
    double DamageFactor=1,CostFactor=1,CooldownReduction=0;
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.Count+=int32(Craft(TEXT("lightningChainTargetsDelta")));
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+Craft(TEXT("critChancePercent"))+Craft(TEXT("magicCritPercent")));
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+Craft(TEXT("magicPenetrationPercent"));
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            const double Area=1+Craft(TEXT("magicRangePercent"));C.AimRadius*=Area;C.ChainRange*=Area;
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            C.StunSeconds+=Craft(TEXT("electricStunExtendMs"))/1000;
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
            const auto Data=CombatItemFormula::ReadOnly(*Item);const TSharedPtr<FJsonObject>* Effects=nullptr;FString Specialty;
            if(Data&&Data->TryGetObjectField(TEXT("_craftEffects"),Effects)&&(*Effects)->TryGetStringField(TEXT("staffSpecialty"),Specialty)&&Specialty==TEXT("electric"))
                DamageFactor+=Craft(TEXT("electricDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    C.Count=FMath::Max(1,C.Count);
    C.Damage=FMath::FloorToFloat(FMath::FloorToDouble(C.DamageBase+Matk*C.MagicMultiplier+Intelligence*C.IntelligenceMultiplier)*DamageFactor*MagicImplementMultiplier());
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor)*float(Rune.MagicCost));
    C.Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown"))));C.Cooldown*=Rune.MagicCooldown;
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

bool UColdSteelStatusModel::ApplyLightningHit(APawn* Shooter,AActor* Target,const FVector& Origin,const FLightningCast& Spell,float Damage,FLightningRewards& Batch,bool bTrain)
{
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||Target->ActorHasTag(TEXT("Friendly")))return false;
    FFireballRewards Rewards;Rewards.Victim=Target;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    bool Critical=false;
    // A locked spell has no aimed bone contact; it can randomly crit but cannot invent a headshot.
    const CombatFormulaRuntime::MagicHit Context{Spell.CriticalChance,Spell.CriticalDamageBonus,Spell.MagicPenetration,Spell.MagicDamageBonus,&Critical,false};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const FVector End=Target->GetActorLocation();
    FHitResult Hit(Target,Cast<UPrimitiveComponent>(Target->GetRootComponent()),End,(Origin-End).GetSafeNormal());
    Hit.TraceStart=Origin;Hit.TraceEnd=End;
    const float Applied=UGameplayStatics::ApplyPointDamage(Target,Damage,(End-Origin).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,ULightningDamage::StaticClass());
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

void UColdSteelStatusModel::FinishLightningCast(const FLightningRewards& Batch)
{
    SyncRuntime();auto P=Snapshot();const auto& T=LightningSkill.Lightning;
    ColdSteelSkills::AddExperience(P,LightningSkill,Batch.Hits*T.HitExperience+Batch.Kills*T.KillExperience+(Batch.Hits>=2?T.MultiHitExperience:0)+(Batch.Kills>=2?T.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,Batch.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+Batch.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    for(const auto& K:Batch.KillRewards){P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Batch.KillRewards)RewardedVictims.Add(K.Key);
}
