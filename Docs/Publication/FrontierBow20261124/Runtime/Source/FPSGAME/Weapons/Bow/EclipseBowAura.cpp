#include "EclipseBowMark.h"

#include "Components/CapsuleComponent.h"
#include "Components/DecalComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInterface.h"
#include "TimerManager.h"

namespace
{
struct FFootprint
{
    FVector Feet;
    FVector2D Extent; // Actor-forward and actor-right half widths in world centimetres.
};

FFootprint BodyFootprint(const AActor& Target)
{
    if (const auto* Character = Cast<ACharacter>(&Target))
    {
        const UCapsuleComponent* Capsule = Character->GetCapsuleComponent();
        const float Radius = Capsule->GetScaledCapsuleRadius();
        FFootprint Body{Capsule->GetComponentLocation() - FVector::UpVector * Capsule->GetScaledCapsuleHalfHeight(),
            FVector2D(Radius, Radius)};

        // Keep elongated creatures' length. Reference bounds exclude pose swings and held equipment.
        const auto* Mesh = Character->GetMesh();
        if (Mesh && Mesh->IsVisible() && Mesh->GetSkeletalMeshAsset())
        {
            const FQuat Yaw = FRotator(0., Target.GetActorRotation().Yaw, 0.).Quaternion();
            const FTransform BodyFrame(Yaw.Inverse() * Mesh->GetComponentQuat(), FVector::ZeroVector, Mesh->GetComponentScale());
            const FVector HalfSize = Mesh->GetSkeletalMeshAsset()->GetBounds().GetBox().TransformBy(BodyFrame).GetExtent();
            Body.Extent.X = FMath::Max(Body.Extent.X, HalfSize.X);
            Body.Extent.Y = FMath::Max(Body.Extent.Y, HalfSize.Y);
        }
        return Body;
    }

    // Practice targets use a scene root, a colliding mesh, and a separate non-colliding DPS sign.
    const FBox Box = Target.CalculateComponentsBoundingBoxInLocalSpace(false);
    if (!Box.IsValid) return {Target.GetActorLocation(), FVector2D(15., 15.)};
    const FVector Size = Box.GetExtent() * Target.GetActorScale3D().GetAbs();
    const FBox WorldBox = Box.TransformBy(Target.GetActorTransform());
    FVector Feet = WorldBox.GetCenter();
    Feet.Z = WorldBox.Min.Z;
    return {Feet, FVector2D(Size.X, Size.Y)};
}

bool FindSupport(AActor& Target, const FVector& Feet, FVector& Center, FVector& Normal)
{
    if (const auto* Character = Cast<ACharacter>(&Target))
    {
        const auto* Move = Character->GetCharacterMovement();
        if (Move && Move->IsMovingOnGround() && Move->CurrentFloor.IsWalkableFloor())
        {
            const FHitResult& Floor = Move->CurrentFloor.HitResult;
            Normal = Floor.ImpactNormal;
            if (Normal.Z > .35 && Floor.GetComponent())
            {
                Center = Feet;
                Center.Z -= FVector::DotProduct(Feet - Floor.ImpactPoint, Normal) / Normal.Z;
                return true;
            }
        }
    }

    // Airborne creatures and props have no movement floor. Use the support directly below them.
    FCollisionObjectQueryParams Objects(ECC_WorldStatic);
    Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FHitResult Hit;
    if (!Target.GetWorld()->LineTraceSingleByObjectType(Hit, Feet + FVector::UpVector * 15.,
        Feet - FVector::UpVector * 5000., Objects, FCollisionQueryParams(SCENE_QUERY_STAT(EclipseAuraGround), false, &Target))
        || Hit.bStartPenetrating || Hit.ImpactNormal.Z <= .35) return false;
    Center = Hit.ImpactPoint;
    Normal = Hit.ImpactNormal;
    return true;
}
}

void UEclipseBowMark::StartGroundAura()
{
    if (GroundAura || GetNetMode() == NM_DedicatedServer || !AuraMaterial || !GetOwner()->GetRootComponent()) return;
    GroundAura = NewObject<UDecalComponent>(GetOwner());
    GroundAura->SetupAttachment(GetOwner()->GetRootComponent());
    // Inherit translation between floor samples; the projection uses world dimensions and surface normal.
    GroundAura->SetAbsolute(false, true, true);
    GroundAura->SetDecalMaterial(AuraMaterial);
    GroundAura->SetVisibility(false);
    GroundAura->RegisterComponent();
    GetWorld()->GetTimerManager().SetTimer(AuraPlacementTimer, this, &UEclipseBowMark::UpdateGroundAura, .10f, true);
    UpdateGroundAura();
}

void UEclipseBowMark::UpdateGroundAura()
{
    if (!GroundAura || !ActiveLayers()) { StopGroundAura(); return; }
    AActor& Target = *GetOwner();
    const FFootprint Body = BodyFootprint(Target);
    FVector Center, Normal;
    if (!FindSupport(Target, Body.Feet, Center, Normal))
    {
        GroundAura->SetVisibility(false);
        return;
    }

    // The main rim is at 84% of the decal radius. Give the feet clear space inside it.
    constexpr double RimUV = .84;
    const FVector2D Radius = (Body.Extent * 1.10 + FVector2D(4., 4.)) / RimUV;
    const double Depth = FMath::Clamp(Radius.GetMin() * .28, 9., 45.);
    const FVector Size(Depth, Radius.X, Radius.Y);
    if (!GroundAura->DecalSize.Equals(Size, .1))
    {
        GroundAura->DecalSize = Size;
        GroundAura->MarkRenderStateDirty();
    }
    const FVector Forward = FRotator(0., Target.GetActorRotation().Yaw, 0.).Vector();
    const FQuat Frame = FRotationMatrix::MakeFromXY(-Normal, Forward).ToQuat();
    GroundAura->SetWorldLocationAndRotation(Center, Frame);
    GroundAura->SetVisibility(true);
}

void UEclipseBowMark::StopGroundAura()
{
    if (auto* World = GetWorld()) World->GetTimerManager().ClearTimer(AuraPlacementTimer);
    if (IsValid(GroundAura)) GroundAura->DestroyComponent();
    GroundAura = nullptr;
}

void UEclipseBowMark::EndPlay(const EEndPlayReason::Type Reason)
{
    StopGroundAura();
    Super::EndPlay(Reason);
}
