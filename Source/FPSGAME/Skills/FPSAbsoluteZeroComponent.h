#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "AbsoluteZeroTypes.h"
#include "FPSLeftHandNotice.h"
#include "../Weapons/Staff/StaffCastMotion.h"
#include "FPSAbsoluteZeroComponent.generated.h"

class AFPSAbsoluteZeroNova;
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UDynamicMeshComponent;
class UMaterialInstanceDynamic;
class UNiagaraComponent;
class UPointLightComponent;

/** Player ability component for IV Ultimate Ice Nova ("绝对零度"). */
UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSAbsoluteZeroComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSAbsoluteZeroComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger();
    void CancelPending();
    void InterruptPending(bool bCancelChannel);
    void FinishNovasForRemoval();
    bool IsChanneling() const { return bChanneling||bNetChanneling; }
    bool HasLightStaggerResistance() const { return IsChanneling(); }
    float ChannelAlpha() const;
    bool IsPresentingStaffSlam() const;
    FStaffCastPose SampleStaffSlamPose(const FStaffCastPose& Current) const;
    void GetCameraMotion(FVector& OutLocation,FRotator& OutRotation,float* OutFov=nullptr) const;
    bool HasQueuedAction() const { return bQueued||bChanneling; }
    bool HasUnreleasedCast() const { return bCommitted||bNetAwaitingCancel; }
    /** Incoming damage multiplier during grounding windup (0.65 base, 0.50 with IceArmor). */
    float ChannelDamageTakenMultiplier() const;
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    // ── 联机 ──
    bool NetBeginChannel(APawn* Caster,const FAbsoluteZeroCast& Spell);
    void NetCancelChannel();
    bool NetCommitNova(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow,const FAbsoluteZeroCast& Spell);
    void NetCastAccepted(uint8 Phase);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    TArray<TWeakObjectPtr<AFPSAbsoluteZeroNova>> ActiveNovas;
    FAbsoluteZeroCast CastSnapshot;
    FFPSLeftHandNotice HandNotice;
    FString Message;
    double MessageUntil=0.;

    UPROPERTY(ReplicatedUsing=OnRep_Channel) bool bNetChanneling=false;
    UPROPERTY(Replicated) float NetChannelDuration=.75f;
    UPROPERTY(Replicated) float NetChannelReduction=.35f;
    UPROPERTY(Replicated) bool bNetArmorSynergy=false;
    UPROPERTY(Replicated) float NetSigilColorSeed=0.f;
    UFUNCTION() void OnRep_Channel();

    UPROPERTY(Transient) TObjectPtr<UDynamicMeshComponent> ChannelSigil;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> ChannelMID;
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> ChannelMist;
    UPROPERTY(Transient) TObjectPtr<UPointLightComponent> ChannelLight;

    FStaffCastPose StaffSlamEntry;
    FVector CachedChannelGround=FVector::ZeroVector;
    FVector CachedChannelOwnerPos=FVector::ZeroVector;
    double NetWaitSince=0.;
    bool bQueued=false,bCommitted=false,bChanneling=false,bAssetsReady=false,bHasCachedGround=false;
    bool bNetPaid=false,bNetPrepared=false,bNetAwaitingRelease=false,bNetAwaitingCancel=false;
    float PaidMana=0.f,ChannelAge=0.f,ChannelDuration=.75f,ActiveDamageReduction=0.f,SlamRecoveryAge=-1.f,SigilColorSeed=0.f;

    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool InputAvailable(bool bContinuing=false) const;
    bool Allowed(const FAbsoluteZeroCast& Spell,FString& Failure) const;
    void ServiceQueue();
    void OnGestureContact();
    void ReleaseNova();
    void CompleteRelease();
    void StartChannelVisuals();
    void UpdateChannelVisuals(float Delta);
    void ClearChannelVisuals();
    void UpdateTickState();
    void Feedback(const FString& Text);
    FVector GroundPointBeneathCaster() const;
};
