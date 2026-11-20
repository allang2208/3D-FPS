#include "ResidentHighlightSubsystem.h"
#include "ColdSteelWorldInteraction.h"
#include "../FPSGAMECharacter.h"
#include "../NPC/ChapelNun.h"
#include "../NPC/VillageArtisanMerchant.h"
#include "../NPC/VillageBaker.h"
#include "../NPC/VillageHerbalist.h"
#include "../NPC/VillageTavernKeeper.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "../WorldGeneration/HillsCarpenterWorkshop.h"
#include "../WorldGeneration/HillsHerbalistWorkshop.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/LocalPlayer.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GroomComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "TimerManager.h"

namespace
{
    const FSoftObjectPath OutlinePath(TEXT("/Game/Characters/ResidentInteraction/M_ResidentFocusOutline.M_ResidentFocusOutline"));
    const FName StencilParameter(TEXT("ResidentStencil"));
    // One slot per distinct resident selected by the local cameras in this world.
    constexpr int32 FirstResidentStencil = 176;
    constexpr int32 ResidentStencilCount = 16;
    const FName ShopMaskParameter(TEXT("VisibleResidentSlots"));
    constexpr int32 FirstOtherFocusStencil = 144;
    const FSoftObjectPath ShopMaterialPath(TEXT("/Game/Characters/ResidentInteraction/M_ResidentShopHighlightResponse.M_ResidentShopHighlightResponse"));

    template<class TShop>
    bool AtShop(const TShop& Shop, const AActor& Resident, FVector Eye)
    {
        // These are the authored repair footprint and station transform, also available
        // when a client first sees a guard returning from a fight.
        const FBox Bounds = FBox::BuildAABB(Shop.RepairAreaCenter, Shop.RepairAreaHalfExtent);
        const FTransform& Frame = Shop.GetActorTransform();
        return Bounds.IsInsideOrOn(Frame.InverseTransformPosition(Resident.GetActorLocation()))
            && Bounds.ExpandBy(100.).IsInsideOrOn(Frame.InverseTransformPosition(Eye));
    }

    bool NearShopkeeper(const AActor& Resident, FVector Eye)
    {
        const FVector Delta = Eye - Resident.GetActorLocation();
        if (Delta.SizeSquared2D() > FMath::Square(680.) || FMath::Abs(Delta.Z) > 255.) return false;
        if (const auto* Workshop = Cast<AHillsBlacksmith>(Resident.GetOwner())) return AtShop(*Workshop, Resident, Eye);
        if (const auto* Workshop = Cast<AHillsCarpenterWorkshop>(Resident.GetOwner())) return AtShop(*Workshop, Resident, Eye);
        if (const auto* Workshop = Cast<AHillsHerbalistWorkshop>(Resident.GetOwner())) return AtShop(*Workshop, Resident, Eye);
        // Both counter residents are stationary. In their local frame +X faces the guests.
        const FVector P = Resident.GetActorTransform().InverseTransformPosition(Eye);
        if (Resident.IsA<AVillageBaker>())
            return FBox(FVector(-575.,-300.,-45.),FVector(365.,510.,320.)).IsInsideOrOn(P);
        if (Resident.IsA<AVillageTavernKeeper>())
            return FBox(FVector(-220.,-590.,-45.),FVector(755.,830.,320.)).IsInsideOrOn(P);
        return false;
    }
}

void ColdSteelWorldInteraction::UpdateResidentHighlight(const APlayerController* PC, AActor* Target)
{
    if (!IsValid(PC) || !PC->GetLocalPlayer()) return;
    UWorld* World = PC->GetWorld();
    if (!World) return;
    auto* Player = PC->GetLocalPlayer()->GetPlayerController(World);
    if (Player != PC) return;
    if (!IsValid(Target) || Target->GetWorld() != World
        || !(Target->IsA<AVillageTavernKeeper>() || Target->IsA<AVillageBaker>() || Target->IsA<AVillageArtisanMerchant>()
            || Target->IsA<AVillageHerbalist>() || Target->IsA<AChapelNun>()))
        Target = nullptr;
    if (auto* Focus = World->GetSubsystem<UResidentHighlightSubsystem>()) Focus->SetFocus(Player, Target);
}

void UResidentHighlightSubsystem::RegisterShopkeeper(AActor& Resident)
{
    UWorld* World = Resident.GetWorld();
    if (!World || World->GetNetMode() == NM_DedicatedServer) return;
    auto* Self = World->GetSubsystem<UResidentHighlightSubsystem>();
    if (!Self) return;
    Self->Shopkeepers.AddUnique(&Resident);
    if (!Self->ShopLoad && !Self->ShopResponse)
        Self->ShopLoad = UAssetManager::GetStreamableManager().RequestAsyncLoad(ShopMaterialPath,
            FStreamableDelegate::CreateUObject(Self, &ThisClass::ShopMaterialLoaded));
    if (!World->GetTimerManager().IsTimerActive(Self->ShopTimer))
        World->GetTimerManager().SetTimer(Self->ShopTimer, Self, &ThisClass::UpdateShopkeepers, .2f, true);
}

void UResidentHighlightSubsystem::ShopMaterialLoaded()
{
    ShopResponse = Cast<UMaterialInterface>(ShopMaterialPath.ResolveObject());
    if (!ShopResponse) return;
    ShopParameters = UMaterialInstanceDynamic::Create(ShopResponse, this);
    UpdateShopkeepers();
}

void UResidentHighlightSubsystem::UpdateShopkeepers()
{
    UWorld* World = GetWorld();
    TArray<FVector, TInlineAllocator<4>> Eyes;
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
        if (auto* PC = It->Get(); PC && PC->GetLocalPlayer() && PC->PlayerCameraManager)
            Eyes.Add(PC->PlayerCameraManager->GetCameraLocation());

    Shopkeepers.RemoveAllSwap([](const TWeakObjectPtr<AActor>& Actor){ return !Actor.IsValid(); });
    // The engine's pending-shader material would draw its own screen overlay.
    const auto* Resource = ShopResponse && World->Scene ? ShopResponse->GetMaterialResource(World->Scene->GetShaderPlatform()) : nullptr;
    const bool bReady = Resource && Resource->GetGameThreadShaderMap() && Resource->IsGameThreadShaderMapComplete();
    uint32 ActiveSlots = 0;
    for (const auto& Weak : Shopkeepers)
    {
        auto* Actor = Weak.Get();
        const bool bNear = bReady && Eyes.ContainsByPredicate([Actor](FVector Eye){ return NearShopkeeper(*Actor,Eye); });
        if (!bNear) continue;
        const int32 Slot = FindOrAddResident(Actor);
        if (Slot != INDEX_NONE) ActiveSlots |= 1u << Slot;
    }
    for (int32 Slot = 0; Slot < Residents.Num(); ++Slot)
    {
        auto& Entry = Residents[Slot];
        const bool bActive = (ActiveSlots & (1u << Slot)) != 0;
        if (Entry.bShopLighting == bActive) continue;
        Entry.bShopLighting = bActive;
        UpdateStencil(Slot);
    }
    // A view submits the pass only when it can actually see a nearby shopkeeper.
    if (ActiveSlots && !ShopViewHandle.IsValid())
        ShopViewHandle = World->OnBeginPostProcessSettings.AddUObject(this, &ThisClass::ApplyShopResponse);
    else if (!ActiveSlots && ShopViewHandle.IsValid())
    {
        World->OnBeginPostProcessSettings.Remove(ShopViewHandle);
        ShopViewHandle.Reset();
    }
    if (Shopkeepers.IsEmpty()) World->GetTimerManager().ClearTimer(ShopTimer);
}

void UResidentHighlightSubsystem::ApplyShopResponse(FVector Eye, FSceneView* View)
{
    if (!View || View->bIsSceneCapture || View->bIsReflectionCapture || View->bIsPlanarReflection || !ShopParameters) return;
    uint32 VisibleSlots = 0;
    for (int32 Slot = 0; Slot < Residents.Num(); ++Slot)
    {
        const FResident& Entry = Residents[Slot];
        const AActor* Actor = Entry.Actor.Get();
        if (!Entry.bShopLighting || !Actor || !NearShopkeeper(*Actor, Eye)) continue;
        if (!View->ViewFrustum.IntersectSphere(Actor->GetActorLocation() + FVector(0,0,75), 190.)) continue;
        VisibleSlots |= 1u << Slot;
    }
    if (!VisibleSlots) return;
    // UE copies these scalars to the view state's own post-process MID on submission.
    if (VisibleSlots != LastShopMask)
    {
        ShopParameters->SetScalarParameterValue(ShopMaskParameter, static_cast<float>(VisibleSlots));
        LastShopMask = VisibleSlots;
    }
    ShopParameters->OverrideBlendableSettings(*View, 1.f);
}

int32 UResidentHighlightSubsystem::FindOrAddResident(AActor* Actor)
{
    int32 Slot = Residents.IndexOfByPredicate([Actor](const FResident& Entry) { return Entry.Actor == Actor; });
    if (Slot != INDEX_NONE) return Slot;
    Slot = Residents.IndexOfByPredicate([](const FResident& Entry) { return !Entry.Actor.IsValid() && !Entry.Viewers && !Entry.bShopLighting; });
    if (Slot == INDEX_NONE)
    {
        if (Residents.Num() == ResidentStencilCount) return INDEX_NONE;
        Slot = Residents.AddDefaulted();
    }
    auto& Entry = Residents[Slot];
    Entry.Actor = Actor;
    TInlineComponentArray<UMeshComponent*> Meshes(Actor);
    for (auto* Mesh : Meshes)
    {
        if (!Mesh->bRenderInMainPass || !(Mesh->IsA<USkeletalMeshComponent>()
            || Mesh->IsA<UStaticMeshComponent>() || Mesh->IsA<UGroomComponent>())) continue;
        // Set the real mesh even while its appearance is streaming. Its normal visibility,
        // hidden sections, skinning and cloth simulation also govern the custom-depth pass.
        Entry.Meshes.Add({Mesh, bool(Mesh->bRenderCustomDepth), Mesh->CustomDepthStencilValue, Mesh->CustomDepthStencilWriteMask});
    }
    return Slot;
}

void UResidentHighlightSubsystem::UpdateStencil(int32 Slot)
{
    auto& Entry = Residents[Slot];
    const int32 Next = Entry.bShopLighting ? FirstResidentStencil + Slot
        : Entry.Viewers ? FirstOtherFocusStencil + Slot : INDEX_NONE;
    if (Next == Entry.Stencil) return;
    const bool bRetagFocus = Entry.Viewers && Entry.Stencil != INDEX_NONE;
    for (const auto& Saved : Entry.Meshes)
    {
        auto* Mesh = Saved.Mesh.Get();
        if (!Mesh) continue;
        if (Entry.Stencil != INDEX_NONE && Mesh->CustomDepthStencilValue != Entry.Stencil) continue;
        if (Next == INDEX_NONE)
        {
            Mesh->SetRenderCustomDepth(Saved.bCustomDepth);
            Mesh->SetCustomDepthStencilValue(Saved.Stencil);
            Mesh->SetCustomDepthStencilWriteMask(Saved.Mask);
        }
        else
        {
            if (Entry.Stencil == INDEX_NONE && Saved.bCustomDepth) continue;
            Mesh->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
            Mesh->SetCustomDepthStencilValue(Next);
            Mesh->SetRenderCustomDepth(true);
        }
    }
    Entry.Stencil = Next;
    if (Next == INDEX_NONE) Entry = {};
    else if (bRetagFocus)
        for (auto& Pair : Viewers)
            if (Pair.Value.Resident == Slot) BindMaterial(Pair.Value);
}

void UResidentHighlightSubsystem::Release(int32 Slot)
{
    if (Slot == INDEX_NONE) return;
    --Residents[Slot].Viewers;
    UpdateStencil(Slot);
}

void UResidentHighlightSubsystem::BindMaterial(FViewer& Viewer)
{
    auto* Camera = Viewer.Camera.Get();
    if (!Camera || !Outline || Viewer.Resident == INDEX_NONE) return;
    auto* Material = Viewer.Material.Get();
    if (!Material)
    {
        Material = UMaterialInstanceDynamic::Create(Outline, Camera);
        Viewer.Material = Material;
    }
    Material->SetScalarParameterValue(StencilParameter, Residents[Viewer.Resident].Stencil);
    Camera->AddOrUpdateBlendable(Material, 1.f);
}

void UResidentHighlightSubsystem::MaterialLoaded()
{
    Outline = Cast<UMaterialInterface>(OutlinePath.ResolveObject());
    for (auto& Pair : Viewers) BindMaterial(Pair.Value);
}

void UResidentHighlightSubsystem::SetFocus(APlayerController* Player, AActor* Target)
{
    const auto* Character = Target ? Cast<AFPSGAMECharacter>(Player->GetPawn()) : nullptr;
    auto* Camera = Character ? Character->FirstPersonCamera.Get() : nullptr;
    if (!Camera)
    {
        if (auto* Previous = Viewers.Find(Player); Previous && Previous->Resident != INDEX_NONE)
        {
            if (Previous->Camera.IsValid() && Previous->Material.IsValid())
                Previous->Camera->RemoveBlendable(Previous->Material.Get());
            Release(Previous->Resident);
            Previous->Resident = INDEX_NONE;
        }
        return;
    }

    FViewer& Viewer = Viewers.FindOrAdd(Player);
    if (Viewer.Camera == Camera && Viewer.Resident != INDEX_NONE && Residents[Viewer.Resident].Actor == Target) return;
    if (Viewer.Camera != Camera)
    {
        if (Viewer.Camera.IsValid() && Viewer.Material.IsValid())
            Viewer.Camera->RemoveBlendable(Viewer.Material.Get());
        Viewer.Material.Reset();
        Viewer.Camera = Camera;
        Player->OnEndPlay.AddUniqueDynamic(this, &ThisClass::PlayerEnded);
    }
    Release(Viewer.Resident);
    Viewer.Resident = FindOrAddResident(Target);
    if (Viewer.Resident == INDEX_NONE)
    {
        if (Viewer.Material.IsValid()) Camera->RemoveBlendable(Viewer.Material.Get());
        return;
    }
    ++Residents[Viewer.Resident].Viewers;
    UpdateStencil(Viewer.Resident);
    if (Outline) BindMaterial(Viewer);
    else if (!Load)
        Load = UAssetManager::GetStreamableManager().RequestAsyncLoad(OutlinePath,
            FStreamableDelegate::CreateUObject(this, &ThisClass::MaterialLoaded));
}

void UResidentHighlightSubsystem::RemoveViewer(APlayerController* Player)
{
    FViewer Viewer;
    if (!Viewers.RemoveAndCopyValue(Player, Viewer)) return;
    if (Viewer.Camera.IsValid() && Viewer.Material.IsValid())
        Viewer.Camera->RemoveBlendable(Viewer.Material.Get());
    Release(Viewer.Resident);
    Player->OnEndPlay.RemoveDynamic(this, &ThisClass::PlayerEnded);
}

void UResidentHighlightSubsystem::PlayerEnded(AActor* Actor, EEndPlayReason::Type Reason)
{
    RemoveViewer(CastChecked<APlayerController>(Actor));
}

void UResidentHighlightSubsystem::Deinitialize()
{
    if (Load) Load->CancelHandle();
    if (ShopLoad) ShopLoad->CancelHandle();
    GetWorld()->GetTimerManager().ClearTimer(ShopTimer);
    GetWorld()->OnBeginPostProcessSettings.Remove(ShopViewHandle);
    for (auto& Pair : Viewers)
    {
        if (auto* Player = Pair.Key.Get()) Player->OnEndPlay.RemoveDynamic(this, &ThisClass::PlayerEnded);
        const auto& Viewer = Pair.Value;
        if (Viewer.Camera.IsValid() && Viewer.Material.IsValid())
            Viewer.Camera->RemoveBlendable(Viewer.Material.Get());
        Release(Viewer.Resident);
    }
    Viewers.Reset();
    for (int32 i = 0; i < Residents.Num(); ++i)
        if (Residents[i].bShopLighting)
        {
            Residents[i].bShopLighting = false;
            UpdateStencil(i);
        }
    Residents.Reset();
    Shopkeepers.Reset();
    Super::Deinitialize();
}
