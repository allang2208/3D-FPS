#include "../UI/ColdSteelStatusModel.h"
#include "../UI/ColdSteelEnhancementSystem.h"
#include "../Dungeon/DungeonLayout.h"
#include "../Combat/CombatStatusFormula.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Weapons/MeleeWeaponStats.h"
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
{const auto* P=Current.Skills.Find(IceWallSkill.Id);return P?*P:FColdSteelSkillProgress();}

FIceWallCast UColdSteelStatusModel::IceWallStats(int32 AtLevel) const
{
    const int32 L=FMath::Clamp(AtLevel<0?IceWallProgress().Level:AtLevel,1,IceWallSkill.MaxLevel);
    const auto& T=IceWallSkill.IceWall;FIceWallCast C;
    C.FixedDamage=T.DamageBase+T.DamagePerLevel*L;
    C.IntelligenceContribution=Attribute(TEXT("int"))*(T.IntelligenceBase+L*T.IntelligencePerLevel);
    C.WisdomContribution=Attribute(TEXT("wis"))*(T.WisdomBase+L*T.WisdomPerLevel);
    C.Count=T.CountBase+(L-1)*T.CountPerLevel;C.SegmentSpacing=T.SegmentSpacing*T.UnitsToCM;
    C.Duration=T.Duration+(L-1)*T.DurationPerLevel;C.Range=T.Range*T.UnitsToCM;
    C.HighHeight=T.HighHeight;C.LowHeight=T.LowHeight;C.Thickness=T.Thickness;
    C.HoverDuration=T.HoverDuration;C.RiseSeconds=T.RiseSeconds;C.RiseHeight=T.RiseHeight;
    C.DropSeconds=T.DropSeconds;C.DropHeight=T.DropHeight;
    C.MaxHealth=T.MaxHealth+(L-1)*T.MaxHealthPerLevel;
    C.ManaCost=T.ManaCost;C.Cooldown=T.Cooldown;
    C.Knockback=T.Knockback*T.UnitsToCM;C.PushDistanceMultiplier=T.PushDistanceMultiplier;
    C.ChillRadius=T.ChillRadius*T.UnitsToCM;C.ChillInterval=T.ChillInterval;
    C.ChillDuration=T.ChillDuration;C.ChillSlow=T.ChillSlow;C.ChillStacks=T.ChillStacks;
    double CostFactor=1,CooldownReduction=0,ChainDamage=1;
    const auto* Player=RuntimePawn();
    const auto* Status=Player?Player->FindComponentByClass<UCombatStatusFormula>():nullptr;
    const int32 Chain=Status?Status->ChainSpellStacks():0;
    if(const auto* Item=Equipped();Item&&ColdSteelInventory::Text(*Item,TEXT("weaponType"))==TEXT("staff"))
        if(auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>())
        {
            auto Craft=[&](const TCHAR* Key){return E->CraftEffect(*Item,Key);};
            CostFactor+=Craft(TEXT("magicMpCostPercent"))+Chain*Craft(TEXT("chainSpellMpCostPercent"));
            CooldownReduction=Craft(TEXT("magicCooldownPercent"));C.Range*=1+Craft(TEXT("magicRangePercent"));
            C.CastSpeed=FMath::Max(.1f,float(1+Craft(TEXT("castSpeedPercent"))));
            ChainDamage+=Chain*Craft(TEXT("chainSpellDamagePercent"));
            C.bGrantChain=Craft(TEXT("chainSpellDamagePercent"))!=0;
            C.CastHasteStacks=Craft(TEXT("castHasteStacks"));C.CastHasteDuration=E->CraftEffect(*Item,TEXT("castHasteDuration"),5000)/1000;
            C.PendantChillSlow=Craft(TEXT("iceChillSlowPercent"));
            C.PendantChillSeconds=E->CraftEffect(*Item,TEXT("iceChillDuration"),3000)/1000;
        }
    const auto Rune=ColdSteelMelee::EquippedModifiers(this);
    // Original identity: INT + WIS physical impact, no magic critical/penetration.
    C.Damage=FMath::FloorToFloat(FMath::FloorToFloat(C.FixedDamage+C.IntelligenceContribution+C.WisdomContribution)*ChainDamage);
    C.ManaCost=FMath::Max(0.f,FMath::FloorToFloat(C.ManaCost*CostFactor)*float(Rune.MagicCost));
    C.Cooldown*=FMath::Max(.2,double(1-CooldownReduction)*(1-SetEffect(TEXT("cooldown"))));C.Cooldown*=Rune.MagicCooldown;
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
    SyncRuntime();auto P=Snapshot();P.bIceWallReserved=false;P.IceWallReservedMana=0;return CommitState(MoveTemp(P));
}

void UColdSteelStatusModel::ApplyIceWallSpawn(APawn* Shooter,const FIceWallPlacement& Plan,const FIceWallCast& C,TSet<AActor*>* Impacted)
{
    if(!Shooter||!Shooter->IsPlayerControlled()||!Shooter->HasAuthority())return;
    const auto Targets=IceWallPlacement::Monsters(GetWorld(),Plan,C);
    if(Impacted)*Impacted=Targets;
    int32 Hits=0,Kills=0;FFireballRewards Rewards;
    TGuardValue<FFireballRewards*> RewardScope(ActiveFireballRewards,&Rewards);
    for(auto* Target:Targets)
    {
        auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||Combat->IsDead()||Target==Shooter||Target->ActorHasTag(TEXT("Friendly")))continue;
        Rewards.Victim=Target;
        const float Applied=UGameplayStatics::ApplyDamage(Target,C.Damage,Shooter->GetController(),Shooter,nullptr);
        const bool bTraining=!Target->ActorHasTag(TEXT("Summoned"))&&!Target->ActorHasTag(TEXT("NoSkillTraining"));
        if(Applied>0)
        {if(auto* P=Cast<AFPSGAMECharacter>(Shooter))P->NotifyConfirmedWeaponHit(Target,Applied);if(bTraining){++Hits;if(Combat->IsDead())++Kills;}}
        if(Combat->IsDead())continue;
        // Apply the landing chill before displacement. Even a target pushed beyond
        // the later aura keeps this impact's slow; the initial aura excludes it.
        UCombatStatusFormula::GetOrAdd(Target)->AddChill(C.ChillStacks,C.ChillDuration,C.ChillSlow);
        if(Applied>0&&C.PendantChillSlow>0)
            UCombatStatusFormula::GetOrAdd(Target)->AddChill(1,C.PendantChillSeconds,C.PendantChillSlow);
    }
    SyncRuntime();auto P=Snapshot();const auto& T=IceWallSkill.IceWall;
    ColdSteelSkills::AddExperience(P,IceWallSkill,Hits*T.HitExperience+Kills*T.KillExperience+(Hits>=2?T.MultiHitExperience:0));
    for(const auto& K:Rewards.Kills){if(!DungeonLayout::RecordKill(P.DungeonRun,K.Key.Get()))continue;P.Kills=FMath::Min(P.Kills+1,MAX_int32-1);P.Experience+=FMath::FloorToInt64(K.Value*TributeEffect(TEXT("expPercent")));}
    while(P.Level<10000){const int64 Need=(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8;if(P.Experience<Need)break;P.Experience-=Need;++P.Level;P.Points=FMath::Min(P.Points+3,1000000);}
    if(P.Level==10000)P.Experience=FMath::Min(P.Experience,(20ll+P.Level*20ll+int64(P.Level)*P.Level*12)*8-1);
    if(StageTraining(MoveTemp(P)))for(const auto& K:Rewards.Kills)RewardedVictims.Add(K.Key);
}

void UColdSteelStatusModel::ApplyIceWallChill(APawn* Shooter,const FIceWallPlacement& Plan,const FIceWallCast& C,const TSet<AActor*>* Excluded)
{
    if(!Shooter||!Shooter->HasAuthority()||C.ChillRadius<=0)return;
    const auto Targets=IceWallPlacement::Monsters(GetWorld(),Plan,C,C.ChillRadius);
    for(auto* Target:Targets)
    {
        if((Excluded&&Excluded->Contains(Target))||Target==Shooter||Target->ActorHasTag(TEXT("Friendly")))continue;
        const auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();if(!Combat||Combat->IsDead())continue;
        const FVector At=Plan.Rotation.UnrotateVector(Target->GetActorLocation()-Plan.Location);
        if(const auto* Capsule=Target->FindComponentByClass<UCapsuleComponent>();Capsule&&FMath::Abs(Capsule->GetComponentLocation().Z-Capsule->GetScaledCapsuleHalfHeight()-Plan.Location.Z-IceWallPlacement::GroundAt(Plan,float(At.X),float(At.Y)))>45)continue;
        const float X=FMath::Max(0.f,float(FMath::Abs(At.X))-C.Thickness*.5f);
        const float Y=FMath::Max(0.f,FMath::Max(Plan.MinAlong()-float(At.Y),float(At.Y)-Plan.MaxAlong()));
        if(X*X+Y*Y<=C.ChillRadius*C.ChillRadius)UCombatStatusFormula::GetOrAdd(Target)->AddChill(C.ChillStacks,C.ChillDuration,C.ChillSlow);
    }
}
