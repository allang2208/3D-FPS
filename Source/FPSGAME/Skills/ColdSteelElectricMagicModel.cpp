#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Combat/CombatItemFormula.h"
#include "../Dungeon/DungeonLayout.h"
#include "ColdSteelSkillRules.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"
#include "Dom/JsonObject.h"

const FColdSteelSkillDefinition& UColdSteelStatusModel::ElectricMagicDefinition(FName Id) const
{return Id==TEXT("stormDomain")?StormDomainSkill:ThunderLanceSkill;}
FColdSteelSkillProgress UColdSteelStatusModel::ElectricMagicProgress(FName Id) const
{const auto* P=Current.Skills.Find(Id);return P?*P:FColdSteelSkillProgress();}
float UColdSteelStatusModel::ElectricMagicCooldown(FName Id) const
{return HasNoAbilityCooldown()?0.f:Current.ElectricCooldowns.FindRef(Id);}
float UColdSteelStatusModel::ElectricMagicCooldownDuration(FName Id) const
{return Current.ElectricCooldownDurations.FindRef(Id);}
FElectricMagicCast UColdSteelStatusModel::ElectricMagicStats(FName Id,int32 AtLevel) const
{
    const auto& D=ElectricMagicDefinition(Id);const auto& T=D.ElectricMagic;
    const int32 L=FMath::Clamp(AtLevel<0?ElectricMagicProgress(Id).Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    FElectricMagicCast C;C.Hit=LightningStats();auto& H=C.Hit;
    H.DamageBase=T.DamageBase+L*T.DamagePerLevel;
    H.MagicMultiplier=T.MagicBase+L*T.MagicPerLevel;H.IntelligenceMultiplier=T.IntelligenceBase+L*T.IntelligencePerLevel;
    H.ManaCost=T.ManaBase+FMath::FloorToFloat(Growth*T.ManaGrowth);
    H.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    H.Range=(T.RangeBase+L*T.RangePerLevel)*T.UnitsToCM;
    H.ChainRange=T.ChainRange*T.UnitsToCM;H.Count=1+T.ChainExtraBase+(L-1)/FMath::Max(1,T.ChainLevelStep);
    H.ChainDecay=T.ChainDecay;H.StunSeconds=T.StunSeconds;
    H.ElectrifyStacks=T.ElectrifyStacks;H.ElectrifyDuration=T.ElectrifySeconds;
    H.Duration=Id==TEXT("stormDomain")?.42f:T.BeamHold;H.Fade=Id==TEXT("stormDomain")?.22f:T.BeamFade;
    H.Segments=Id==TEXT("stormDomain")?9:2;H.Jitter=Id==TEXT("stormDomain")?.10f:0.f;
    C.Radius=(T.RadiusBase+L*T.RadiusPerLevel)*T.UnitsToCM;
    C.Duration=T.Duration+FMath::FloorToFloat(Growth*T.DurationGrowth);C.StrikeSeconds=T.StrikeSeconds;
    C.MinCharge=T.MinCharge;C.MaxCharge=T.MaxCharge;C.ChargeBonus=T.ChargeBonus;C.StackDamage=T.StackDamage;C.bRequiresStaff=T.bRequiresStaff;
    C.HalfWidth=T.HalfWidth*T.UnitsToCM;C.Knockback=(T.KnockbackBase+FMath::FloorToFloat(Growth*T.KnockbackGrowth))*T.UnitsToCM;
    C.EndRadius=T.EndRadius*T.UnitsToCM;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    const auto* Player=UGameplayStatics::GetPlayerPawn(this,0);
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    double DamageFactor=1,CostFactor=1,CooldownReduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));
            const float Range=float(1+Craft(TEXT("magicRangePercent")));H.Range*=Range;H.ChainRange*=Range;C.Radius*=Range;
            H.StunExtensionSeconds=Craft(TEXT("electricStunExtendMs"))/1000;
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            const auto Data=CombatItemFormula::ReadOnly(*Item);const TSharedPtr<FJsonObject>* Effects=nullptr;FString Specialty;
            if(Data&&Data->TryGetObjectField(TEXT("_craftEffects"),Effects)&&(*Effects)->TryGetStringField(TEXT("staffSpecialty"),Specialty)&&Specialty==TEXT("electric"))
                DamageFactor+=Craft(TEXT("electricDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    H.Damage=FMath::FloorToFloat(FMath::FloorToDouble(H.DamageBase+Derived(TEXT("matk"))*H.MagicMultiplier+Attribute(TEXT("int"))*H.IntelligenceMultiplier)*DamageFactor*MagicImplementMultiplier());
    H.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(H.ManaCost*CostFactor)*float(Rune.MagicCost));
    H.Cooldown=FMath::Clamp(H.Cooldown*float(FMath::Max(.2,(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown")))))*float(Rune.MagicCooldown),0.f,300.f);
    return C;
}
bool UColdSteelStatusModel::BeginElectricMagicCast(FName Id,const FElectricMagicCast& Spell)
{
    if(!ElectricMagic::IsSkill(Id)||Current.ElectricReservedMana.Contains(Id)||ElectricMagicCooldown(Id)>0||!CanSpendMana(Spell.Hit.ManaCost)||(Spell.bRequiresStaff&&!HasEquippedStaff()))return false;
    SyncRuntime();auto P=Snapshot();const float Before=P.Mana;
    if(!HasInfiniteMana())P.Mana-=Spell.Hit.ManaCost;
    P.ElectricReservedMana.Add(Id,Before-P.Mana);
    P.ElectricCooldowns.Add(Id,HasNoAbilityCooldown()?0.f:Spell.Hit.Cooldown);
    P.ElectricCooldownDurations.Add(Id,P.ElectricCooldowns.FindRef(Id));
    return CommitState(MoveTemp(P));
}
bool UColdSteelStatusModel::CommitElectricMagicRelease(FName Id)
{
    if(!Current.ElectricReservedMana.Contains(Id))return false;
    SyncRuntime();auto P=Snapshot();P.ElectricReservedMana.Remove(Id);return CommitState(MoveTemp(P));
}
void UColdSteelStatusModel::FinishElectricMagicCast(FName Id,const FElectricMagicRewards& Batch)
{
    if(!ElectricMagic::IsSkill(Id)||Batch.Hit.Hits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& D=ElectricMagicDefinition(Id);const auto& T=D.ElectricMagic;const auto& R=Batch.Hit;
    ColdSteelSkills::AddExperience(P,D,R.Hits*T.HitExperience+R.Kills*T.KillExperience+(Batch.bMultiHit?T.MultiHitExperience:0)+(R.Kills>=2?T.MultiKillExperience:0));
    ColdSteelSkills::AddExperience(P,CriticalStrikeSkill,R.CriticalHits*CriticalStrikeSkill.CriticalHitExperience+R.CriticalKills*CriticalStrikeSkill.CriticalKillExperience);
    for(const auto& K:R.KillRewards){if(!DungeonLayout::RecordKill(P.DungeonRun,K.Key.Get()))continue;P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(StageTraining(MoveTemp(P)))for(const auto& K:R.KillRewards)RewardedVictims.Add(K.Key);
}
