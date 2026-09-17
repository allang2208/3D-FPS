#pragma once

#include "CoreMinimal.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "DevelopmentTuningSubsystem.generated.h"

class APlayerController;
class AController;
class APawn;
class AActor;

UENUM(BlueprintType)
enum class EDevelopmentTuningOption : uint8
{
    Invincible,
    OneHitKill,
    InfiniteReserveAmmo,
    InfiniteMana,
    NoAbilityCooldown,
    /** 建造不消耗资源：放置体素块时不扣背包／仓库里的体块。 */
    FreeBuilding
};

/** Single-player session overrides. These flags are deliberately absent from the profile/save. */
UCLASS()
class FPSGAME_API UDevelopmentTuningSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    static UDevelopmentTuningSubsystem* Find(const UObject* Context);
    static bool IsPlayerOptionEnabled(const APawn* Pawn, EDevelopmentTuningOption Option);
    static bool ShouldOneHitKill(const AActor* Victim, AController* DamageInstigator, AActor* DamageCauser);

    UFUNCTION(BlueprintPure, Category="Development|Tuning") bool IsEnabled(EDevelopmentTuningOption Option) const;
    UFUNCTION(BlueprintPure, Category="Development|Tuning") bool CanEdit(const APlayerController* Player) const;
    UFUNCTION(BlueprintCallable, Category="Development|Tuning") bool SetEnabled(EDevelopmentTuningOption Option, bool bEnabled, APlayerController* Player);
    UFUNCTION(BlueprintCallable, Category="Development|Tuning") bool DisableAll(APlayerController* Player);
    FSimpleMulticastDelegate OnChanged;

private:
    void PublishChange();
    UPROPERTY(Transient) TSet<EDevelopmentTuningOption> EnabledOptions;
    UPROPERTY(Transient) bool bReserveAmmoOverride = false;
};
