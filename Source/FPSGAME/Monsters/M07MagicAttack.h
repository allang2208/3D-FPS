#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/NetSerialization.h"
#include "M07MagicAttack.generated.h"

class APawn;
class UMonsterCombatComponent;
class UFPSCombatHealthComponent;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class UStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;
class UParticleSystem;
class USoundBase;

UENUM(BlueprintType)
enum class EM07MagicElement : uint8
{
    Fireball,
    IceColumn,
    Lightning
};

/** Only the presentation snapshot is replicated; damage is settled by the authority once. */
USTRUCT()
struct FM07MagicAttackPresentation
{
    GENERATED_BODY()
    UPROPERTY() EM07MagicElement Element = EM07MagicElement::Fireball;
    UPROPERTY() FVector_NetQuantize Start = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Direction = FVector::ForwardVector;
    UPROPERTY() FVector_NetQuantize Impact = FVector::ZeroVector;
    UPROPERTY() FVector_NetQuantizeNormal Normal = FVector::UpVector;
    UPROPERTY() float Speed = 1500.f;
    UPROPERTY() float Radius = 140.f;
    UPROPERTY() bool bInitialized = false;
    UPROPERTY() bool bResolved = false;
    UPROPERTY() bool bSurfaceHit = false;
    UPROPERTY() bool bCancelled = false;
};

/** M-07's released spell. It owns no player resource, training, or target-selection logic. */
UCLASS()
class FPSGAME_API AM07MagicAttack : public AActor
{
    GENERATED_BODY()
public:
    AM07MagicAttack();

    /** Safe both before FinishSpawning and immediately after SpawnActor. Initialize once. */
    UFUNCTION(BlueprintCallable, Category="M07|Magic")
    void Initialize(APawn* Caster, const FVector& AimPoint, EM07MagicElement Element,
        float Damage, float RangeCm, float ProjectileSpeedCmS, float ImpactRadiusCm);

    /** Returns an already retained CDO asset; it performs no per-cast synchronous load. */
    static UNiagaraSystem* ChargeSystem(EM07MagicElement Element);
    /** Populate the existing player systems' input contract while the palm charges. */
    static void ConfigureCharge(UNiagaraComponent* FX, EM07MagicElement Element, float Fraction);

    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Core;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> Trail;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UNiagaraComponent> ColdMist;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> IceShell;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> IceHeart;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPointLightComponent> SpellLight;

    // Hard references keep shared player effects available to cooking and to all casts.
    UPROPERTY() TObjectPtr<UNiagaraSystem> FireCoreAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> FireTrailAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> FireImpactAsset;
    UPROPERTY() TObjectPtr<UMaterialInterface> FireWaveMaterial;
    UPROPERTY() TObjectPtr<USoundBase> FireHitSound;
    UPROPERTY() TObjectPtr<UStaticMesh> IceMesh;
    UPROPERTY() TObjectPtr<UStaticMesh> IceShardMesh;
    UPROPERTY() TObjectPtr<UMaterialInterface> IceShellMaterial;
    UPROPERTY() TObjectPtr<UMaterialInterface> IceHeartMaterial;
    UPROPERTY() TObjectPtr<UParticleSystem> IceImpactAsset;
    UPROPERTY() TObjectPtr<USoundBase> IceHitSound;
    UPROPERTY() TObjectPtr<UNiagaraSystem> IceCrystalAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> IceMistAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> LightningArcAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> LightningChargeAsset;
    UPROPERTY() TObjectPtr<UNiagaraSystem> LightningImpactAsset;
    UPROPERTY() TObjectPtr<USoundBase> LightningSound;

    UPROPERTY(ReplicatedUsing=OnRep_Presentation) FM07MagicAttackPresentation Presentation;
    TWeakObjectPtr<APawn> Shooter;
    TWeakObjectPtr<UMonsterCombatComponent> ShooterCombat;
    TWeakObjectPtr<UFPSCombatHealthComponent> ShooterHealth;
    TSet<TWeakObjectPtr<APawn>> HitPlayers;
    FVector PreviousVisualPosition = FVector::ZeroVector;
    float HitDamage = 0.f;
    float RemainingRange = 0.f;
    float FlightAge = 0.f;
    float NextEnvironmentUpdate = 0.f;
    float CollisionRadius = 16.f;
    bool bStarted = false;
    bool bFlightPresented = false;
    bool bImpactPresented = false;

    bool CasterAlive() const;
    bool IsHostilePlayer(APawn* Pawn) const;
    bool FirstBlockingContact(const FVector& Start, const FVector& End, float Radius, FHitResult& Hit) const;
    bool BlastVisible(APawn* Target, const FVector& Start, const FVector& End) const;
    void BeginAttack();
    void PresentFlight();
    void UpdateFlightPresentation(float DeltaSeconds, const FVector& PreviousPosition);
    void Resolve(const FHitResult* Hit);
    void ApplyPlayerHit(APawn* Target, const FHitResult& Hit, const FVector& IncomingDirection);
    void PresentImpact();
    void CancelUnresolved();
    UFUNCTION() void OnRep_Presentation();
    UFUNCTION() void OnCasterEndPlay(AActor* Actor, EEndPlayReason::Type Reason);
};
