#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LightningHasteTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSLightningHasteComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class UNiagaraComponent;
class USplineComponent;
class USoundBase;
class USkeletalMeshComponent;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSLightningHasteComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSLightningHasteComponent();
    void Trigger();
    void Cancel();
    void FinishForRemoval();
    void ObserveKill(AActor* Victim);
    bool HasQueuedAction() const{return bQueued;}
    bool HasUnreleasedCast() const{return bCommitted;}
    float Remaining() const;
    float ActionMultiplier() const;
    float MoveMultiplier() const;
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Request,UColdSteelStatusModel* Model,const FLightningHasteCast& Spell);
    void NetCastResult(uint8 Phase,uint8 Code,uint32 CastId);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
private:
    friend class USkillNetworkAuditCommandlet;
    UPROPERTY(ReplicatedUsing=OnRep_State) FLightningHasteState State;
    UFUNCTION() void OnRep_State();
    FLightningHasteState Prediction;
    FLightningHasteCast Pending;
    uint32 LocalCastId=0,ConfirmedCastId=0,RejectedCastId=0,SoundSerial=0;
    bool bQueued=false,bCommitted=false,bAwaiting=false,bVisualWasActive=false;
    float PendingRefund=0;
    double MessageUntil=0,NextArcShapeAt=0;
    FString Message;
    FFPSLeftHandNotice HandNotice;
    TWeakObjectPtr<UColdSteelStatusModel> RewardModel;
    TSet<TWeakObjectPtr<AActor>> CountedVictims;
    int32 Kills=0;
    FLightningHasteCast RewardCast;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ArcSystem;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> EndSound;
    UPROPERTY(Transient) TArray<TObjectPtr<USplineComponent>> ArcPaths;
    UPROPERTY(Transient) TArray<TObjectPtr<UNiagaraComponent>> ArcFX;
    TArray<TWeakObjectPtr<USkeletalMeshComponent>> LimbMeshes;
    TArray<TWeakObjectPtr<USkeletalMeshComponent>> PresentedLimbMeshes;
    TArray<FName> LimbRoots,LimbTips;
    double NextLimbResolveAt=0;
    bool bLastFirstPerson=false;
    void ResolveLimbSources();
    void ClearLimbTickPrerequisites();
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    double Clock() const;
    const FLightningHasteState& View() const;
    void ServiceQueue();
    void Release();
    void Start(const FLightningHasteCast& Spell,uint32 CastId,UColdSteelStatusModel* OwnerModel);
    void End(bool bTrain);
    void RefreshStatus();
    void UpdateVisuals(float Delta=0.f);
    void ClearVisuals();
    void Feedback(const TCHAR* Text);
};
