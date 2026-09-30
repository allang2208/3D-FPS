#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FireballHandPose.h"
#include "FireballCastMotion.h"
#include "FPSLeftHandNotice.h"
#include "LeftHandPowerFistMotion.h"
#include "../Weapons/Staff/StaffCastMotion.h"
#include "FPSFireballComponent.generated.h"
class AFPSFireballProjectile;
class UColdSteelStatusModel;
class UNiagaraSystem;
class USoundBase;
class UMaterialInterface;
class UFPSCastingMeshComponent;
class UStaffWeaponComponent;

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
    bool IsGestureActive() const { return HandPhase!=EFireballHandPhase::None; }
    bool IsStaffCasting() const { return bStaffGesture&&IsGestureActive(); }
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") bool IsOccupyingLeftHand() const { return IsGestureActive()&&!bStaffGesture; }
    bool HasQueuedCast() const { return bQueuedCast; }
    // Preserve action arbitration even when the staff, rather than the left palm, casts.
    bool BlocksNewLeftHandAction() const { return bQueuedCast || bQueuedLaunch || IsGestureActive(); }
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") EFireballHandPhase GetHandPhase() const { return HandPhase; }
    UFUNCTION(BlueprintPure,Category="Skills|Fireball") float HandPhaseFraction() const;
    float GatherFraction() const;
    float HandReleaseFraction() const;
    FFireballArmMotion SampleHandMotion(const FQuat& HandCorrection,const FFireballArmMotion& Current) const;
    FStaffCastPose SampleStaffMotion(const FStaffCastPose& Current) const;
    bool TryStaffCastOrigin(FVector& OutOrigin) const;
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
    /** Hold-to-preview while the orb hovers: red trajectory line until the release. */
    void SetAimPreview(bool bActive);
    void ReleaseAimPreview();
    bool IsAimPreviewActive() const {return bAimPreview;}
    // UI pulse for a request that is rejected instead of queued (see FPSLeftHandNotice.h).
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    float CooldownFraction() const;
    void ProjectileFinished(AFPSFireballProjectile* Projectile);
    void Cancel();
    // Priority interrupts settle the actual gesture phase, keeping launched effects alive.
    void InterruptForPriority();
    void RecordGesturePayment(float BeforeMana,float AfterMana,bool bDirectCast=false);
    float TakeGesturePayment(){const float Paid=GesturePaidMana;GesturePaidMana=0.f;return Paid;}
    // Spells share one clock; the equipped staff selects right-hand casting at entry.
    bool TryBeginSpellGesture(UActorComponent* Spell,bool bRelease,float Speed,const FSimpleDelegate& Contact,bool bPowerFist=false);
    bool IsPowerFistGesture() const {return bPowerFistGesture;}
    const FLeftHandPowerFistMotion& PowerFistPose() const {return PowerFistSettings;}
    float PowerFistSourceAge() const;
    // A burst keeps the existing extended palm; only its hold deadline and impulse change.
    bool ContinueSpellRelease(UActorComponent* Spell,float HoldSeconds,bool bAddImpact);
    void CancelSpellGesture(UActorComponent* Spell);
    bool IsSpellGesture(const UActorComponent* Spell) const { return GestureOwner.Get()==Spell; }
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float RaiseDuration=.95f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float ReleaseDuration=.34f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float ReleaseEntryDuration=.26f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0",Units="s")) float LaunchContactTime=.20f;
    UPROPERTY(EditDefaultsOnly,Category="Skills|Fireball|Hands",meta=(ClampMin="0.01",Units="s")) float RecoveryDuration=.50f;
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
    FLeftHandPowerFistMotion PowerFistSettings;
    TWeakObjectPtr<UStaffWeaponComponent> CastingStaff;
    FStaffCastPose StaffEntry,StaffRecoveryEntry;
    bool bStaffGesture=false,bStaffOrb=false;
    FVector StaffOrbHover=FVector::ZeroVector;
    void BeginStaffGesture();
    void CaptureStaffRecovery();
    float GesturePhaseDuration(EFireballHandPhase Phase) const;
    float ReleaseContactAge() const;
    float ReleaseEndAge() const;
    bool bPowerFistGesture=false;
    float PowerFistRecoveryStartAge=0.f;
    uint32 CastSerial=0;
    bool bHandEntryCaptured=false;
    FTransform EntryHand,EntryClavicle;
    FVector EntryShoulder,EntryElbow;
    void UpdateFallbackHands();
    TWeakObjectPtr<AFPSFireballProjectile> Active;
    TWeakObjectPtr<UActorComponent> GestureOwner;
    FSimpleDelegate GestureContact;
    float GestureSpeed=1.f;
    float GesturePaidMana=0.f;
    bool bDirectCastWindup=false;
    EFireballHandPhase HandPhase=EFireballHandPhase::None;
    float PhaseAge=0.f;
    float ReleaseHoldEndAge=0.f;
    TArray<float,TInlineAllocator<4>> ReleaseImpactAges;
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
    FFPSLeftHandNotice HandNotice;
    bool bAimPreview=false;
    void Feedback(const FString& Text);
    void RejectHeldLeftHand();
};
