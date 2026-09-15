#include "../FPSGAMECharacter.h"
#include "M1911WeaponAssets.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Sound/SoundBase.h"

namespace
{
    FTransform PistolBone(const FReferenceSkeleton& Ref, const TCHAR* Name)
    {
        FTransform Result = FTransform::Identity;
        for (int32 I = Ref.FindBoneIndex(Name); I != INDEX_NONE; I = Ref.GetParentIndex(I))
            Result = Result * Ref.GetRefBonePose()[I];
        return Result;
    }
    void PistolFrame(const FReferenceSkeleton& Ref, FVector& Forward, FVector& Up)
    {
        Up = PistolBone(Ref, TEXT("WPN_root")).GetRotation().GetAxisZ();
        const FVector SightAxis = PistolBone(Ref, TEXT("WPN_FrontSight")).GetLocation()
            - PistolBone(Ref, TEXT("WPN_RearSight")).GetLocation();
        Forward = FVector::VectorPlaneProject(SightAxis, Up).GetSafeNormal();
    }
}

void AFPSGAMECharacter::SetM1911Optic(const FString& Variant)
{
    const bool Enabled = bInventoryWeaponReady && (Variant == TEXT("holographic") || Variant == TEXT("panoramic_red_dot"));
    if (Enabled && (!HolographicOptic || OpticVariant != Variant))
    {
        auto* AttachmentMesh = LoadObject<UStaticMesh>(nullptr, *M1911WeaponAssets::AttachmentPath(Variant));
        if (!AttachmentMesh) { UE_LOG(LogTemp, Error, TEXT("M1911 missing optic %s"), *Variant); return; }
        if (!HolographicOptic)
        {
            HolographicOptic = NewObject<UStaticMeshComponent>(this, TEXT("M1911Optic"));
            HolographicOptic->SetupAttachment(AKMViewmodel, TEXT("WPN_Slide"));
            HolographicOptic->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            HolographicOptic->SetCastShadow(false);
            HolographicOptic->bReceivesDecals = false;
            HolographicOptic->RegisterComponent();
        }
        const auto& Ref = AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        FVector Forward, Up; PistolFrame(Ref, Forward, Up);
        // Compact optics sit lower on a contoured two-foot saddle. The relief
        // leaves the original rear sight intact and clears the chamber opening.
        const FVector Origin = PistolBone(Ref, TEXT("WPN_RearSight")).GetLocation() + Forward * 1.6f + Up * .45f;
        const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat(), Origin);
        HolographicMount = Mount.GetRelativeTransform(PistolBone(Ref, TEXT("WPN_Slide")));
        // Wet MIDs and their slot indices belong to the previous optic mesh.
        HolographicOptic->EmptyOverrideMaterials();
        HolographicOptic->SetStaticMesh(AttachmentMesh);
        HolographicOptic->SetRelativeTransform(HolographicMount);
    }
    if (bHolographicOptic != Enabled || OpticVariant != Variant) bSightCalibrated = false;
    bHolographicOptic = Enabled;
    OpticVariant = Enabled ? Variant : FString();
    if (HolographicOptic) HolographicOptic->SetVisibility(Enabled);
}

void AFPSGAMECharacter::SetM1911Muzzle(const FString& Variant)
{
    const bool Enabled = bInventoryWeaponReady && (Variant == TEXT("true") || Variant == TEXT("tactical_suppressor") || Variant == TEXT("brake"));
    if (!Enabled)
    {
        // Profile refresh propagates weapon visibility to children. An unequipped
        // muzzle must cease to be a child, otherwise that refresh resurrects it.
        if (MuzzleAttachment)
        {
            MuzzleAttachment->SetVisibility(false, true);
            MuzzleAttachment->DestroyComponent();
            MuzzleAttachment = nullptr;
        }
        MuzzleVariant.Reset();
        MuzzleLocalTip = FVector::ZeroVector;
        MuzzleLocalAxis = FVector::ZeroVector;
        return;
    }
    if (!MuzzleAttachment || MuzzleVariant != Variant)
    {
        const bool Suppressor = Variant == TEXT("true") || Variant == TEXT("tactical_suppressor");
        const FString Part = Variant == TEXT("tactical_suppressor") ? Variant : Suppressor ? TEXT("suppressor") : TEXT("brake");
        auto* AttachmentMesh = LoadObject<UStaticMesh>(nullptr, *M1911WeaponAssets::AttachmentPath(Part));
        if (!AttachmentMesh) { UE_LOG(LogTemp, Error, TEXT("M1911 missing muzzle %s"), *Part); return; }
        if (!MuzzleAttachment)
        {
            MuzzleAttachment = NewObject<UStaticMeshComponent>(this, TEXT("M1911MuzzleAttachment"));
            MuzzleAttachment->SetupAttachment(AKMViewmodel, TEXT("WPN_Barrel"));
            MuzzleAttachment->SetCollisionEnabled(ECollisionEnabled::NoCollision);
            MuzzleAttachment->SetCastShadow(false);
            MuzzleAttachment->bReceivesDecals = false;
            MuzzleAttachment->RegisterComponent();
        }
        MuzzleAttachment->EmptyOverrideMaterials();
        MuzzleAttachment->SetStaticMesh(AttachmentMesh);
        const auto& Ref = AKMViewmodel->GetSkeletalMeshAsset()->GetRefSkeleton();
        FVector Forward, Up; PistolFrame(Ref, Forward, Up);
        // The refined barrel bore is 0.598 cm above the legacy muzzle marker.
        // Each muzzle has its own fitted rear collar; both retain an open bore.
        const float ExtensionCM = Suppressor ? 1.2f : .6f;
        const FVector Origin = PistolBone(Ref, TEXT("WPN_SOCKET_Muzzle")).GetLocation() + Up * .598f + Forward * (ExtensionCM - .012535f);
        // FBX imports the can's author +Y as UE -Y. Use its actual bore axis;
        // the old +Y mount turned the body back through the slide.
        const FQuat SourceFrame = FRotationMatrix::MakeFromXZ(-FVector::RightVector, FVector::UpVector).ToQuat();
        const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat() * SourceFrame.Inverse(), Origin);
        MuzzleAttachment->SetRelativeTransform(Mount.GetRelativeTransform(PistolBone(Ref, TEXT("WPN_Barrel"))));
        MuzzleLocalAxis = -FVector::RightVector;
        MuzzleLocalTip = FVector(0.f, -(Suppressor ? M1911WeaponAssets::SuppressorTipCM : M1911WeaponAssets::BrakeTipCM), 0.f);
        if (Suppressor && !SuppressedFireSound)
            SuppressedFireSound = LoadObject<USoundBase>(nullptr, TEXT("/Game/Weapons/M4MuzzlesV1/S_M4_Suppressed"));
    }
    MuzzleVariant = Variant;
    MuzzleAttachment->SetVisibility(true);
}
