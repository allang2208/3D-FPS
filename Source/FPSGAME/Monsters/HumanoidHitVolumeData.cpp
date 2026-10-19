#include "HumanoidHitVolumeData.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Character.h"
#include "PhysicsEngine/PhysicsAsset.h"

namespace
{
const UHumanoidHitVolumeData* HitVolumeData(const FHitResult& Hit, USkeletalMeshComponent*& Mesh)
{
    Mesh = Cast<USkeletalMeshComponent>(Hit.GetComponent());
    if (!Mesh) if (const auto* Character = Cast<ACharacter>(Hit.GetActor())) Mesh = Character->GetMesh();
    auto* Physics = Mesh ? Mesh->GetPhysicsAsset() : nullptr;
    return Physics ? Cast<UHumanoidHitVolumeData>(Physics->GetAssetUserDataOfClass(UHumanoidHitVolumeData::StaticClass())) : nullptr;
}
}

bool UHumanoidHitVolumeData::ResolveCriticalHit(const FHitResult& Hit, bool& bCritical)
{
    USkeletalMeshComponent* Mesh = nullptr;
    const auto* Data = HitVolumeData(Hit, Mesh);
    if (!Data) return false;
    bCritical = false;
    if (Hit.BoneName != Data->HeadBone) return true;
    // Network reports have no component. Their bone designation is normalized
    // against the shooter's contact pose before serialization. Preserve that
    // result instead of testing a quantized point against a later server pose.
    if (!Hit.GetComponent()) { bCritical = true; return true; }
    const FTransform HeadTransform = Mesh->GetSocketTransform(Data->HeadBone);
    const FVector Point = HeadTransform.InverseTransformPosition(Hit.ImpactPoint);
    const double Tolerance = .05 / FMath::Max(double(UE_KINDA_SMALL_NUMBER), HeadTransform.GetScale3D().GetAbsMin());
    for (const auto& Hull : Data->HeadHulls)
    {
        if (!Hull.Bounds.ExpandBy(Tolerance).IsInsideOrOn(Point)) continue;
        bool Inside = true;
        for (const FPlane& Plane : Hull.Planes) if (Plane.PlaneDot(Point) > Tolerance) { Inside = false; break; }
        if (Inside) { bCritical = true; break; }
    }
    return true;
}

FName UHumanoidHitVolumeData::NetworkBoneName(const FHitResult& Hit)
{
    USkeletalMeshComponent* Mesh = nullptr;
    const auto* Data = HitVolumeData(Hit, Mesh);
    if (Data && Hit.BoneName == Data->HeadBone)
    {
        bool bCritical = false;
        ResolveCriticalHit(Hit, bCritical);
        if (!bCritical) return NAME_None;
    }
    return Hit.BoneName;
}
