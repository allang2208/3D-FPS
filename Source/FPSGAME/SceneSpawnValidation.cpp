#include "SceneSpawnValidation.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/StaticMesh.h"
#include "Components/StaticMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerStart.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/PlatformMisc.h"
#include "TimerManager.h"
#include "GameFramework/PlayerController.h"
#include "Components/CapsuleComponent.h"

bool USceneSpawnValidation::FindSafeSpawn(UObject* WorldContextObject, FVector NearLocation, FVector& SafeLocation)
{
    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(SceneSafeSpawn), false);
    for (TActorIterator<APlayerStart> It(World); It; ++It) Query.AddIgnoredActor(*It);
    // Original FPS character capsule: radius 42 cm, half height 96 cm.
    const FCollisionShape Capsule = FCollisionShape::MakeCapsule(44.f, 98.f);
    for (int32 Ring = 0; Ring <= 4; ++Ring)
    {
        const int32 Samples = Ring ? 8 : 1;
        for (int32 Sample = 0; Sample < Samples; ++Sample)
        {
            const float Angle = Sample * 2.f * PI / Samples;
            const FVector Probe = NearLocation + FVector(FMath::Cos(Angle), FMath::Sin(Angle), 0) * (Ring * 100.f);
            FHitResult Hit;
            if (!World->LineTraceSingleByChannel(Hit, Probe + FVector(0,0,500), Probe - FVector(0,0,2000), ECC_Pawn, Query)) continue;
            if (Hit.bStartPenetrating || Hit.ImpactNormal.Z < .71f) continue;
            const FVector Candidate = Hit.ImpactPoint + FVector(0,0,102);
            if (World->OverlapBlockingTestByChannel(Candidate, FQuat::Identity, ECC_Pawn, Capsule, Query)) continue;
            SafeLocation = Candidate;
            UE_LOG(LogTemp, Display, TEXT("SceneSpawn: Validated %s on %s"), *SafeLocation.ToString(), *GetNameSafe(Hit.GetActor()));
            return true;
        }
    }
    UE_LOG(LogTemp, Error, TEXT("SceneSpawn: No safe capsule location near %s"), *NearLocation.ToString());
    return false;
}

bool USceneSpawnValidation::InternalizeTestActors(UObject* WorldContextObject)
{
#if WITH_EDITOR
    UWorld* World = GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull);
    if (!World || World->IsGameWorld() || World->GetWorldPartition() ||
        !World->GetOutermost()->GetName().StartsWith(TEXT("/Game/GameMaps/L_MilitaryTrench_FPS_Test"))) return false;
    // Landscape Nanite generated meshes are private objects in external actor
    // packages. Carry these owned objects into the map along with their actors.
    const FString ExternalPrefix = TEXT("/Game/__ExternalActors__/GameMaps/L_MilitaryTrench_FPS_Test/");
    for (AActor* Actor : World->PersistentLevel->Actors)
    {
        if (!Actor) continue;
        TInlineComponentArray<UStaticMeshComponent*> Components(Actor);
        for (UStaticMeshComponent* Component : Components)
        {
            UStaticMesh* Mesh = Component->GetStaticMesh();
            if (Mesh && Mesh->GetOutermost()->GetName().StartsWith(ExternalPrefix))
                Mesh->Rename(*MakeUniqueObjectName(World->PersistentLevel, Mesh->GetClass(), Mesh->GetFName()).ToString(),
                    World->PersistentLevel, REN_DontCreateRedirectors | REN_NonTransactional);
        }
    }
    World->PersistentLevel->ConvertAllActorsToPackaging(false);
    World->PersistentLevel->SetUseExternalActors(false);
    World->MarkPackageDirty();
    return true;
#else
    return false;
#endif
}

void USceneSpawnAuditSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if (World.IsGameWorld() && FParse::Param(FCommandLine::Get(), TEXT("SceneSpawnAudit")))
        World.GetTimerManager().SetTimer(AuditTimer, this, &USceneSpawnAuditSubsystem::CheckLanding,
            FParse::Param(FCommandLine::Get(), TEXT("SceneMovementAudit")) ? .05f : 1.f, true, 3.f);
}

void USceneSpawnAuditSubsystem::CheckLanding()
{
    if (Samples == 0)
    {
        for (TActorIterator<APlayerStart> It(GetWorld()); It; ++It)
        {
            FVector Safe;
            const bool Valid = USceneSpawnValidation::FindSafeSpawn(this, It->GetActorLocation(), Safe);
            UE_LOG(LogTemp, Display, TEXT("SCENE_START_RUNTIME %s position=%s safe=%d candidate=%s"),
                *It->GetName(), *It->GetActorLocation().ToString(), Valid, *Safe.ToString());
        }
    }
    ACharacter* Character = UGameplayStatics::GetPlayerCharacter(this, 0);
    const bool Grounded = Character && Character->GetCharacterMovement()->IsMovingOnGround();
    if (FParse::Param(FCommandLine::Get(), TEXT("SceneMovementAudit")))
    {
        ++Samples;
        if (!Character)
        {
            UE_LOG(LogTemp, Error, TEXT("SCENE_MOVEMENT_FAIL no pawn"));
            FPlatformMisc::RequestExitWithStatus(false, 1);
            return;
        }
        UCharacterMovementComponent* Movement = Character->GetCharacterMovement();
        if (Samples == 1) InitialPosition = Character->GetActorLocation();
        if (Samples == 20)
        {
            UE_LOG(LogTemp, Display, TEXT("AUDIT_MOVE_STATE active=%d tick=%d cantick=%d canjump=%d ignored=%d mode=%d"),
                Movement->IsActive(), Movement->IsComponentTickEnabled(), Character->IsActorTickEnabled(),
                Character->CanJump(), Character->IsMoveInputIgnored(), int32(Movement->MovementMode));
            Character->Jump();
            FCollisionQueryParams Query(SCENE_QUERY_STAT(SceneMovementBlocker), false, Character);
            for (const FVector Direction : {FVector::UpVector, Character->GetActorForwardVector()})
            {
                FHitResult Hit;
                GetWorld()->SweepSingleByChannel(Hit, Character->GetActorLocation(), Character->GetActorLocation() + Direction * 100,
                    FQuat::Identity, Character->GetCapsuleComponent()->GetCollisionObjectType(),
                    Character->GetCapsuleComponent()->GetCollisionShape(), Query);
                UE_LOG(LogTemp, Display, TEXT("AUDIT_BLOCKER direction=%s actor=%s component=%s penetration=%d type=%d"),
                    *Direction.ToString(), *GetNameSafe(Hit.GetActor()), *GetNameSafe(Hit.GetComponent()), Hit.bStartPenetrating,
                    int32(Character->GetCapsuleComponent()->GetCollisionObjectType()));
            }
        }
        if (Samples == 24) Character->StopJumping();
        if (!Grounded && Movement->Velocity.Z > 20) SawRising = true;
        if (!Grounded && Movement->Velocity.Z < -20) SawFalling = true;
        if (Samples >= 70 && Samples < 110) Character->AddMovementInput(Character->GetActorForwardVector(), 1.f);
        if (Samples % 20 == 0 || Samples == 1)
        {
            const UStaticMeshComponent* SupportMesh = Cast<UStaticMeshComponent>(Movement->CurrentFloor.HitResult.GetComponent());
            FHitResult Surface;
            FCollisionQueryParams SurfaceQuery(SCENE_QUERY_STAT(SceneVisibleFloor), true, Character);
            GetWorld()->LineTraceSingleByChannel(Surface, Character->GetActorLocation(), Character->GetActorLocation() - FVector(0,0,2000), ECC_Pawn, SurfaceQuery);
            UE_LOG(LogTemp, Display, TEXT("AUDIT_SUPPORT mesh=%s complex_ground_z=%.2f feet_z=%.2f"),
                SupportMesh ? *GetPathNameSafe(SupportMesh->GetStaticMesh()) : TEXT("terrain"), Surface.ImpactPoint.Z,
                Character->GetActorLocation().Z - Character->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            UE_LOG(LogTemp, Display, TEXT("SCENE_MOVEMENT_SAMPLE n=%d ground=%d zspeed=%.2f gravity=%.2f support=%s pos=%s"),
                Samples, Grounded, Movement->Velocity.Z, Movement->GetGravityZ(),
                *GetNameSafe(Movement->CurrentFloor.HitResult.GetActor()), *Character->GetActorLocation().ToString());
        }
        if (Samples >= 160)
        {
            const float Travel = FVector::Dist2D(InitialPosition, Character->GetActorLocation());
            const bool BadSupport = GetNameSafe(Movement->CurrentFloor.HitResult.GetActor()).Contains(TEXT("1776864923"));
            const bool Passed = Grounded && SawRising && SawFalling && Travel > 30 && !BadSupport && Movement->GetGravityZ() < 0;
            UE_LOG(LogTemp, Display, TEXT("SCENE_MOVEMENT_%s rise=%d fall=%d ground=%d moved=%.1f bad_support=%d"),
                Passed ? TEXT("PASS") : TEXT("FAIL"), SawRising, SawFalling, Grounded, Travel, BadSupport);
            FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
        }
        return;
    }
    if (Grounded) ++GroundedSamples;
    ++Samples;
    UE_LOG(LogTemp, Display, TEXT("SCENE_LANDING_SAMPLE map=%s grounded=%d position=%s"),
        *UGameplayStatics::GetCurrentLevelName(this, true), Grounded,
        Character ? *Character->GetActorLocation().ToString() : TEXT("NO_PAWN"));
    if (Samples >= 10)
    {
        const bool Passed = GroundedSamples == 10;
        UE_LOG(LogTemp, Display, TEXT("SCENE_LANDING_%s grounded=%d/10"), Passed ? TEXT("PASS") : TEXT("FAIL"), GroundedSamples);
        FPlatformMisc::RequestExitWithStatus(false, Passed ? 0 : 1);
    }
}

void USceneSpawnAuditSubsystem::Deinitialize()
{
    if (GetWorld()) GetWorld()->GetTimerManager().ClearTimer(AuditTimer);
    Super::Deinitialize();
}
