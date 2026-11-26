#include "../UI/ColdSteelStatusModel.h"
#include "IceSpikeDamage.h"
#include "../Monsters/UnknownSpellCombat.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "ColdSteelSpellRewards.h"
#include "ColdSteelSpellFeedback.h"
#include "ColdSteelSpellCrafting.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
#include "../Weapons/StarMarrowComponent.h"
#include "../FPSGAMECharacter.h"
#include "ColdSteelSkillRules.h"
#include "IceWallPlacement.h"
#include "Components/PrimitiveComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"
#include "GameFramework/Character.h"
#include "Kismet/GameplayStatics.h"

FColdSteelSkillProgress UColdSteelStatusModel::IceWallProgress() const
{return Current.Skills.FindRef(IceWallSkill.Id);}

FIceWallCast UColdSteelStatusModel::IceWallStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?IceWallProgress().Level:AtLevel,1,IceWallSkill.MaxLevel);
    const auto& T=IceWallSkill.IceWall;FIceWallCast C;
    const int32 DamageLevel=L-1;
    C.FixedDamage=T.DamageBase+T.DamagePerLevel*DamageLevel;
    C.IntelligenceContribution=Attribute(TEXT("int"))*(T.IntelligenceBase+DamageLevel*T.IntelligencePerLevel);
    C.WisdomContribution=Attribute(TEXT("wis"))*(T.WisdomBase+DamageLevel*T.WisdomPerLevel);
    C.Count=T.CountBase+(L-1)*T.CountPerLevel;C.SegmentSpacing=T.SegmentSpacing*T.UnitsToCM;
    C.Duration=T.Duration+(L-1)*T.DurationPerLevel;C.Range=T.Range*T.UnitsToCM;
    C.HighHeight=T.HighHeight;C.LowHeight=T.LowHeight;C.Thickness=T.Thickness;
    C.HoverDuration=T.HoverDuration;C.RiseSeconds=T.RiseSeconds;C.RiseHeight=T.RiseHeight;
    C.DropSeconds=T.DropSeconds;C.DropHeight=T.DropHeight;
    C.MaxHealth=T.MaxHealth+(L-1)*T.MaxHealthPerLevel;
    C.Cooldown=T.Cooldown;
    C.Knockback=T.Knockback*T.UnitsToCM;C.PushDistanceMultiplier=T.PushDistanceMultiplier;
    C.ChillRadius=T.ChillRadius*T.UnitsToCM;C.ChillInterval=T.ChillInterval;
    C.ChillDuration=T.ChillDuration;C.ChillSlow=T.ChillSlow;C.ChillStacks=T.ChillStacks;
    double CooldownReduction=0,ChainDamage=1;
    const int32 Chain=ColdSteelSpellCrafting::ChainSpellStacks(RuntimePawn());
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            ChainDamage+=Chain*Craft(TEXT("chainSpellDamagePercent"));
            ColdSteelSpellCrafting::ApplyChainAndCastHaste(C,*E,*Item);
            C.PendantChillSlow=Craft(TEXT("iceChillSlowPercent"))>0?CombatChill::SlowPerStack:0.f;
            C.PendantChillSeconds=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
        }
    C.Range*=float(MagicRangeMultiplier());
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    // Original identity: INT + WIS physical impact, no magic critical/penetration.
    C.Damage=FMath::FloorToFloat(FMath::FloorToFloat(C.FixedDamage+C.IntelligenceContribution+C.WisdomContribution)*ChainDamage);
    C.ManaCost=SpellManaCost(TEXT("iceWall"),L);
    ColdSteelSpellCrafting::ApplyCooldownMultipliers(C.Cooldown,CooldownReduction,SetEffect(TEXT("cooldown")),
        Rune.SkillCooldown*Rune.MagicCooldown);
    ApplySpellCastSpeed(C.CastSpeed);
    return C;
}

bool UColdSteelStatusModel::BeginIceWallCast(const FIceWallCast& C)
{
    if(IceWallSkill.IceWall.bRequiresStaff&&!HasEquippedStaff())return false;
    if(Current.bIceWallReserved||IceWallCooldown()>0||!CanSpendMana(C.ManaCost))return false;
    SyncRuntime();auto P=Snapshot();P.IceWallReservedMana=HasInfiniteMana()?0.f:C.ManaCost;P.Mana-=P.IceWallReservedMana;
    P.bIceWallReserved=true;P.IceWallCooldown=HasNoAbilityCooldown()?0.f:C.Cooldown;
    P.IceWallCooldownDuration=P.IceWallCooldown;return CommitState(MoveTemp(P));
}
bool UColdSteelStatusModel::CommitIceWallRelease()
{
    if(IceWallSkill.IceWall.bRequiresStaff&&!HasEquippedStaff())return false;
    if(!Current.bIceWallReserved)return false;
    SyncRuntime();auto P=Snapshot();P.bIceWallReserved=false;P.IceWallReservedMana=0;const bool Released=CommitState(MoveTemp(P));
    if(Released)NotifyMagicReleased();return Released;
}

void UColdSteelStatusModel::ApplyIceWallSpawn(APawn* Shooter,const FIceWallPlacement& Plan,const FIceWallCast& C,TSet<AActor*>* Impacted)
{
    if(UnknownSpell::IsCaster(Shooter))
    {
        for(auto* Target:IceWallPlacement::Monsters(Shooter->GetWorld(),Plan,C))
        {
            if(!UnknownSpell::IsTarget(Shooter,Target))continue;
            if(Impacted)Impacted->Add(Target);
            UGameplayStatics::ApplyDamage(Target,C.Damage,Shooter->GetController(),Shooter,UIceSpikeDamage::StaticClass());
            UCombatStatusFormula::GetOrAdd(Target)->AddChill(C.ChillStacks,C.ChillDuration);
        }
        return;
    }
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority())return;
    const auto Targets=IceWallPlacement::Monsters(GetWorld(),Plan,C);
    if(Impacted)*Impacted=Targets;
    int32 Hits=0,Kills=0;FFireballRewards Rewards;
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,&Rewards);
    for(auto* Target:Targets)
    {
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||Combat->IsDead()||Target==Shooter||Target->ActorHasTag(TEXT("Friendly")))continue;
        Rewards.Victim=Target;
        const bool bMagicDamage=UStarMarrowComponent::ChargesDamage(Shooter);
        const float Applied=UGameplayStatics::ApplyDamage(Target,C.Damage,Shooter->GetController(),Shooter,nullptr);
        const bool bTraining=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
        if(Applied>0)
        {
            ColdSteelSpellFeedback::NotifyHit(Shooter,Target,Applied,*Combat,false,bMagicDamage);
            if(bTraining){++Hits;if(Combat->IsDead())++Kills;}
        }
        if(Combat->IsDead())continue;
        // Apply the landing chill before displacement. Even a target pushed beyond
        // the later aura keeps this impact's slow; the initial aura excludes it.
        UCombatStatusFormula::GetOrAdd(Target)->AddChill(C.ChillStacks,C.ChillDuration);
        if(Applied>0&&C.PendantChillSlow>0)
            UCombatStatusFormula::GetOrAdd(Target)->AddChill(1,C.PendantChillSeconds);
    }
    SyncRuntime();auto P=Snapshot();const auto& T=IceWallSkill.IceWall;
    ColdSteelSkills::AddExperience(P,IceWallSkill,ColdSteelSpellRewards::HitTrainingExperience(T,Hits,Kills,Hits>=2));
    ColdSteelSpellRewards::AccumulateKillExperience(P,Rewards.Kills,*this);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Rewards.Kills)RewardedVictims.Add(K.Key);
}

void UColdSteelStatusModel::ApplyIceWallChill(APawn* Shooter,const FIceWallPlacement& Plan,const FIceWallCast& C,const TSet<AActor*>* Excluded)
{
    if(!Shooter||!Shooter->HasAuthority()||C.ChillRadius<=0)return;
    const auto Targets=IceWallPlacement::Monsters(GetWorld(),Plan,C,C.ChillRadius);
    for(auto* Target:Targets)
    {
        if((Excluded&&Excluded->Contains(Target))||Target==Shooter||(!Plan.bHostileCaster&&Target->ActorHasTag(TEXT("Friendly"))))continue;
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
        if(UnknownSpell::IsCaster(Shooter)?!UnknownSpell::IsTarget(Shooter,Target):(!Combat||Combat->IsDead()))continue;
        const FVector At=Plan.Rotation.UnrotateVector(Target->GetActorLocation()-Plan.Location);
        if(const auto* Capsule=Target->FindComponentByClass<UCapsuleComponent>();Capsule&&FMath::Abs(Capsule->GetComponentLocation().Z-Capsule->GetScaledCapsuleHalfHeight()-Plan.Location.Z-IceWallPlacement::GroundAt(Plan,float(At.X),float(At.Y)))>45)continue;
        const float X=FMath::Max(0.f,float(FMath::Abs(At.X))-C.Thickness*.5f);
        const float Y=FMath::Max(0.f,FMath::Max(Plan.MinAlong()-float(At.Y),float(At.Y)-Plan.MaxAlong()));
        if(X*X+Y*Y<=C.ChillRadius*C.ChillRadius)UCombatStatusFormula::GetOrAdd(Target)->AddChill(C.ChillStacks,C.ChillDuration);
    }
}
