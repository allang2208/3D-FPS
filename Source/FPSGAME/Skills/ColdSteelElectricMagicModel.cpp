#include "../UI/ColdSteelStatusModel.h"
#include "ColdSteelSpellCrafting.h"
#include "LightningHasteSpeed.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "ColdSteelSpellRewards.h"
#include "Engine/GameInstance.h"
#include "Kismet/GameplayStatics.h"

const FColdSteelSkillDefinition& UColdSteelStatusModel::ElectricMagicDefinition(FName Id) const
{return Id==TEXT("stormDomain")?StormDomainSkill:ThunderLanceSkill;}
FColdSteelSkillProgress UColdSteelStatusModel::ElectricMagicProgress(FName Id) const
{return Current.Skills.FindRef(Id);}
float UColdSteelStatusModel::ElectricMagicCooldown(FName Id) const
{return HasNoAbilityCooldown()?0.f:Current.ElectricCooldowns.FindRef(Id);}
float UColdSteelStatusModel::ElectricMagicCooldownDuration(FName Id) const
{return Current.ElectricCooldownDurations.FindRef(Id);}
FElectricMagicCast UColdSteelStatusModel::ElectricMagicStats(FName Id,int32 AtLevel) const
{
    const auto& D=ElectricMagicDefinition(Id);const auto& T=D.ElectricMagic;
    const int32 L=FMath::Clamp(AtLevel<0?ElectricMagicProgress(Id).Level:AtLevel,1,D.MaxLevel);
    const float Growth=float(L-1)/FMath::Max(1,D.MaxLevel-1);
    const int32 DamageLevel=L-1;
    FElectricMagicCast C;C.Hit=LightningStats(-1,false);auto& H=C.Hit;
    H.DamageBase=T.DamageBase+DamageLevel*T.DamagePerLevel;
    H.MagicMultiplier=T.MagicBase+DamageLevel*T.MagicPerLevel;H.IntelligenceMultiplier=T.IntelligenceBase+DamageLevel*T.IntelligencePerLevel;
    H.Cooldown=T.Cooldown-FMath::FloorToFloat(Growth*T.CooldownReduction);
    H.Range=(T.RangeBase+L*T.RangePerLevel)*T.UnitsToCM;
    H.ChainRange=T.ChainRange*T.UnitsToCM;H.Count=1+T.ChainExtraBase+(L-1)/FMath::Max(1,T.ChainLevelStep);
    H.ChainDecay=T.ChainDecay;H.StunSeconds=T.StunSeconds;
    H.ElectrifyStacks=T.ElectrifyStacks;H.ElectrifyDuration=T.ElectrifySeconds;
    H.Duration=Id==TEXT("stormDomain")?.42f:T.BeamHold;H.Fade=Id==TEXT("stormDomain")?.22f:T.BeamFade;
    H.Segments=Id==TEXT("stormDomain")?9:2;H.Jitter=Id==TEXT("stormDomain")?.10f:0.f;
    C.Radius=(T.RadiusBase+L*T.RadiusPerLevel)*T.UnitsToCM;
    C.Duration=T.Duration+FMath::FloorToFloat(Growth*T.DurationGrowth);C.StrikeSeconds=T.StrikeSeconds;
    C.MinCharge=T.MinCharge/LightningHaste::ActionSpeed(RuntimePawn());C.MaxCharge=T.MaxCharge/LightningHaste::ActionSpeed(RuntimePawn());C.ChargeBonus=T.ChargeBonus;C.StackDamage=T.StackDamage;C.bRequiresStaff=T.bRequiresStaff;
    C.HalfWidth=T.HalfWidth*T.UnitsToCM;C.Knockback=(T.KnockbackBase+FMath::FloorToFloat(Growth*T.KnockbackGrowth))*T.UnitsToCM;
    C.EndRadius=T.EndRadius*T.UnitsToCM;
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    double DamageFactor=1,CooldownReduction=0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));
            const float Range=float(1+Craft(TEXT("magicRangePercent")));H.Range*=Range;H.ChainRange*=Range;C.Radius*=Range;
            H.StunExtensionSeconds=Craft(TEXT("electricStunExtendMs"))/1000;
            DamageFactor+=Craft(TEXT("magicDamagePercent"));
            if(ColdSteelSpellCrafting::HasStaffSpecialty(*Item,TEXT("electric")))
                DamageFactor+=Craft(TEXT("electricDamagePercent"));
            DamageFactor*=1+Chain*Craft(TEXT("chainSpellDamagePercent"));
        }
    H.Range*=float(MagicRangeMultiplier());
    H.Damage=FMath::FloorToFloat(FMath::FloorToDouble(H.DamageBase+Derived(TEXT("matk"))*H.MagicMultiplier+Attribute(TEXT("int"))*H.IntelligenceMultiplier)*DamageFactor*MagicImplementMultiplier());
    H.ManaCost=SpellManaCost(Id,L);
    H.Cooldown=FMath::Clamp(H.Cooldown*float(FMath::Max(.2,(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown")))))*float(Rune.SkillCooldown*Rune.MagicCooldown),0.f,300.f);
    ApplySpellCastSpeed(H.CastSpeed);
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
    if(ElectricMagicDefinition(Id).ElectricMagic.bRequiresStaff&&!HasEquippedStaff())return false;
    SyncRuntime();auto P=Snapshot();P.ElectricReservedMana.Remove(Id);const bool Released=CommitState(MoveTemp(P));
    if(Released)NotifyMagicReleased();return Released;
}
void UColdSteelStatusModel::FinishElectricMagicCast(FName Id,const FElectricMagicRewards& Batch)
{
    if(!ElectricMagic::IsSkill(Id)||Batch.Hit.Hits<=0)return;
    SyncRuntime();auto P=Snapshot();const auto& D=ElectricMagicDefinition(Id);const auto& T=D.ElectricMagic;const auto& R=Batch.Hit;
    ColdSteelSpellRewards::AccumulateHitKillTraining(P,D,T,R.Hits,R.Kills,Batch.bMultiHit);
    ColdSteelSpellRewards::AccumulateCriticalTraining(P,CriticalStrikeSkill,R.CriticalHits,R.CriticalKills);
    ColdSteelSpellRewards::AccumulateKillExperience(P,R.KillRewards,*this);
    if(StageTraining(MoveTemp(P)))for(const auto& K:R.KillRewards)RewardedVictims.Add(K.Key);
}
