#include "ChapelDialogueComponent.h"
#include "ResidentConversation.h"
#include "VillageArtisanMerchant.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "../FPSGAMECharacter.h"
#include "../FPSGAMEPlayerController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../UI/ColdSteelWorldInteraction.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "InputCoreTypes.h"
#include "TimerManager.h"
#include "UnrealClient.h"

namespace
{
    constexpr float ArtisanAidSeconds = 3.f;
    constexpr float ArtisanAidInterval = .08f;

    bool CanAidDownedArtisan(const AFPSGAMEPlayerController* Player, const APawn* Pawn, const AVillageArtisanMerchant* Artisan)
    {
        if (!IsValid(Player) || !IsValid(Pawn) || Player->GetPawn() != Pawn
            || AFPSGAMEPlayerController::BlocksOngoingActions(Player) || !ResidentConversation::IsSpeakerDowned(Artisan))
            return false;
        const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
        return Health && !Health->IsDead();
    }

    bool CanAidArtisan(const AFPSGAMEPlayerController* Player, const APawn* Pawn, const AVillageArtisanMerchant* Artisan)
    {
        if (!CanAidDownedArtisan(Player, Pawn, Artisan)) return false;
        constexpr float Reach = 250.f;
        if (ColdSteelWorldInteraction::IsFocused(Pawn, Artisan, Reach)) return true;
        if (!Player->HasAuthority() || Player->IsLocalController() || Player->bShowMouseCursor) return false;
        // A guest with the first-person body hidden looks from the camera mounted on
        // the capsule. The authority normally tests the forward-shifted anatomical eye.
        // Use the same controlled aim, reach and first blocking hit from this second
        // server-owned viewpoint. A wall or another resident still blocks the rescue.
        const auto* Character = Cast<AFPSGAMECharacter>(Pawn);
        if (!Character || !Character->FirstPersonCamera) return false;
        const FVector Eye = Character->FirstPersonCamera->GetComponentLocation();
        FHitResult Hit;
        return Pawn->GetWorld()->LineTraceSingleByChannel(Hit, Eye, Eye + Player->GetControlRotation().Vector() * Reach,
                   ECC_Visibility, FCollisionQueryParams(SCENE_QUERY_STAT(ArtisanAidCamera), false, Pawn))
            && Hit.GetActor() == Artisan;
    }

    bool CanHoldAidInput(const AFPSGAMEPlayerController* Player, const APawn* Pawn, const AVillageArtisanMerchant* Artisan)
    {
        if (!CanAidDownedArtisan(Player, Pawn, Artisan) || !Player->CanOpenGameMenu()) return false;
        const auto* Character = Cast<AFPSGAMECharacter>(Pawn);
        const auto* Viewport = Player->GetWorld()->GetGameViewport();
        return Character && !Character->IsAmmoWheelOpen() && Viewport && Viewport->Viewport && Viewport->Viewport->HasFocus();
    }

    bool CanContinueLocalAid(const AFPSGAMEPlayerController* Player, const APawn* Pawn, const AVillageArtisanMerchant* Artisan)
    {
        return CanHoldAidInput(Player, Pawn, Artisan) && ColdSteelWorldInteraction::IsFocused(Pawn, Artisan);
    }
}

bool UChapelDialogueComponent::CanAidFocusedArtisan(const AVillageArtisanMerchant* Artisan) const
{
    // The HUD already has the same blocking eye trace used by BeginFirstAid.
    const auto* Player = Cast<AFPSGAMEPlayerController>(GetOwner());
    return !bPending && (LocalAidTarget.IsExplicitlyNull() || LocalAidTarget.Get() == Artisan)
        && Player && CanHoldAidInput(Player, Player->GetPawn(), Artisan);
}

void UChapelDialogueComponent::BeginFirstAid(AVillageArtisanMerchant* Artisan)
{
    auto* Player = Cast<AFPSGAMEPlayerController>(GetOwner());
    APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    if (bPending || !LocalAidTarget.IsExplicitlyNull() || !CanContinueLocalAid(Player, Pawn, Artisan)) return;

    if (++LocalAidSerial == 0) ++LocalAidSerial;
    LocalAidPawn = Pawn;
    LocalAidTarget = Artisan;
    LocalAidStart = GetWorld()->GetTimeSeconds();
    GetWorld()->GetTimerManager().SetTimer(LocalAidTimer, this, &ThisClass::UpdateLocalFirstAid, ArtisanAidInterval, true);
    ServerBeginFirstAid(LocalAidSerial, Artisan);
}

TOptional<float> UChapelDialogueComponent::FirstAidProgress(const AActor* Target) const
{
    if (!Target || LocalAidTarget.Get() != Target) return {};
    if (bLocalAidConfirmed) return 1.f;
    const double Fraction = (GetWorld()->GetTimeSeconds() - LocalAidStart) / ArtisanAidSeconds;
    return static_cast<float>(FMath::Clamp(Fraction, 0., 1.));
}

bool UChapelDialogueComponent::ReleaseFirstAid()
{
    if (LocalAidTarget.IsExplicitlyNull()) return false;
    if (bLocalAidConfirmed) return true;
    const bool HeldLongEnough = GetWorld()->GetTimeSeconds() - LocalAidStart >= ArtisanAidSeconds;
    bLocalAidConfirmed = HeldLongEnough && CanContinueLocalAid(Cast<AFPSGAMEPlayerController>(GetOwner()), LocalAidPawn.Get(), LocalAidTarget.Get());
    const bool Completed = bLocalAidConfirmed;
    if (!Completed) EndLocalFirstAid();
    ServerEndFirstAid(LocalAidSerial, Completed);
    return true;
}

void UChapelDialogueComponent::UpdateLocalFirstAid()
{
    if (bLocalAidConfirmed) return;
    const auto* Player = Cast<AFPSGAMEPlayerController>(GetOwner());
    const auto* Viewport = GetWorld()->GetGameViewport();
    const bool KeyHeld = Viewport && Viewport->Viewport && Viewport->Viewport->KeyState(EKeys::E);
    if (!KeyHeld || !CanContinueLocalAid(Player, LocalAidPawn.Get(), LocalAidTarget.Get()))
    {
        EndLocalFirstAid();
        ServerEndFirstAid(LocalAidSerial, false);
    }
    else if (GetWorld()->GetTimeSeconds() - LocalAidStart >= ArtisanAidSeconds)
    {
        bLocalAidConfirmed = true;
        ServerEndFirstAid(LocalAidSerial, true);
    }
}

void UChapelDialogueComponent::EndLocalFirstAid()
{
    if (auto* World = GetWorld()) World->GetTimerManager().ClearTimer(LocalAidTimer);
    LocalAidTarget.Reset();
    LocalAidPawn.Reset();
    bLocalAidConfirmed = false;
}

void UChapelDialogueComponent::ServerBeginFirstAid_Implementation(uint32 Serial, AVillageArtisanMerchant* Target)
{
    auto* Player = Cast<AFPSGAMEPlayerController>(GetOwner());
    APawn* Pawn = Player ? Player->GetPawn() : nullptr;
    if (!Serial || AuthorityAidSerial || !CanAidArtisan(Player, Pawn, Target))
    {
        ClientEndFirstAid(Serial);
        return;
    }
    AuthorityAidSerial = Serial;
    AuthorityAidPawn = Pawn;
    AuthorityAidTarget = Target;
    AuthorityAidStart = GetWorld()->GetTimeSeconds();
    GetWorld()->GetTimerManager().SetTimer(AuthorityAidTimer, this, &ThisClass::UpdateAuthorityFirstAid, ArtisanAidInterval, true);
}

void UChapelDialogueComponent::ServerEndFirstAid_Implementation(uint32 Serial, bool CompletedHold)
{
    if (!AuthorityAidSerial || Serial != AuthorityAidSerial) return;
    if (!CompletedHold)
    {
        EndAuthorityFirstAid();
        return;
    }
    bAuthorityAidConfirmed = true;
    UpdateAuthorityFirstAid();
}

void UChapelDialogueComponent::UpdateAuthorityFirstAid()
{
    const uint32 Serial = AuthorityAidSerial;
    APawn* Pawn = AuthorityAidPawn.Get();
    AVillageArtisanMerchant* Artisan = AuthorityAidTarget.Get();
    const double Elapsed = GetWorld()->GetTimeSeconds() - AuthorityAidStart;
    if (Elapsed > ArtisanAidSeconds + 8. || !CanAidArtisan(Cast<AFPSGAMEPlayerController>(GetOwner()), Pawn, Artisan))
    {
        EndAuthorityFirstAid();
        ClientEndFirstAid(Serial);
        return;
    }
    if (!bAuthorityAidConfirmed || Elapsed < ArtisanAidSeconds) return;

    EndAuthorityFirstAid();
    if (auto* Vitals = Artisan->FindComponentByClass<UVillageArtisanVitalsComponent>())
        Vitals->ReviveFromFirstAid(Pawn);
    ClientEndFirstAid(Serial);
}

void UChapelDialogueComponent::EndAuthorityFirstAid()
{
    if (auto* World = GetWorld()) World->GetTimerManager().ClearTimer(AuthorityAidTimer);
    AuthorityAidTarget.Reset();
    AuthorityAidPawn.Reset();
    AuthorityAidSerial = 0;
    bAuthorityAidConfirmed = false;
}

void UChapelDialogueComponent::ClientEndFirstAid_Implementation(uint32 Serial)
{
    if (Serial == LocalAidSerial) EndLocalFirstAid();
}
