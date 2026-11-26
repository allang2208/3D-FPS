#include "ProductionToolComponent.h"
#include "../Weapons/PojunGrip.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundBase.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Skills/ColdSteelSkillRules.h"
#include "../Weapons/RuneSwordHitQuery.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"

namespace
{
bool IsAxeEnemy(AActor* Target,AActor* Owner)
{
    const auto* Combat=IsValid(Target)?Target->FindComponentByClass<UMonsterCombatComponent>():nullptr;
    const auto* Pawn=Cast<APawn>(Target);
    return Target!=Owner && Combat && !Combat->IsDead() && Target->CanBeDamaged() &&
        !Target->ActorHasTag(TEXT("Friendly")) && !Target->ActorHasTag(TEXT("Player")) &&
        (!Pawn || !Pawn->IsPlayerControlled());
}

bool SameAxeTarget(const FHitResult& A,const FHitResult& B,bool bEnemy)
{
    if(bEnemy)return A.GetActor()==B.GetActor();
    // The entire terrain and many trunks share one world actor. Actor equality
    // would allow chopping through a wall, rock or a different tree instance.
    return A.GetComponent()==B.GetComponent() && A.Item==B.Item;
}
}

bool UProductionToolComponent::TraceAxeContact(FProductionResource& Resource,FHitResult& Hit,FString& Reason) const
{
    Resource={};Hit=FHitResult();
    auto* Pawn=Character.Get();auto* World=GetWorld();
    if(!Pawn || !World)return false;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    const FVector Start=Aim.GetLocation(),Forward=Aim.GetUnitAxis(EAxis::X);
    const float MaxReach=FMath::Max(AxeHarvestReach,AxeCombatReach);
    const FVector End=Start+Forward*MaxReach;
    const FCollisionQueryParams Query(SCENE_QUERY_STAT(ProductionAxeContact),false,Pawn);
    Reason=FString::Printf(TEXT("瞄准%s（%.1f 米内）或近身敌人（%.1f 米内）"),
        Kind==TEXT("pickaxe")?TEXT("独立岩块或矿石"):TEXT("树干"),AxeHarvestReach/100,AxeCombatReach/100);

    if(Kind==TEXT("warhammer"))Reason=TEXT("双手战锤 · 左键三连击");

    auto Classify=[&](const FHitResult& Candidate,FProductionResource& Tree,bool& bEnemy)
    {
        bEnemy=IsAxeEnemy(Candidate.GetActor(),Pawn);
        const FVector Delta=Candidate.ImpactPoint-Start;
        const float Limit=(bEnemy || Kind==TEXT("warhammer"))?AxeCombatReach:AxeHarvestReach;
        // Swept volume adds width only; its front cap does not extend reach.
        if(FVector::DotProduct(Delta,Forward)<0 || Delta.SizeSquared()>FMath::Square(Limit))return false;
        if(bEnemy || Cast<UWardBreakableGlass>(Candidate.GetComponent()))return true;
        if(Kind==TEXT("warhammer"))return false;
        FString TreeReason;
        if(FProductionResource::ResolveHit(World,Candidate,Tree,TreeReason))return Tree.RequiredTool==Kind;
        if(!TreeReason.IsEmpty())Reason=TreeReason;
        return false;
    };
    auto SetResult=[&](const FHitResult& Selected,const FProductionResource& Tree,bool bEnemy)
    {
        Hit=Selected;Hit.TraceStart=Start;Hit.TraceEnd=End;Resource=Tree;
        if(Cast<UWardBreakableGlass>(Selected.GetComponent()))Reason=TEXT("玻璃 · 左键击碎");
        else if(bEnemy)Reason=TEXT("敌人 · 左键攻击（单目标物理伤害）");
    };

    // An exact crosshair contact wins over nearby assistance candidates.
    FHitResult Center;
    if(World->LineTraceSingleByChannel(Center,Start,End,ECC_Visibility,Query))
    {
        FProductionResource Tree;bool bEnemy=false;
        if(Classify(Center,Tree,bEnemy)){SetResult(Center,Tree,bEnemy);return true;}
    }

    bool bFound=false;
    double BestOffset=MAX_dbl,BestDistance=MAX_dbl;
    const FCollisionObjectQueryParams Objects(FCollisionObjectQueryParams::AllObjects);
    // Object sweeps collect candidates without stopping at an incidental floor
    // edge. A separate visibility ray must reach each selected surface.
    for(bool bEnemyPass:{false,true})
    {
        const float Radius=bEnemyPass?AxeCombatRadius:AxeHarvestRadius;
        const float Length=bEnemyPass?AxeCombatReach:AxeHarvestReach;
        // A zero radius keeps the pickaxe's existing crosshair-only mining.
        if(Radius<=0.f)continue;
        TArray<FHitResult> Candidates;
        World->SweepMultiByObjectType(Candidates,Start,Start+Forward*Length,FQuat::Identity,
            Objects,FCollisionShape::MakeSphere(Radius),Query);
        for(FHitResult Candidate:Candidates)
        {
            if(!Candidate.GetComponent() || IsAxeEnemy(Candidate.GetActor(),Pawn)!=bEnemyPass)continue;
            // Initial overlaps have no surface point. Probe toward this instance,
            // keeping eye height, instead of trusting the sweep's start position.
            if(Candidate.bStartPenetrating)
            {
                FVector Probe=Candidate.GetComponent()->GetBounds().Origin;
                if(const auto* Instances=Cast<UInstancedStaticMeshComponent>(Candidate.GetComponent()))
                {
                    FTransform Instance;
                    if(!Instances->GetInstanceTransform(Candidate.Item,Instance,true))continue;
                    Probe=Instance.GetLocation();
                }
                const auto& Bounds=Candidate.GetComponent()->GetBounds();
                Probe.Z=bEnemyPass?FMath::Clamp(Start.Z,Bounds.Origin.Z-Bounds.BoxExtent.Z+1,
                    Bounds.Origin.Z+Bounds.BoxExtent.Z-1):Start.Z;
                FHitResult Surface;
                if(!World->LineTraceSingleByChannel(Surface,Start,Probe,ECC_Visibility,Query) ||
                    !SameAxeTarget(Surface,Candidate,bEnemyPass))continue;
                Candidate=Surface;
            }
            FProductionResource Tree;bool bEnemy=false;
            if(!Classify(Candidate,Tree,bEnemy) || bEnemy!=bEnemyPass)continue;
            const FVector Delta=Candidate.ImpactPoint-Start;
            const double Along=FVector::DotProduct(Delta,Forward);
            const double Offset=(Delta-Forward*Along).SizeSquared();
            if(Offset>FMath::Square(Radius))continue;
            FHitResult Cover;
            if(World->LineTraceSingleByChannel(Cover,Start,Candidate.ImpactPoint+Delta.GetSafeNormal()*2,
                ECC_Visibility,Query) && !SameAxeTarget(Cover,Candidate,bEnemy))continue;
            if(Offset>BestOffset || (FMath::IsNearlyEqual(Offset,BestOffset) && Delta.SizeSquared()>=BestDistance))continue;
            BestOffset=Offset;BestDistance=Delta.SizeSquared();bFound=true;
            SetResult(Candidate,Tree,bEnemy);
        }
    }
    if(bFound && Resource.Id.IsEmpty() && !Cast<UWardBreakableGlass>(Hit.GetComponent()))Reason=TEXT("敌人 · 左键攻击（单目标物理伤害）");
    return bFound;
}

bool UProductionToolComponent::PredictBluntEnemyContact() const
{
    auto* Pawn=Character.Get();if(!Pawn||!GetWorld())return false;
    const bool Pofeng=!bBluntHeavy&&BluntStage==2&&ToolStats.PofengFinisherMultiplier.IsSet();
    for(const auto& Hit:BluntContactHits(Pofeng))
        if(IsAxeEnemy(Hit.GetActor(),Pawn))return true;
    return false;
}

void UProductionToolComponent::MulticastPojunCutImpact_Implementation(FVector_NetQuantize Location)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    if(auto* Sound=LoadObject<USoundBase>(nullptr,PojunGrip::SwordHit))
        UGameplayStatics::PlaySoundAtLocation(this,Sound,Location,.75f);
}

bool UProductionToolComponent::ResolveAxeEnemyContact(const FHitResult& Hit)
{
    auto* Pawn=Character.Get();auto* Target=Hit.GetActor();
    if(!Pawn || !IsAxeEnemy(Target,Pawn))return false;
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    FWeaponDamageResult Result;
    auto ContactShot=AxeStrike;ContactShot.ToughnessDamageMultiplier*=FinalTollToughnessMultiplier(ContactShot,Target);
    const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,ContactShot.DamagePanel.Total(),
        (Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),ContactShot,&Result);
    const bool bConfirmed=Applied>0.f || Combat->IsDead();
    if(bConfirmed)
    {
        if(ContactShot.ItemDefinition==PojunGrip::Weapon)MulticastPojunCutImpact(Hit.ImpactPoint);
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        Feedback=Kind==TEXT("warhammer")?TEXT("战锤命中敌人"):Kind==TEXT("pickaxe")?TEXT("镐头命中敌人"):TEXT("斧刃命中敌人");FeedbackSeconds=1.2f;
    }
    // The existing confirmed-hit clock supplies hit stop, pry/recover and shake.
    // Enemy contacts do not call harvest commits, spawn wood dust or play wood audio.
    return bConfirmed;
}
bool UProductionToolComponent::TraceShovelEnemyContact(FHitResult& Hit) const
{
    // Same combat trace family as the axe/pickaxe: the melee aim transform and
    // the shovel's evaluated combat reach - never the long dig-ray.
    auto* Pawn=Character.Get();
    if(!Pawn||!Camera)return false;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    const FVector Start=Aim.GetLocation(),Forward=Aim.GetUnitAxis(EAxis::X);
    const float CombatReach=FMath::Max(float(ToolStats.CombatReachCM),100.f);
    FCollisionQueryParams Q(SCENE_QUERY_STAT(ProductionShovel),false,Pawn);
    return GetWorld()->LineTraceSingleByChannel(Hit,Start,Start+Forward*CombatReach,ECC_Visibility,Q)
        && IsAxeEnemy(Hit.GetActor(),Pawn);
}

bool UProductionToolComponent::ResolveShovelEnemyContact(const FHitResult& Hit)
{
    auto* Pawn=Character.Get();auto* Target=Hit.GetActor();
    if(!Pawn || !IsAxeEnemy(Target,Pawn))return false;
    auto* Combat=Target->FindComponentByClass<UMonsterCombatComponent>();
    FWeaponDamageResult Result;
    const float Applied=ColdSteelSkills::ApplyHit(Pawn,Hit,AxeStrike.DamagePanel.Total(),
        (Hit.TraceEnd-Hit.TraceStart).GetSafeNormal(),AxeStrike,&Result);
    const bool bConfirmed=Applied>0.f || Combat->IsDead();
    if(bConfirmed)
    {
        Pawn->NotifyConfirmedWeaponHit(Target,Applied,&Result);
        Feedback=TEXT("铲头命中敌人");FeedbackSeconds=1.2f;
    }
    return bConfirmed;
}
