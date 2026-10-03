#include "G18WeaponAssets.h"
#include "../FPSGAMECharacter.h"
#include "M1911WeaponAssets.h"
#include "PitViper2011WeaponAssets.h"
#include "PitViper2011SICompensator.h"
#include "PistolAudioAssets.h"
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
        auto* AttachmentMesh = LoadObject<UStaticMesh>(nullptr, *(IsPitViperWeapon()?PitViper2011WeaponAssets::AttachmentPath(Variant):IsG18Weapon()?G18WeaponAssets::AttachmentPath(Variant):M1911WeaponAssets::AttachmentPath(Variant)));
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
    const bool PitViper = IsPitViperWeapon();
    const bool SI = PitViper && Variant == PitViper2011SICompensator::Part;
    const bool Enabled = bInventoryWeaponReady && (SI || Variant == TEXT("true") || Variant == TEXT("tactical_suppressor") || Variant == TEXT("brake"));
    if (!Enabled)
    {
        if (PitViper) PitViper2011SICompensator::ShowFactory(AKMViewmodel, true);
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
        const FString Part = SI ? FString(PitViper2011SICompensator::Part) : Variant == TEXT("tactical_suppressor") ? Variant : Suppressor ? TEXT("suppressor") : TEXT("brake");
        const FString MeshPath = SI ? FString(PitViper2011SICompensator::MeshPath)
            : PitViper ? PitViper2011WeaponAssets::AttachmentPath(Part)
            : IsG18Weapon() ? G18WeaponAssets::AttachmentPath(Part) : M1911WeaponAssets::AttachmentPath(Part);
        auto* AttachmentMesh = LoadObject<UStaticMesh>(nullptr, *MeshPath);
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
        const FVector Origin = PistolBone(Ref, TEXT("WPN_SOCKET_Muzzle")).GetLocation()
            + (PitViper ? Forward * (SI ? PitViper2011SICompensator::MountOffsetCM : 0.f)
                : Up * (IsG18Weapon()?0.f:.598f) + Forward * (ExtensionCM - .012535f));
        // FBX imports the can's author +Y as UE -Y. Use its actual bore axis;
        // the old +Y mount turned the body back through the slide.
        const FQuat SourceFrame = PitViper ? FQuat::Identity : FRotationMatrix::MakeFromXZ(-FVector::RightVector, FVector::UpVector).ToQuat();
        const FTransform Mount(FRotationMatrix::MakeFromXZ(Forward, Up).ToQuat() * SourceFrame.Inverse(), Origin);
        MuzzleAttachment->SetRelativeTransform(Mount.GetRelativeTransform(PistolBone(Ref, TEXT("WPN_Barrel"))));
        MuzzleLocalAxis = PitViper ? FVector::ForwardVector : -FVector::RightVector;
        MuzzleLocalTip = FVector(0.f, -(Suppressor ? M1911WeaponAssets::SuppressorTipCM : M1911WeaponAssets::BrakeTipCM), 0.f);
        if((PitViper || IsG18Weapon()) && MuzzleAttachment->DoesSocketExist(TEXT("Muzzle")))
            MuzzleLocalTip=MuzzleAttachment->GetSocketTransform(TEXT("Muzzle"),RTS_Component).GetLocation();
        if (SI && MuzzleAttachment->DoesSocketExist(TEXT("AimGuide")))
            MuzzleLocalAxis = (MuzzleAttachment->GetSocketTransform(TEXT("AimGuide"), RTS_Component).GetLocation() - MuzzleLocalTip).GetSafeNormal();
        // The cached cue can belong to a previously equipped weapon. Bind the
        // current pistol's cue when mounting, including the off-hand source rig.
        if (Suppressor)
            SuppressedFireSound = LoadObject<USoundBase>(nullptr, PistolAudioAssets::Suppressed);
    }
    MuzzleVariant = Variant;
    MuzzleAttachment->SetVisibility(true);
    if (PitViper) PitViper2011SICompensator::ShowFactory(AKMViewmodel, !SI);
}
