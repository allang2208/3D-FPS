#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSWeaponFXComponent.generated.h"

class UNiagaraSystem;
class UNiagaraComponent;
class UCameraComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UMaterialInstanceDynamic;
class UPointLightComponent;

USTRUCT()
struct FFPSWeaponFXParticle
{
    GENERATED_BODY()
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> Mesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> Material;
    FVector Position = FVector::ZeroVector;
    FVector Velocity = FVector::ZeroVector;
    FVector Acceleration = FVector::ZeroVector;
    FVector Size = FVector::OneVector;
    FRotator Rotation = FRotator::ZeroRotator;
    FRotator Spin = FRotator::ZeroRotator;
    float Age = 0.0f;
    float Lifetime = 0.0f;
    float Opacity = 1.0f;
    float ForwardOffset = 0.0f;
    uint8 Kind = 0;
    bool bActive = false;
    bool bBounced = false;
    uint64 BirthFrame = 0;
};

/** Local cosmetic weapon feedback. No damage, replicated state or physical viewmodel collision. */
UCLASS(ClassGroup=(Weapons), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSWeaponFXComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSWeaponFXComponent();
    UFUNCTION(BlueprintCallable, Category="Weapon FX")
    void Initialize(USkeletalMeshComponent* InWeaponMesh, UCameraComponent* InCamera);
    void SetIndependentPistol(bool Revolver,bool Suppressed,class USceneComponent* Exit);
    FVector ShotOrigin() const { return MuzzleLocation(); }
    FVector ShotForward() const { return MuzzleForward(); }
    bool IndependentSuppressed=false;
    bool bUseCharacterMuzzle=true;
    UFUNCTION(BlueprintCallable, Category="Weapon FX") void OnShot(bool bADS);
    UFUNCTION(BlueprintCallable, Category="Weapon FX") void OnImpact(const FHitResult& Hit);
    void OnTracerSegment(const FVector& Start,const FVector& End);
    int32 TracerSegments=0;
    int32 GetActiveTracerCount() const;
    int32 ExpiredTracerSegments=0;
    int32 EpicMuzzleBursts=0, EpicSmokeBursts=0;
    int32 GetActiveEpicFXCount() const;
    bool HasEpicGunFX() const { return EpicMuzzleSystem && EpicSmokeSystem; }
    FVector LastTracerEnd=FVector::ZeroVector;
    UFUNCTION(BlueprintCallable, Category="Weapon FX") void StopEmission();
    UFUNCTION(BlueprintPure, Category="Weapon FX") int32 GetActiveParticleCount() const;
    UFUNCTION(BlueprintPure, Category="Weapon FX") bool IsReady() const { return bReady; }

    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

    UPROPERTY(EditAnywhere, Category="Weapon FX|Sockets") FName MuzzleSocket = TEXT("WPN_SOCKET_Muzzle");
    UPROPERTY(EditAnywhere, Category="Weapon FX|Sockets") FName EjectSocket = TEXT("WPN_SOCKET_Eject");
    UPROPERTY(EditAnywhere, Category="Weapon FX", meta=(ClampMin="0.0", ClampMax="2.0")) float FlashScale = 1.0f;
    UPROPERTY(EditAnywhere, Category="Weapon FX", meta=(ClampMin="0.0", ClampMax="1.0")) float PistolFlashScale = 0.45f;
    UPROPERTY(EditAnywhere, Category="Weapon FX", meta=(ClampMin="0.0", ClampMax="1.0")) float SmokeOpacity = 0.55f;
    UPROPERTY(EditAnywhere, Category="Weapon FX|Smoke", meta=(ClampMin="1.0", ClampMax="2.5")) float SmokeSpreadScale = 1.6f;

private:
    bool bIndependentPistol=false, bIndependentRevolver=false;
    UPROPERTY(Transient) TObjectPtr<class USceneComponent> IndependentExit;
    void SpawnCasing();
    bool ShouldHideCasings() const;
    bool SpawnEpicFX(FVector Position, FVector Forward, float Scale);
    void UpdateSmokeStream(float DeltaTime);
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UNiagaraSystem> EpicMuzzleSystem;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UNiagaraSystem> EpicSmokeSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> EpicFXPool;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> SmokeStream;
    FFPSWeaponFXParticle* Acquire(uint8 Kind, UStaticMesh* Geometry, UMaterialInterface* Material);
    void Release(FFPSWeaponFXParticle& Particle);
    void SpawnSmoke(bool bImmediate, float InitialAge, const FVector& BirthPosition,
        const FVector& BirthForward, float HeatAtBirth);
    void AdvanceParticle(FFPSWeaponFXParticle& Particle, float DeltaTime);
    FVector MuzzleLocation() const;
    FVector MuzzleForward() const;
    void ApplyParticleTransform(FFPSWeaponFXParticle& Particle);
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> WeaponMesh;
    UPROPERTY(Transient) TObjectPtr<UCameraComponent> Camera;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> FlashLight;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UStaticMesh> CardMesh;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UStaticMesh> CylinderMesh;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UStaticMesh> RifleCasingMesh;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UMaterialInterface> RifleCasingMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UMaterialInterface> FlashMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UMaterialInterface> SmokeMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UMaterialInterface> BrassMaterial;
    UPROPERTY(EditDefaultsOnly, Category="Weapon FX|Assets") TObjectPtr<UMaterialInterface> TracerMaterial;
    UPROPERTY(Transient) TArray<FFPSWeaponFXParticle> Particles;
    static constexpr int32 MaxParticles = 64;
    float BarrelHeat = 0.0f;
    // Shots arrive at the current game time, after the interval represented by this Tick.
    float PendingHeat = 0.0f;
    double SmokeClock = 0.0;
    double LastFXShotTime = -10.0;
    double SmokeFeedUntil = -10.0;
    double SmokeTailUntil = -10.0;
    float SmokeHeatAtLastShot = 0.0f;
    double LastSmokeFeedTime = -10.0;
    float SmokeEmissionRate = 0.0f;
    FVector PreviousMuzzlePosition = FVector::ZeroVector;
    FVector PreviousMuzzleForward = FVector::ForwardVector;
    float FlashTime = 0.0f;
    uint64 FlashBirthFrame = 0;
    float LastADSMultiplier = 1.0f;
    float LastWeaponFlashMultiplier = 1.0f;
    float LastSuppression = 1.0f;
    // Authored rifle frame relative to WPN_root; independent of camera and folding sights.
    FQuat CasingFrameInRoot = FQuat::Identity;
    bool bReady = false;
};
