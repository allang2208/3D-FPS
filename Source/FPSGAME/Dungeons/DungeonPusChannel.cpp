#include "DungeonPusChannel.h"
#include "AuthoredDungeonGenerator.h"
#include "../Monsters/FatZombiePusPool.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Skills/CorrosivePusDamage.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "DungeonPerformanceScope.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "Kismet/GameplayStatics.h"
#include "TimerManager.h"

ADungeonPusChannel::ADungeonPusChannel()
{
    PrimaryActorTick.bCanEverTick = false;
    Surface = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PusSurface"));
    SetRootComponent(Surface);
    Surface->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Surface->SetGenerateOverlapEvents(false);
    Surface->SetCanEverAffectNavigation(false);
    Surface->SetCastShadow(false);
    const FFatZombiePusSettings DeathResidue;
    DamagePerPulse = DeathResidue.Damage;
    DamageInterval = DeathResidue.Interval;
    SetCanBeDamaged(false);
    Tags.Add(TEXT("CorrosivePus"));
    Tags.Add(TEXT("DungeonPermanentHazard"));
}

void ADungeonPusChannel::BeginPlay()
{
    Super::BeginPlay();
    if (const auto* Dungeon=Cast<AAuthoredDungeonGenerator>(GetOwner()); Dungeon&&Dungeon->IsPreparationPending()) return;
    ActivateDamage();
}

void ADungeonPusChannel::ActivateDamage()
{
    if (HasAuthority()&&!GetWorldTimerManager().IsTimerActive(DamageTimer))
        GetWorldTimerManager().SetTimer(DamageTimer, this, &ThisClass::PulseDamage,
            FMath::Max(.1f, DamageInterval), true, FMath::Max(.1f, DamageInterval));
}

void ADungeonPusChannel::PulseDamage()
{
    if (!HasAuthority() || DamagePerPulse <= 0.f) return;
    if (const auto* Dungeon=Cast<AAuthoredDungeonGenerator>(GetOwner()); Dungeon&&Dungeon->IsPreparationPending()) return;
    TRACE_CPUPROFILER_EVENT_SCOPE(FPS_Dungeon_PusDamage);
    DungeonPerformance::FScope Scope(this, TEXT("Dungeon.PusDamage"));
    const FTransform Transform = GetActorTransform();
    const FVector Scale = GetActorScale3D().GetAbs();
    // Damage is player-only. Enumerating controllers avoids one physics broadphase query and
    // contact-array allocation per puddle, while retaining each zone's independent pulse clock.
    for (auto It=GetWorld()->GetPlayerControllerIterator(); It; ++It)
    {
        APlayerController* Controller=It->Get();
        APawn* Pawn=Controller?Controller->GetPawn():nullptr;
        if (!IsValid(Pawn) || !Pawn->GetActorEnableCollision()) continue;
        const UPrimitiveComponent* Body=Cast<UPrimitiveComponent>(Pawn->GetRootComponent());
        if (!Body || !Body->IsQueryCollisionEnabled() || Body->GetCollisionObjectType()!=ECC_Pawn) continue;
        if (!Pawn->IsPlayerControlled() || !Pawn->CanBeDamaged()) continue;
        if (const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>(); Health && Health->IsDead()) continue;
        const ACharacter* Character = Cast<ACharacter>(Pawn);
        // Match the death pool: grounded feet only. Walking over the bridge or jumping above it is safe.
        if (Character && !Character->GetCharacterMovement()->IsMovingOnGround()) continue;
        const FVector Feet = Transform.InverseTransformPosition(Pawn->GetActorLocation()-FVector(0,0,Pawn->GetSimpleCollisionHalfHeight()));
        if (FMath::Abs(Feet.Z)>GroundContactTolerance) continue;
        const float Radius = FMath::Max(4.f,Pawn->GetSimpleCollisionRadius()*.65f);
        if (ActorHasTag(TEXT("PusRadialFootprint")))
        {
            // Same polar outline as the generated puddle; Y is mirrored by FBX import.
            // HalfSize describes the wet core, leaving the transparent edge as a contact margin.
            const double RX = FMath::Max(1.,FMath::Abs(HalfSize.X));
            const double RY = FMath::Max(1.,FMath::Abs(HalfSize.Y));
            const double Angle = FMath::Atan2(-Feet.Y/RY,Feet.X/RX);
            const double Outline = 1.+.035*FMath::Sin(5.*Angle)+.022*FMath::Sin(9.*Angle+.4);
            const double X = Feet.X/(RX*Outline+Radius/FMath::Max(Scale.X,.001));
            const double Y = Feet.Y/(RY*Outline+Radius/FMath::Max(Scale.Y,.001));
            if (X*X+Y*Y>1.) continue;
        }
        else
        {
            const double DX = FMath::Max(0.,FMath::Abs(Feet.X)-FMath::Abs(HalfSize.X));
            const double DY = FMath::Max(0.,FMath::Abs(Feet.Y)-FMath::Abs(HalfSize.Y));
            if (FMath::Square(DX*Scale.X)+FMath::Square(DY*Scale.Y)>FMath::Square(Radius)) continue;
        }
        UGameplayStatics::ApplyDamage(Pawn,DamagePerPulse,nullptr,this,UCorrosivePusDamage::StaticClass());
    }
}

void ADungeonPusChannel::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DamageTimer);
    Super::EndPlay(Reason);
}
