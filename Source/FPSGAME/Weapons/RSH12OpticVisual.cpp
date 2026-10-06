#include "../FPSGAMECharacter.h"
#include "RSH12OpticAssets.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

void AFPSGAMECharacter::SetRSH12Optic(const FString& InputVariant)
{
    const FString Variant = RSH12OpticAssets::Upgrade(InputVariant);
    const bool Enabled = bInventoryWeaponReady && RSH12OpticAssets::Supports(Variant);
    auto Remove = [](TObjectPtr<UStaticMeshComponent>& Component)
    {
        if (Component) { Component->DestroyComponent(); Component = nullptr; }
    };
    if (!Enabled)
    {
        Remove(LPVORing);
        Remove(HolographicOptic);
        Remove(AKMOpticBridge);
        if (bHolographicOptic) bSightCalibrated = false;
        bHolographicOptic = false;
        OpticVariant.Reset();
        return;
    }
    if (!AKMViewmodel || !AKMViewmodel->GetSkeletalMeshAsset()) return;
    if (bHolographicOptic && OpticVariant == Variant && HolographicOptic && AKMOpticBridge)
    {
        HolographicOptic->SetVisibility(true);
        AKMOpticBridge->SetVisibility(true);
        if (LPVORing) LPVORing->SetVisibility(Variant == TEXT("lpvo_1_6x"));
        return;
    }
    const bool IsLPVO = Variant == TEXT("lpvo_1_6x");
    auto* OpticMesh = LoadObject<UStaticMesh>(nullptr, *RSH12OpticAssets::MeshPath(Variant));
    auto* RailMesh = LoadObject<UStaticMesh>(nullptr, *RSH12OpticAssets::RailPath(Variant));
    auto* RingMesh = IsLPVO ? LoadObject<UStaticMesh>(nullptr, *RSH12OpticAssets::MeshPath(TEXT("lpvo_ring"))) : nullptr;
    if (!OpticMesh || !RailMesh || (IsLPVO && !RingMesh))
    {
        UE_LOG(LogTemp, Error, TEXT("RSH12 missing fitted optic assembly %s"), *Variant);
        return;
    }
    auto Configure = [&](TObjectPtr<UStaticMeshComponent>& Component, UStaticMesh* AttachmentMesh,
                         USceneComponent* Parent, FName Socket, const FTransform& Local)
    {
        if (!Component) Component = NewObject<UStaticMeshComponent>(this);
        Component->EmptyOverrideMaterials();
        Component->SetStaticMesh(AttachmentMesh);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCastShadow(false);
        Component->bReceivesDecals = false;
        Component->SetOnlyOwnerSee(AKMViewmodel->bOnlyOwnerSee);
        Component->SetFirstPersonPrimitiveType(AKMViewmodel->FirstPersonPrimitiveType);
        if (!Component->IsRegistered())
        {
            Component->SetupAttachment(Parent, Socket);
            Component->RegisterComponent();
        }
        else Component->AttachToComponent(Parent, FAttachmentTransformRules::KeepRelativeTransform, Socket);
        Component->SetRelativeTransform(Local);
        Component->SetVisibility(true);
    };
    // Both pieces follow the fixed receiver. The animated cylinder remains independent.
    Configure(AKMOpticBridge, RailMesh, AKMViewmodel, TEXT("WPN_root"), RSH12OpticAssets::RailMount());
    HolographicMount = RSH12OpticAssets::OpticMount(Variant);
    Configure(HolographicOptic, OpticMesh, AKMViewmodel, TEXT("WPN_root"), HolographicMount);
    if (OpticVariant != Variant) LPVOMagnification = DisplayedLPVOMagnification = 1.f;
    if (IsLPVO)
        Configure(LPVORing, RingMesh, HolographicOptic, TEXT("ZoomRing"),
            FTransform(FRotator(0.f, 0.f, (DisplayedLPVOMagnification - 1.f) * 24.f)));
    else Remove(LPVORing);
    OpticVariant = Variant;
    bHolographicOptic = true;
    bSightCalibrated = false;
}
