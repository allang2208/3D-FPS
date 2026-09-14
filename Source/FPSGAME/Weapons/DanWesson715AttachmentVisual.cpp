#include "../FPSGAMECharacter.h"
#include "DanWesson715WeaponAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"

void AFPSGAMECharacter::SetDanWesson715Optic(const FString& Variant)
{
    const bool Enabled = bInventoryWeaponReady &&
        (Variant == TEXT("holographic") || Variant == TEXT("panoramic_red_dot"));
    if (!Enabled)
    {
        if (HolographicOptic) { HolographicOptic->DestroyComponent(); HolographicOptic = nullptr; }
        if (bHolographicOptic) bSightCalibrated = false;
        bHolographicOptic = false;
        OpticVariant.Reset();
        return;
    }
    if (!HolographicOptic || OpticVariant != Variant)
    {
        auto* OpticMesh = LoadObject<UStaticMesh>(nullptr, *DanWesson715WeaponAssets::AttachmentPath(Variant));
        if (!OpticMesh) { UE_LOG(LogTemp, Error, TEXT("DW715 missing optic %s"), *Variant); return; }
        if (!HolographicOptic)
        {
            HolographicOptic = NewObject<UStaticMeshComponent>(this, TEXT("DW715Optic"));
            // A revolver optic follows the fixed frame, independently of the cylinder.
            HolographicOptic->SetupAttachment(AKMViewmodel, TEXT("WPN_root"));
            HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            HolographicOptic->SetCastShadow(false);
            HolographicOptic->bReceivesDecals = false;
            HolographicOptic->RegisterComponent();
        }
        const auto& Ref = AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        auto Bone = [&Ref](const TCHAR* Name)
        {
            FTransform Result = FTransform::Identity;
            for (int32 I = Ref.FindBoneIndex(Name); I != INDEX_NONE; I = Ref.GetParentIndex(I))
                Result = Result * Ref.GetRefBonePose()[I];
            return Result;
        };
        const FTransform Root = Bone(TEXT("WPN_root"));
        const FVector Up = Root.GetRotation().GetAxisZ();
        const FVector Rear = Bone(TEXT("WPN_RearSight")).GetLocation();
        const FVector Forward = FVector::VectorPlaneProject(
            Bone(TEXT("WPN_FrontSight")).GetLocation() - Rear, Up).GetSafeNormal();
        // Source saddle: (0, -0.120, 0.0615) m in this gun's model frame.
        // The optic's imported +X points forward. Keep its body at authored size.
        const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat(),
            Rear + Forward * 11.25f - Up * .25f);
        HolographicMount = Mount.GetRelativeTransform(Root);
        HolographicOptic->EmptyOverrideMaterials();
        HolographicOptic->SetStaticMesh(OpticMesh);
        HolographicOptic->SetRelativeTransform(HolographicMount);
        bSightCalibrated = false;
    }
    bHolographicOptic = true;
    OpticVariant = Variant;
    HolographicOptic->SetVisibility(true);
}
