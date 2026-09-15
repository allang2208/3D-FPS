#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatFormulaRuntime.h"
#include "../Combat/CombatItemFormula.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "IceSpikeDamage.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"

FColdSteelSkillProgress UColdSteelStatusModel::IceSpikeProgress() const
{const auto* P=Current.Skills.Find(IceSpikeSkill.Id);return P?*P:FColdSteelSkillProgress();}

FIceSpikeCast UColdSteelStatusModel::IceSpikeStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?IceSpikeProgress().Level:AtLevel,1,IceSpikeSkill.MaxLevel);
    const auto& T=IceSpikeSkill.IceSpike;FIceSpikeCast C;
    C.DamageBase=T.DamageBase+L*T.DamagePerLevel;
    C.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;C.IntMultiplier=T.IntBase+L*T.IntPerLevel;
    C.MagicContribution=Derived(TEXT("matk"))*C.MagicMultiplier;
    const double IntBonus=EquipmentBonus(TEXT("intt"));
    C.IntContribution=(Attribute(TEXT("intt"))+IntBonus-int32(IntBonus))*C.IntMultiplier;
    C.Count=T.CountBase+(L-1)/T.CountLevelStep;
    C.ManaCost=T.ManaCost;C.Cooldown=T.Cooldown;C.HoverDuration=T.HoverDuration;
    C.Speed=T.Speed*T.UnitsToCM;C.Range=T.Range*T.UnitsToCM;
    C.CriticalChance=Derived(TEXT("crit"));C.CriticalDamageBonus=CriticalStrikeEffect().CriticalDamageBonus;
    C.MagicDamageBonus=SetEffect(TEXT("magicDamage"));
    double DamageFactor=1,CostFactor=1,CooldownReduction=0;
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    // Only the active staff contributes spell crafting. The immutable cast survives weapon swaps.
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            C.Count+=int32(Craft(TEXT("iceSpikeCountDelta")));
            C.CriticalChance+=100*(E->Effect(*Item,TEXT("critRate"))+Craft(TEXT("critChancePercent"))+Craft(TEXT("magicCritPercent")));
            C.MagicPenetration=E->Effect(*Item,TEXT("magicPenetrationPercent"))+Craft(TEXT("magicPenetrationPercent"));
            CostFactor+=Craft(TEXT("magicMpCostPercent"));CooldownReduction=Craft(TEXT("magicCooldownPercent"));
            C.Range*=1+Craft(TEXT("magicRangePercent"));C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            CostFactor+=Chain*Craft(TEXT("chainSpellMpCostPercent"));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
            C.ChillSlow=Craft(TEXT("iceChillSlowPercent"));C.ChillDuration=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
            const auto Data=CombatItemFormula::Read(*Item);const TSharedPtr<FJsonObject>* Effects=nullptr;FString Specialty;
            if(Data&&Data->TryGetObjectField(TEXT("_craftEffects"),Effects)&&(*Effects)->TryGetStringField(TEXT("staffSpecialty"),Specialty)&&Specialty==TEXT("ice"))
                DamageFactor+=Craft(TEXT("iceDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    C.Count=FMath::Max(1,C.Count);
    C.Damage=FMath::FloorToFloat(FMath::FloorToDouble(C.DamageBase+C.MagicContribution+C.IntContribution)*DamageFactor);
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor));
    C.Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown"))));
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

void UColdSteelStatusModel::ApplyIceSpikeHit(APawn* Shooter,const FHitResult& Hit,const FIceSpikeCast& Cast,FIceSpikeRewards& Batch)
{
    AActor* Target=Hit.GetActor();
    auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority()||Target==Shooter||!Combat||Combat->IsDead()||Target->ActorHasTag(TEXT("Friendly")))return;
    FFireballRewards Rewards;Rewards.Victim=Target;TGuardValue<FFireballRewards*> Scope(ActiveFireballRewards,&Rewards);
    bool Critical=false;
    const CombatFormulaRuntime::MagicHit Context{Cast.CriticalChance,Cast.CriticalDamageBonus,Cast.MagicPenetration,Cast.MagicDamageBonus,&Critical,ColdSteelSkills::IsCriticalHit(Hit)};
    TGuardValue<const CombatFormulaRuntime::MagicHit*> MagicScope(CombatFormulaRuntime::ActiveMagicHit,&Context);
    const float Applied=UGameplayStatics::ApplyPointDamage(Target,Cast.Damage,(Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),Hit,Shooter->GetController(),Shooter,UIceSpikeDamage::StaticClass());
    for(const auto& K:Rewards.Kills)Batch.KillRewards.FindOrAdd(K.Key)=K.Value;
    if(Applied<=0)return;
    if(Cast.ChillSlow>0&&!Combat->IsDead())UCombatStatusFormula::GetOrAdd(Target)->AddChill(1,Cast.ChillDuration,Cast.ChillSlow);
    if(auto* Player=::Cast<AFPSGAMECharacter>(Shooter))Player->NotifyConfirmedWeaponHit(Target,Applied);
    if(Target->ActorHasTag(TEXT("Summoned"))||Target->ActorHasTag(TEXT("NoSkillTraining")))return;
    ++Batch.Hits;if(Combat->IsDead())++Batch.Kills;
    if(Critical){++Batch.CriticalHits;if(Combat->IsDead())++Batch.CriticalKills;}
}

void UColdSteelStatusModel::FinishIceSpikeCast(const FIceSpikeRewards& Batch)
{
    if(!Current.bIceSpikeReserved)return;
    SyncRuntime();auto P=Snapshot();P.bIceSpikeReserved=false;
    const auto& T=IceSpikeSkill.IceSpike;
    ColdSteelSkills::AddExperience(P,IceSpikeSkill,Batch.Hits*T.HitExperience+Batch.Kills*T.KillExperience+(Batch.Hits>=2?T.MultiHitExperience:0)+(Batch.Kills>=2?T.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,Batch.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+Batch.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    for(const auto& K:Batch.KillRewards){P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(CommitState(P))for(const auto& K:Batch.KillRewards)RewardedVictims.Add(K.Key);
}
