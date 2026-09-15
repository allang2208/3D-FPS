#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FireballHandPose.h"
#include "FireballCastMotion.h"
#include "FPSFireballComponent.generated.h"
class AFPSFireballProjectile;
class UColdSteelStatusModel;
class UNiagaraSystem;
class USoundBase;
class UMaterialInterface;
class UFPSCastingMeshComponent;

UENUM(BlueprintType)
enum class EFireballHandPhase : uint8
{
    None,
    Raising,
    Holding UMETA(Hidden), // Reserved enum value; hovering no longer owns the hand.
    Releasing,
    Recovering,
    ReadyingRelease
};

/** Local player ability. The profile owns MP, cooldown and training; the actor owns flight. */
UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSFireballComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSFireballComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger();
    bool IsPrepared() const;
    bool IsFlying() const;
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") bool IsOccupyingLeftHand() const { return HandPhase!=EFireballHandPhase::None; }
    bool HasQueuedCast() const { return bQueuedCast; }
    bool BlocksNewLeftHandAction() const { return bQueuedCast || bQueuedLaunch || IsOccupyingLeftHand(); }
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") EFireballHandPhase GetHandPhase() const { return HandPhase; }
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") float HandPhaseFraction() const;
    float GatherFraction() const;
    float HandReleaseFraction() const;
    FFireballArmMotion SampleHandMotion(const FQuat& HandCorrection,const FFireballArmMotion& Current) const;
    bool HasLaunchedFromHand() const { return bLaunchCommitted; }
    uint32 GetCastSerial() const { return CastSerial; }
    const FFireballHandPose& HandPose() const { return PoseSettings; }
    void CaptureHandEntry(const FTransform& Hand,const FTransform& Clavicle,const FVector& Shoulder,const FVector& Elbow);
    const FTransform& HandEntry() const { return EntryHand; }
    const FTransform& HandEntryClavicle() const { return EntryClavicle; }
    const FVector& HandEntryShoulder() const { return EntryShoulder; }
    const FVector& HandEntryElbow() const { return EntryElbow; }
    FVector HeldOrbPosition() const;
    FString StatusText() const;
    float CooldownFraction() const;
    void ProjectileFinished(AFPSFireballProjectile* Projectile);
    void Cancel();
    // Other projectile spells share the accepted left-arm gesture and action arbitration.
    bool TryBeginSpellGesture(UActorComponent* Spell,bool bRelease,float Speed,const FSimpleDelegate& Contact);
    void CancelSpellGesture(UActorComponent* Spell);
    bool IsSpellGesture(const UActorComponent* Spell) const { return GestureOwner.Get()==Spell; }
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float RaiseDuration=.95f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float ReleaseDuration=.34f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float ReleaseEntryDuration=.26f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0",Units="s")) float LaunchContactTime=.20f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float RecoveryDuration=.44f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball") TSoftObjectPtr<UNiagaraSystem> CoreAsset;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball") TSoftObjectPtr<UNiagaraSystem> TrailAsset;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball") TSoftObjectPtr<UNiagaraSystem> ExplosionAsset;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball") TSoftObjectPtr<UMaterialInterface> ShockwaveAsset;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball") TSoftObjectPtr<USoundBase> ImpactSoundAsset;
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Core;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Trail;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Explosion;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> Shockwave;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<UFPSCastingMeshComponent> FallbackHands;
    FFireballHandPose PoseSettings;
    uint32 CastSerial=0;
    bool bHandEntryCaptured=false;
    FTransform EntryHand,EntryClavicle;
    FVector EntryShoulder,EntryElbow;
    void UpdateFallbackHands();
    TWeakObjectPtr<AFPSFireballProjectile> Active;
    TWeakObjectPtr<UActorComponent> GestureOwner;
    FSimpleDelegate GestureContact;
    float GestureSpeed=1.f;
    EFireballHandPhase HandPhase=EFireballHandPhase::None;
    float PhaseAge=0.f;
    bool bQueuedCast=false, bQueuedLaunch=false, bLaunchCommitted=false;
    bool bReleaseFromRest=false;
    float RecoveryReleaseAlpha=0.f;
    EFireballHandPhase RecoveryFromPhase=EFireballHandPhase::None;
    float RecoveryFromFraction=0.f;
    void SetHandPhase(EFireballHandPhase Phase);
    void TryBeginQueuedCast();
    void TryBeginQueuedLaunch();
    void LaunchAtContact();
    UColdSteelStatusModel* Model() const;
    FString LastMessage;
    double MessageUntil=0;
    void Feedback(const FString& Text);
};
