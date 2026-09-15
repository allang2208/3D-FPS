#include "DevelopmentTuningSubsystem.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"

UDevelopmentTuningSubsystem* UDevelopmentTuningSubsystem::Find(const UObject* Context)
{
    UWorld* World = Context ? Context->GetWorld() : nullptr;
    UGameInstance* Instance = World ? World->GetGameInstance() : nullptr;
    return Instance ? Instance->GetSubsystem<UDevelopmentTuningSubsystem>() : nullptr;
}

bool UDevelopmentTuningSubsystem::IsEnabled(EDevelopmentTuningOption Option) const
{
    if (!GetWorld() || GetWorld()->GetNetMode() != NM_Standalone) return false;
    if (Option == EDevelopmentTuningOption::InfiniteReserveAmmo && !bReserveAmmoOverride)
        return UGameplayStatics::GetCurrentLevelName(this, true) == TEXT("DayNight_Lighting");
    return EnabledOptions.Contains(Option);
}

bool UDevelopmentTuningSubsystem::CanEdit(const APlayerController* Player) const
{
    return GetWorld() && GetWorld()->GetNetMode() == NM_Standalone && Player &&
        Player->GetWorld() == GetWorld() && Player->IsLocalController() && Player->HasAuthority() &&
        Cast<AFPSGAMECharacter>(Player->GetPawn()) != nullptr;
}

bool UDevelopmentTuningSubsystem::IsPlayerOptionEnabled(const APawn* Pawn, EDevelopmentTuningOption Option)
{
    if (!Pawn || !Pawn->HasAuthority() || !Pawn->IsPlayerControlled()) return false;
    const auto* Tuning = Find(Pawn);
    return Tuning && Tuning->IsEnabled(Option);
}

bool UDevelopmentTuningSubsystem::ShouldOneHitKill(const AActor* Victim, AController* DamageInstigator, AActor* DamageCauser)
{
    if (!Victim || !Victim->HasAuthority() || Victim->ActorHasTag(TEXT("Friendly"))) return false;
    const auto* Tuning = Find(Victim);
    if (!Tuning || !Tuning->IsEnabled(EDevelopmentTuningOption::OneHitKill)) return false;
    AController* Source = DamageInstigator;
    if (!Source && DamageCauser)
    {
        Source = DamageCauser->GetInstigatorController();
        if (!Source) if (auto* Pawn = Cast<APawn>(DamageCauser)) Source = Pawn->GetController();
    }
    const auto* Player = Cast<APlayerController>(Source);
    return Player && Player->IsLocalController() && Player->GetWorld() == Victim->GetWorld();
}

bool UDevelopmentTuningSubsystem::SetEnabled(EDevelopmentTuningOption Option, bool bEnabled, APlayerController* Player)
{
    if (!CanEdit(Player) || uint8(Option) > uint8(EDevelopmentTuningOption::NoAbilityCooldown)) return false;
    if (Option == EDevelopmentTuningOption::InfiniteReserveAmmo) bReserveAmmoOverride = true;
    if (bEnabled) EnabledOptions.Add(Option);
    else EnabledOptions.Remove(Option);
    PublishChange();
    return true;
}

bool UDevelopmentTuningSubsystem::DisableAll(APlayerController* Player)
{
    if (!CanEdit(Player)) return false;
    EnabledOptions.Reset();
    bReserveAmmoOverride = true;
    PublishChange();
    return true;
}

void UDevelopmentTuningSubsystem::PublishChange()
{
    if (auto* Profile = GetGameInstance()->GetSubsystem<UColdSteelStatusModel>()) Profile->RefreshDevelopmentTuning();
    OnChanged.Broadcast();
}
