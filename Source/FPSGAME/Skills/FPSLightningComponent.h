#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "LightningTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSLightningComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class UNiagaraSystem;
class USoundBase;
class AFPSLightningArc;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSLightningComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSLightningComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger();
    void Cancel();
    void InterruptPending();
    bool HasQueuedAction() const{return bQueued;}
    bool HasUnreleasedCast() const{return bCommitted;}
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    // ── 联机 ──
    bool NetRelease(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ArcSystem;
    UPROPERTY(Transient) TArray<TObjectPtr<USoundBase>> CastSounds;
    TArray<TWeakObjectPtr<AFPSLightningArc>> Arcs;
    TWeakObjectPtr<AActor> LockedTarget;
    FLightningCast CastSnapshot;
    FFPSLeftHandNotice HandNotice;
    bool bQueued=false,bCommitted=false;
    /** 联机客人：扣账后等待服务端结算的窗口。 */
    bool bNetPaid=false;
    FString Message;
    double MessageUntil=0;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool IsTarget(AActor* Target) const;
    bool VisibleFrom(AActor* Origin,AActor* Target,const FVector& Start) const;
    AActor* SelectTarget(const FLightningCast& Spell,FString& Failure) const;
    void ServiceQueue();
    void ReleaseAtContact();
    /** 链式结算主体：本地释放与服务端权威释放共用——Model/起点可换。 */
    void RunChain(APawn* Player,UColdSteelStatusModel* M,AActor* First,const FVector& Start,FLightningRewards& Rewards);
    void SpawnArc(const FVector& Start,const FVector& End,float Width=1.f,bool bOverload=false);
    void Overload(AActor* Origin,FLightningRewards& Rewards);
    void Feedback(const FString& Text);
    void RejectHeldHand();
};
