#include "ProductionToolComponent.h"
#include "WarhammerHeavyMotion.h"
#include "WarhammerShockwave.h"
#include "WarhammerCombat.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/RuneSwordHitQuery.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Dungeons/WardBreakableGlass.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Engine/OverlapResult.h"

bool UProductionToolComponent::ResolveBluntContact(float StunSeconds)
{
    auto* Pawn=Character.Get();if(!Pawn)return false;
    const FTransform Aim=Pawn->GetMeleeAimTransform();
    const FVector Forward=Aim.GetUnitAxis(EAxis::X).GetSafeNormal2D(UE_SMALL_NUMBER,Pawn->GetActorForwardVector());
    const TSet<TWeakObjectPtr<AActor>> Empty;
    const auto Hits=RuneSwordCombat::QuerySector(GetWorld(),Pawn,Pawn->GetActorLocation(),Forward,
        AxeCombatReach,BluntArcDegrees,Empty);
    bool Confirmed=false;
    for(const auto& Hit:Hits)
    {
        if(!ResolveAxeEnemyContact(Hit))continue;
        Confirmed=true;
        WarhammerCombat::ApplyHeavyStun(Hit.GetActor(),StunSeconds);
    }
    FProductionResource Resource;FHitResult Glass;FString Reason;
    TraceAxeContact(Resource,Glass,Reason);
    return UWardBreakableGlass::BreakHit(Glass,Forward)||Confirmed;
}

bool UProductionToolComponent::FindBluntGround(FHitResult& Hit) const
{
    auto* Pawn=Character.Get();auto* World=GetWorld();if(!Pawn||!World)return false;
    const FVector Forward=Pawn->GetMeleeAimTransform().GetUnitAxis(EAxis::X).GetSafeNormal2D(UE_SMALL_NUMBER,Pawn->GetActorForwardVector());
    const FVector Feet=Pawn->GetActorLocation()-FVector(0,0,Pawn->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
    // Keep the committed floor location while the view is pulled toward it.
    // The floor is still traced again at impact, so removed ground cannot emit a wave.
    const FVector Point=bBluntFloorTarget&&IsGroundSlamActive()?BluntFloorPoint:Feet+Forward*WarhammerHeavy::LandingForward;
    FCollisionQueryParams Q(SCENE_QUERY_STAT(WarhammerGround),false,Pawn);
    TArray<FOverlapResult> Bodies;
    World->OverlapMultiByObjectType(Bodies,Feet+Forward*50.f+FVector(0,0,70),FQuat::Identity,
        FCollisionObjectQueryParams::AllDynamicObjects,FCollisionShape::MakeBox(FVector(140,140,150)),Q);
    for(const auto& Body:Bodies)
        if(auto* Actor=Body.GetActor();Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>()))Q.AddIgnoredActor(Actor);
    // Physical floor probe: monsters never become a substitute for the floor.
    while(World->LineTraceSingleByChannel(Hit,Point+FVector(0,0,80),Point-FVector(0,0,65),ECC_Visibility,Q))
    {
        auto* Actor=Hit.GetActor();
        if(Actor&&(Actor->IsA<APawn>()||Actor->FindComponentByClass<UMonsterCombatComponent>())){Q.AddIgnoredActor(Actor);continue;}
        if(Hit.ImpactNormal.Z<.65f)return false;
        FHitResult Wall;
        if(World->LineTraceSingleByChannel(Wall,Feet+FVector(0,0,30),Hit.ImpactPoint+FVector(0,0,30),ECC_Visibility,Q))return false;
        return true;
    }
    return false;
}

bool UProductionToolComponent::BeginBluntShockwave(float StunSeconds)
{
    auto* Pawn=Character.Get();if(!Pawn||!Pawn->HasAuthority())return false;
    FHitResult Floor;if(!FindBluntGround(Floor))return ResolveBluntContact(StunSeconds);
    FActorSpawnParameters Params;Params.Owner=Pawn;Params.Instigator=Pawn;
    Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
    if(auto* Wave=GetWorld()->SpawnActor<AWarhammerShockwave>(AWarhammerShockwave::StaticClass(),
        Floor.ImpactPoint+Floor.ImpactNormal*2.f,FRotationMatrix::MakeFromZ(Floor.ImpactNormal).Rotator(),Params))
    {
        Wave->Setup(AxeStrike,BluntWaveRadius,StunSeconds);return true;
    }
    return false;
}
