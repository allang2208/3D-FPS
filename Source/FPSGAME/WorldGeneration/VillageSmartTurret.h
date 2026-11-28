#pragma once

#include "CoreMinimal.h"
#include "VillageDefenseSection.h"
#include "VillageSiegeUpgrades.h"
#include "../UI/ColdSteelItemInstance.h"
#include "VillageSmartTurret.generated.h"

class UBoxComponent;
class UPoseableMeshComponent;
class UStaticMeshComponent;
class UFPSBallisticsComponent;
class UFPSWeaponFXComponent;
class USoundBase;
class AController;
class AColdSteelPlayerState;
class ATemperateHillsWorld;

/** Workshop-backed effective stats preview for a mounted or candidate firearm. */
struct FPSGAME_API FSmartTurretWeaponStats
{
    bool bValid = false;
    bool bSuppressed = false;
    bool bShotgun = false;
    bool bTubeShotgun = false;
    int32 PelletCount = 1;
    int32 BaseCapacity = 30;
    int32 ExpandedCapacity = 30;
    int32 BonusPierce = 0;
    float PerShotDamage = 0.f;
    float FireInterval = 0.12f;
    float RPM = 500.f;
    float ReloadTime = 2.0f;
    float EmptyReloadTime = 2.5f;
    float EffectiveScanRangeCm = 4200.f;
    float WeaponEffectiveRangeCm = 8500.f;
    float BulletSpeedCm = 35000.f;
    float SpreadDeg = 1.f;
    float WeakpointChance = 0.f;
    float CritDamageMultiplier = 1.5f;
    float EstimatedDPS = 0.f;
};

/** Scheme B Garrison Rune-Steel Smart Gun Turret: mounts 16 long guns, infinite reserve ammo, 3D predictive targeting. */
UCLASS()
class FPSGAME_API AVillageSmartTurret final : public AVillageDefenseSection
{
    GENERATED_BODY()
    friend class FVillageSmartTurretTest;
    friend struct FSiegeDrawerReview;
public:
    AVillageSmartTurret();

    static FSoftObjectPath MeshAsset(const TCHAR* Suffix);
    static bool IsMountableFirearm(const FString& Definition);
    static const TCHAR* WeaponArchetypeLabel(const FString& Definition);
    static bool IsShotgunDefinition(const FString& Definition);
    static bool IsTubeShotgunDefinition(const FString& Definition);
    static USoundBase* ResolveWeaponFireSound(const FString& Definition, bool bSuppressed);
    static FSmartTurretWeaponStats ComputeWeaponStats(const FColdSteelItem& Item, UGameInstance* GI, VillageSiegeUpgrades::FRanks Ranks);

    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Out) const override;
    virtual void Tick(float DeltaSeconds) override;
    virtual float TakeDamage(float Amount, const FDamageEvent& Event, AController* Instigator, AActor* Causer) override;
    virtual bool BlocksPassage() const override { return false; }

    bool HasMountedWeapon() const { return !MountedWeapon.Definition.IsEmpty(); }
    const FColdSteelItem& GetMountedWeapon() const { return MountedWeapon; }
    int32 GetCurrentAmmo() const { return CurrentAmmo; }
    int32 GetMaxAmmo() const { return MaxAmmo; }
    bool IsReloading() const { return bReloading; }
    float GetReloadProgressFraction() const;
    float GetReloadRemainingSeconds() const;
    float GetCurrentYawDeg() const { return CurrentYawDeg; }
    float GetCurrentPitchDeg() const { return CurrentPitchDeg; }
    VillageSiegeUpgrades::FRanks CurrentAllRanks() const;
    FSmartTurretWeaponStats GetCurrentWeaponStats() const;

    /** Server-only atomic mount/swap from player backpack/compartment into this turret. */
    bool ServerMountFromPlayer(APawn* Player, const FString& ItemInstanceId, FString& OutMessage);
    /** Server-only atomic unmount back into player backpack (or warehouse fallback). */
    bool ServerUnmountToPlayer(APawn* Player, FString& OutMessage);
    /** Ejects mounted weapon safely on destruction or building demolition (backpack -> warehouse -> world drop). */
    void EjectWeaponSafely(APawn* PreferredOwner = nullptr);

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void OnRep_Setup() override;
    virtual void ApplyHealth() override;

    UFUNCTION() void OnRep_MountedWeapon();
    UFUNCTION(NetMulticast, Unreliable) void MulticastShotFX(FVector_NetQuantize MuzzlePos, FVector_NetQuantizeNormal AimDir, bool bSuppressed, uint8 FiredPellets);

private:
    enum class EOpticState : uint8 { Idle = 1, Tracking = 2, Firing = 3, Reloading = 4 };

    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> InteractHull;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> YawMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> CradleMesh;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> SlideMesh;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> WeaponAttach;
    UPROPERTY(Transient) TObjectPtr<UPoseableMeshComponent> MountedGunMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UFPSBallisticsComponent> Ballistics;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UFPSWeaponFXComponent> WeaponFX;

    UPROPERTY(ReplicatedUsing=OnRep_MountedWeapon) FColdSteelItem MountedWeapon;
    UPROPERTY(Replicated) int32 CurrentAmmo = 0;
    UPROPERTY(Replicated) int32 MaxAmmo = 0;
    UPROPERTY(Replicated) bool bReloading = false;
    UPROPERTY(Replicated) double ReloadEndServerTime = 0.;
    UPROPERTY(Replicated) float ReplicatedReloadDuration = 1.5f;
    UPROPERTY(Replicated) float TargetYawDeg = 0.f;
    UPROPERTY(Replicated) float TargetPitchDeg = 0.f;
    UPROPERTY(Replicated) uint8 OpticState = 1;

    float CurrentYawDeg = 0.f;
    float CurrentPitchDeg = 0.f;
    float SlideRecoilOffset = 0.f;
    double NextScanTime = 0.;
    double NextLosCheckTime = 0.;
    double NextFireTime = 0.;
    double FireFlashUntil = -1.;
    double ReloadDurationSec = 1.5;
    bool bRestoredFromSave = false;
    bool bCurrentShotWeakpoint = false;
    bool bPendingLocalReloadComplete = false;
    uint32 FireSequence = 0;
    uint8 LastAppliedOpticState = 0;
    FString LastBuiltVisualKey;
    FString CachedFireSoundKey;

    TWeakObjectPtr<APawn> CurrentTarget;
    TWeakObjectPtr<APawn> MountedOwnerPawn;
    TWeakObjectPtr<AColdSteelPlayerState> MountedOwnerState;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CachedFireSound;
    mutable TWeakObjectPtr<ATemperateHillsWorld> CachedVillageWorld;
    mutable FSmartTurretWeaponStats CachedWeaponStats;
    mutable FString CachedStatsWeaponId;
    mutable VillageSiegeUpgrades::FRanks CachedStatsRanks{};
    mutable bool bWeaponStatsCached = false;
    mutable TWeakObjectPtr<APawn> CachedAimTarget;
    mutable FName CachedHeadBone = NAME_None;
    mutable FName CachedTorsoBone = NAME_None;
    FTransform CachedMuzzleInWeapon = FTransform::Identity;
    bool bHasMuzzleInWeapon = false;
    mutable TWeakObjectPtr<UStaticMeshComponent> MuzzleMarkerPart;

    double CurrentServerTime() const;
    void UpdateTickCadence();
    static FString ComputeWeaponVisualKey(const FColdSteelItem& Item);

    void EnsureVisualAssembly();
    void RebuildMountedGunVisual();
    void ClearMountedGunVisual();
    void ApplyOpticVisualState(float DeltaSeconds);
    void StepTurretOrientation(float DeltaSeconds, float DesiredYaw, float DesiredPitch);
    void TickAuthorityCombat(float DeltaSeconds, double Now);
    void AcquireTarget(const FSmartTurretWeaponStats& Stats, double Now);
    bool HasLineOfSightToTarget(const FVector& Origin, const FVector& AimPoint, const AActor* Target) const;
    FVector SelectTargetAimPoint(APawn* Target, bool bWeakpointLock) const;
    FTransform ResolveMuzzleWorldTransform() const;
    void StartReload(const FSmartTurretWeaponStats& Stats, bool bEmpty);
    void FinishOrStepReload(const FSmartTurretWeaponStats& Stats, double Now);
    void FireRound(const FSmartTurretWeaponStats& Stats, const FVector& AimPoint, double Now);
    bool ReturnWeaponToInventory(APawn* Recipient, const FColdSteelItem& Item, bool bAllowWarehouseFallback);
    void SpawnDroppedWeapon(const FColdSteelItem& Item);
    void PersistWeaponState();
};
