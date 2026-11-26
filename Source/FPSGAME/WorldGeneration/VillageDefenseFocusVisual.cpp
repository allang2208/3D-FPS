#include "VillageDefenseFocusVisual.h"
#include "VillageDefenseSection.h"
#include "HighVillageDefense.h"
#include "../FPSGAMECharacter.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "GameFramework/PlayerController.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace
{
    const FSoftObjectPath ResidentOutline(TEXT("/Game/Characters/ResidentInteraction/M_ResidentFocusOutline.M_ResidentFocusOutline"));
    // A depth-tested 22% translucent surface. Adjacent intact bays occlude the preview.
    const FSoftObjectPath AssemblyGhost(TEXT("/Game/Building/GunWorkbench20260927/Assembly/M_AssemblyGhost.M_AssemblyGhost"));
    constexpr int32 DefenseStencil = 192; // immediately after the resident slots 176..191

    void RemoveParts(TArray<TObjectPtr<UStaticMeshComponent>>& Parts)
    {
        for (auto& Part : Parts)
            if (IsValid(Part)) Part->DestroyComponent();
        Parts.Reset();
    }
}

void UVillageDefenseFocusVisual::BeginPlay()
{
    Super::BeginPlay();
    if (auto* Pawn = Cast<APawn>(GetOwner()))
        Pawn->ReceiveControllerChangedDelegate.AddDynamic(this, &ThisClass::PossessionChanged);
}

void UVillageDefenseFocusVisual::PossessionChanged(APawn*, AController*, AController*)
{
    SetFocus(nullptr, nullptr);
}

void UVillageDefenseFocusVisual::SetFocus(AVillageDefenseSection* Aimed, AVillageDefenseSection* NearbyDestroyed)
{
    const auto* Character = Cast<AFPSGAMECharacter>(GetOwner());
    const auto* PC = Character ? Cast<APlayerController>(Character->GetController()) : nullptr;
    auto* Camera = PC && PC->GetLocalPlayer() ? Character->FirstPersonCamera.Get() : nullptr;
    if (!Camera || !IsValid(Aimed) || Aimed->GetWorld() != GetWorld()) Aimed = nullptr;
    if (!Camera || !IsValid(NearbyDestroyed) || NearbyDestroyed->GetWorld() != GetWorld()
        || NearbyDestroyed->GetHealth() > 0.f) NearbyDestroyed = nullptr;

    const bool bClosed = Aimed && Aimed->GetHealth() <= 0.f;
    if (FocusedSection.Get() != Aimed || bFocusedClosed != bClosed || (!Aimed && !DepthParts.IsEmpty()))
        RemoveParts(DepthParts);
    if (PreviewSection.Get() != NearbyDestroyed || (!NearbyDestroyed && !GhostParts.IsEmpty()))
        RemoveParts(GhostParts);
    FocusedSection = Aimed;
    PreviewSection = NearbyDestroyed;
    bFocusedClosed = bClosed;

    if ((Aimed || NearbyDestroyed) && !Load)
    {
        Load = UAssetManager::GetStreamableManager().RequestAsyncLoad(
            TArray<FSoftObjectPath>{ResidentOutline, AssemblyGhost},
            FStreamableDelegate::CreateUObject(this, &ThisClass::MaterialsReady));
    }
    UCameraComponent* DesiredCamera = Aimed && Outline ? Camera : nullptr;
    if (BoundCamera.Get() != DesiredCamera)
    {
        if (BoundCamera.IsValid() && Outline) BoundCamera->RemoveBlendable(Outline);
        BoundCamera = DesiredCamera;
        if (DesiredCamera) DesiredCamera->AddOrUpdateBlendable(Outline, 1.f);
    }
    if (Aimed && Outline && DepthParts.IsEmpty()) BuildParts(Aimed, false, bClosed);
    if (NearbyDestroyed && Ghost && GhostParts.IsEmpty()) BuildParts(NearbyDestroyed, true, true);
}

void UVillageDefenseFocusVisual::MaterialsReady()
{
    if (auto* Base = Cast<UMaterialInterface>(ResidentOutline.ResolveObject()))
    {
        Outline = UMaterialInstanceDynamic::Create(Base, this);
        Outline->SetScalarParameterValue(TEXT("ResidentStencil"), DefenseStencil);
    }
    if (auto* Base = Cast<UMaterialInterface>(AssemblyGhost.ResolveObject()))
    {
        Ghost = UMaterialInstanceDynamic::Create(Base, this);
        Ghost->SetVectorParameterValue(TEXT("Tint"), FLinearColor(.06f, 1.f, .15f));
    }
    SetFocus(FocusedSection.Get(), PreviewSection.Get());
}

void UVillageDefenseFocusVisual::BuildParts(AVillageDefenseSection* Section, bool bGhost, bool bClosed)
{
    // The two mounts survive collapse and remain visible. Only the wall itself
    // or the two missing leaves need replacement. Their native origins are the hinges.
    TArray<UStaticMeshComponent*, TInlineAllocator<2>> Sources;
    Sources.Add(Section->GetMasonry());
    if (const auto* Gate=Cast<AVillageDefenseGate>(Section))
        Sources.Add(Gate->GetRightLeaf());
    if (!bClosed)
        if (const auto* LiftGate=Cast<AHighVillageGate>(Section))
            Sources.Add(LiftGate->GetStonePortal());
    for (auto* Source : Sources)
        if (!Source || !Source->GetStaticMesh()) return; // streamed setup may span several frames

    auto& Parts = bGhost ? GhostParts : DepthParts;
    for (auto* Source : Sources)
    {
        auto* Proxy = NewObject<UStaticMeshComponent>(GetOwner(), NAME_None, RF_Transient);
        Proxy->SetMobility(EComponentMobility::Movable);
        Proxy->SetOnlyOwnerSee(true);
        Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Proxy->SetGenerateOverlapEvents(false);
        Proxy->SetCanEverAffectNavigation(false);
        Proxy->SetCastShadow(false);
        Proxy->SetReceivesDecals(false);
        Proxy->SetVisibleInRayTracing(false);
        Proxy->SetHiddenInSceneCapture(true);
        Proxy->bAffectDistanceFieldLighting = false;
        Proxy->bVisibleInReflectionCaptures = false;
        Proxy->bVisibleInRealTimeSkyCaptures = false;
        Proxy->SetRenderInMainPass(bGhost);
        Proxy->SetRenderInDepthPass(false);
        Proxy->SetRenderCustomDepth(!bGhost);
        if (!bGhost) Proxy->SetCustomDepthStencilValue(DefenseStencil);
        else Proxy->SetForceDisableNanite(true); // translucent material requires fallback geometry

        if (bClosed)
        {
            FTransform Relative = Source->GetRelativeTransform();
            if (Section->IsA<AVillageDefenseGate>()) Relative.SetRotation(FQuat::Identity);
            Proxy->SetupAttachment(Section->GetRootComponent());
            Proxy->SetRelativeTransform(Relative);
        }
        else
        {
            Proxy->SetupAttachment(Source); // follows a swinging leaf between focus updates
        }
        Proxy->SetStaticMesh(Source->GetStaticMesh());
        UMaterialInterface* Surface = bGhost ? static_cast<UMaterialInterface*>(Ghost.Get())
                                             : UMaterial::GetDefaultMaterial(MD_Surface);
        for (int32 Slot = 0; Slot < Proxy->GetNumMaterials(); ++Slot)
            Proxy->SetMaterial(Slot, Surface);
        Proxy->RegisterComponent();
        Parts.Add(Proxy);
    }
}

void UVillageDefenseFocusVisual::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Load) Load->CancelHandle();
    if (auto* Pawn = Cast<APawn>(GetOwner()))
        Pawn->ReceiveControllerChangedDelegate.RemoveDynamic(this, &ThisClass::PossessionChanged);
    SetFocus(nullptr, nullptr);
    Super::EndPlay(Reason);
}
