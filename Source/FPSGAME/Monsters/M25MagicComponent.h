#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "M25MagicComponent.generated.h"

class AVortexCofferM25;
class APawn;
class UNiagaraComponent;
class UNiagaraSystem;
class UStaticMesh;
class UMaterialInterface;
class USoundBase;
class UAudioComponent;
struct FStreamableHandle;

UENUM()
enum class EM25Spell : uint8 { None, Lightning, ThunderLance, Recovery };

USTRUCT()
struct FM25CastState
{
    GENERATED_BODY()
    UPROPERTY() EM25Spell Spell = EM25Spell::None;
    UPROPERTY() float StartedAt = 0.f;
    UPROPERTY() float Duration = 0.f;
    UPROPERTY() bool bAimLocked = false;
    UPROPERTY() FVector_NetQuantize Aim = FVector::ZeroVector;
};

/** Shared BT chooses when to attack; this component owns windup, release and recovery. */
UCLASS(ClassGroup=(Monsters), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UM25MagicComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UM25MagicComponent();
    bool CanAttack(APawn* Target) const;
    bool StartAttack(APawn* Target);
    bool IsBusy() const { return CastState.Spell != EM25Spell::None; }
    void SetTarget(APawn* Target);
    void Interrupt();
    FVector ElectrodeLocation() const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic") bool bAttacksEnabled = true;
    // Final authored monster attack: no player attribute conversion is applied here.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic", meta=(ClampMin="0")) float MagicAttack = 60.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic", meta=(ClampMin="0")) float LightningMultiplier = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic", meta=(ClampMin="0")) float LanceMultiplier = 2.5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic", meta=(ClampMin="0", Units="s")) float LightningCooldown = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M25|Magic", meta=(ClampMin="0", Units="s")) float LanceCooldown = 20.f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="0.1", Units="s")) float LightningWindup = .55f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="0.3", Units="s")) float LanceWindup = 1.6f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="0", Units="s")) float LanceAimLockSeconds = .25f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="100", Units="cm")) float LightningRange = 1400.f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="100", Units="cm")) float LanceRange = 1800.f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="0", Units="cm")) float LanceChargeHeight = 65.f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="1", Units="cm")) float LanceHitRadius = 14.f;
    UPROPERTY(EditAnywhere, Category="M25|Magic", meta=(ClampMin="0", Units="cm")) float MaxLeadDistance = 300.f;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UNiagaraSystem> ChargeAsset;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UNiagaraSystem> ArcAsset;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UNiagaraSystem> ImpactAsset;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UStaticMesh> LanceTube;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UStaticMesh> LanceIrisMesh;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UMaterialInterface> LanceBody;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UMaterialInterface> LanceIrisMat;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UNiagaraSystem> LanceGatherAsset;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<UNiagaraSystem> LanceMuzzleAsset;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<USoundBase> ReleaseSound;
    UPROPERTY(EditDefaultsOnly, Category="M25|Magic|VFX") TSoftObjectPtr<USoundBase> LanceTailSound;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Delta, ELevelTick Type, FActorComponentTickFunction* Tick) override;

private:
    UPROPERTY(ReplicatedUsing=OnRep_CastState) FM25CastState CastState;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> Charge;
    UPROPERTY(Transient) TObjectPtr<UAudioComponent> ChargeVoice;
    // Lance telegraph hardware (ray family): charging iris bloom at the electrode
    // and a one-shot muzzle iris flash on release. Client-side only.
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> LanceIris;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> LanceIrisMID;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> MuzzleIris;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> MuzzleIrisMID;
    double MuzzleFlashAt = -1.;
    double NextChargeArc = 0.;
    EM25Spell PresentedSpell = EM25Spell::None;
    TWeakObjectPtr<AVortexCofferM25> Monster;
    TWeakObjectPtr<APawn> AttackTarget;
    TSharedPtr<FStreamableHandle> AssetLoad;
    double LightningReadyAt = 0., LanceReadyAt = 0., RetryReadyAt = 0.;
    float DamageSnapshot = 0.f;
    bool bOpenedWithLightning = false;
    float Clock() const;
    bool CanExecute() const;
    bool LivingEnemyPlayer(const APawn* Target) const;
    bool HasSight(const APawn* Target, EM25Spell Spell) const;
    bool ClearChargeOrigin(EM25Spell Spell) const;
    EM25Spell SelectSpell(APawn* Target) const;
    FVector Origin(EM25Spell Spell) const;
    FVector TargetPoint(const APawn* Target) const;
    FVector PredictAim(const APawn* Target, float Seconds) const;
    bool FirstContact(FVector Start, FVector End, float Radius, FHitResult& Hit) const;
    void Release();
    void Cancel();
    void SetPhase(EM25Spell Spell, float Duration);
    void UpdatePresentation();
    UFUNCTION() void OnRep_CastState();
    UFUNCTION(NetMulticast, Unreliable) void MulticastImpact(FVector_NetQuantize Start,
        FVector_NetQuantize Point, FVector_NetQuantizeNormal Normal, bool bSurfaceHit, bool bLance);
};
