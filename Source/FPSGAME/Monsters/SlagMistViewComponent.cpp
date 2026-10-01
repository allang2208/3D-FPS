#include "SlagMistViewComponent.h"
#include "SlagBlackMist.h"
#include "FPSCombatHealthComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "../UI/StatusEffectsComponent.h"
#include "Camera/CameraComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    const FName BlindName(TEXT("blind"));
}
USlagMistViewComponent::USlagMistViewComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    PrimaryComponentTick.TickGroup = TG_PostUpdateWork;
    PrimaryComponentTick.bStartWithTickEnabled = false;
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> Material(
        TEXT("/Game/Monsters/HundredEyedSlag/WorldSmokeV19/M_SlagMistBlindView.M_SlagMistBlindView"));
    ViewMaterial = Material.Object;
}
USlagMistViewComponent* USlagMistViewComponent::GetOrAdd(AActor* Pawn)
{
    if (!IsValid(Pawn)) return nullptr;
    if (auto* Existing = Pawn->FindComponentByClass<USlagMistViewComponent>()) return Existing;
    auto* Component = NewObject<USlagMistViewComponent>(Pawn);
    if (!Component->ViewMaterial) Component->ViewMaterial = LoadObject<UMaterialInterface>(nullptr,
        TEXT("/Game/Monsters/HundredEyedSlag/WorldSmokeV19/M_SlagMistBlindView.M_SlagMistBlindView"));
    Pawn->AddInstanceComponent(Component); Component->RegisterComponent(); return Component;
}
float USlagMistViewComponent::BlindRemaining() const
{
    return GetWorld() ? FMath::Max(0., BlindUntil - GetWorld()->GetTimeSeconds()) : 0.f;
}
void USlagMistViewComponent::ClearBlindness()
{
    BlindUntil = 0.; NextDisplayRefresh = 0.;
    BlurStrength = 0.f;
    if (bShowBlindTile)
        if (auto* Display = GetOwner()->FindComponentByClass<UStatusEffectsComponent>()) Display->Remove(BlindName);
    bShowBlindTile = false;
}
void USlagMistViewComponent::RefreshBlindness(float Seconds)
{
    if (const auto* Status = GetOwner()->FindComponentByClass<UCombatStatusFormula>(); Status && Status->IsImmune()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    BlindUntil = FMath::Max(BlindUntil, Now + Seconds);
    // Gameplay refreshes every frame; UI broadcasts are capped at 5 Hz per pawn.
    if (!bShowBlindTile || Now >= NextDisplayRefresh)
    {
        UStatusEffectsComponent::GetOrCreate(GetOwner())->SetTimed(BlindName, BlindRemaining());
        bShowBlindTile = true; NextDisplayRefresh = Now + .2;
    }
}
void USlagMistViewComponent::RemoveViewLayer()
{
    if (auto* Camera = BoundCamera.Get(); Camera && ViewInstance) Camera->RemoveBlendable(ViewInstance);
    BoundCamera.Reset();
}
void USlagMistViewComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    RemoveViewLayer(); Super::EndPlay(Reason);
}
void USlagMistViewComponent::TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* Fn)
{
    Super::TickComponent(Dt, Type, Fn);
    auto* Pawn = Cast<APawn>(GetOwner());
    const auto* Vitals = GetOwner()->FindComponentByClass<UFPSCombatHealthComponent>();
    if (!Pawn || !Pawn->IsPlayerControlled() || (Vitals && Vitals->IsDead()))
    { ClearBlindness(); RemoveViewLayer(); SetComponentTickEnabled(false); return; }
    auto* PC = Cast<APlayerController>(Pawn->GetController());
    FVector Eye; FRotator Rotation; Pawn->GetActorEyesViewPoint(Eye, Rotation);
    if (PC && PC->IsLocalController() && PC->PlayerCameraManager)
    { Eye = PC->PlayerCameraManager->GetCameraLocation(); Rotation = PC->PlayerCameraManager->GetCameraRotation(); }
    TArray<ASlagBlackMist*> All; ASlagBlackMist::Gather(GetWorld(), All);
    bool InSmoke = false;
    for (auto* Cloud : All)
    {
        const bool Exposed = Cloud->ContainsExposedEye(Eye, Pawn);
        if (Exposed) { InSmoke = true; RefreshBlindness(Cloud->BlindSeconds); }
    }
    // The latest contract is strictly in-smoke: no lingering screen lock on exit.
    if (!InSmoke) ClearBlindness();
    const float Remaining = BlindRemaining();
    if (Remaining <= 0.f && bShowBlindTile) ClearBlindness();
    if (PC && PC->IsLocalController() && InSmoke && Remaining > 0.f && ViewMaterial)
    {
        UCameraComponent* Camera = nullptr;
        TInlineComponentArray<UCameraComponent*> Cameras(Pawn);
        for (auto* Candidate : Cameras) if (Candidate->IsActive()) { Camera = Candidate; break; }
        if (Camera && Camera != BoundCamera.Get())
        {
            RemoveViewLayer();
            if (!ViewInstance) ViewInstance = UMaterialInstanceDynamic::Create(ViewMaterial, this);
            Camera->AddOrUpdateBlendable(ViewInstance, 1.f); BoundCamera = Camera;
        }
        if (BoundCamera.IsValid() && ViewInstance)
        {
            BlurStrength = FMath::FInterpTo(BlurStrength, 1.f, Dt, 14.f);
            ViewInstance->SetScalarParameterValue(TEXT("BlindStrength"), BlurStrength);
        }
    }
    else RemoveViewLayer();
    if (All.IsEmpty() && Remaining <= 0.f) SetComponentTickEnabled(false);
}
