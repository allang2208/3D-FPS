#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "BlizzardTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSBlizzardComponent.generated.h"
class UColdSteelStatusModel;
class UFPSFireballComponent;
class AFPSBlizzardZone;
class UNiagaraComponent;
class UDecalComponent;
class UMaterialInstanceDynamic;
struct FStreamableHandle;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSBlizzardComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSBlizzardComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger();
    void CancelPending();
    void InterruptPending(bool bCancelCloud);
    void SuspendPreview();
    void SetAimPreview(bool bActive);
    void ReleaseAimPreview();
    bool IsAimPreviewActive() const{return bAimPreview;}
    bool IsPrepared() const{return bCommitted&&bGathered&&!bReleaseRequested;}
    bool HasQueuedAction() const{return bQueued||bReleaseRequested;}
    bool HasUnreleasedCast() const{return bCommitted;}
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    // ── 联机 ──
    bool NetCommitZone(APawn* Caster,const struct FColdSteelNetCastRequest& Req,UColdSteelStatusModel* Shadow);
    void NetCastRejected(uint8 Phase,uint8 Code);
    void NetCastCancelled(uint8 Phase);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UObject>> Assets;
    TSharedPtr<FStreamableHandle> AssetLoad;
    TArray<TWeakObjectPtr<AFPSBlizzardZone>> Zones;
    FBlizzardCast CastSnapshot;
    FVector LockedPoint=FVector::ZeroVector,LockedNormal=FVector::UpVector,LockedAxis=FVector::ForwardVector;
    FFPSLeftHandNotice HandNotice;
    FString Message;
    double MessageUntil=0;
    bool bQueued=false,bCommitted=false,bAssetsReady=false;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    bool InputAvailable() const;
    bool Allowed(const FBlizzardCast& Spell,FString& Failure) const;
    bool SelectGround(const FBlizzardCast& Spell,FString& Failure);
    void ServiceQueue();
    void ReleaseAtContact();
    void Feedback(const FString& Text);
    void ClearZones();
    void Gathered();
    void UpdateGatherCloud();
    void RefreshPreview();
    FVector CloudOrigin() const;
    // Append runtime/reflected state; ordinary rebuild required for loaded instances.
    UPROPERTY(Transient) TObjectPtr<UNiagaraComponent> GatherFX;
    UPROPERTY(Transient) TObjectPtr<UDecalComponent> AimDecal;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> AimMID;
    bool bGathered=false,bReleaseRequested=false,bAimPreview=false,bPreviewValid=false,bStaffCloud=false;
    float PaidMana=0,PreparedAge=0,PreviewAge=0;
    /** 联机客人：本地扣账已发生、等待服务端区复制的窗口。 */
    bool bNetPaid=false;
    double NetPaidAt=-100.0;
    FString PreviewFailure;
};
