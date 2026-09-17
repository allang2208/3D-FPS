#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSLeftHandNotice.h"
#include "FPSIceSpikeComponent.generated.h"
class AFPSIceSpikeVolley;
class UStaticMesh;
class UMaterialInterface;
class UParticleSystem;
class USoundBase;
class UNiagaraSystem;
class UColdSteelStatusModel;
class UFPSFireballComponent;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSIceSpikeComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSIceSpikeComponent();
    UFUNCTION(BlueprintCallable,Category="Skills") void Trigger();
    FString StatusText() const;
    // UI pulse for a request that is rejected instead of queued (see FPSLeftHandNotice.h).
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    float CooldownFraction() const;
    int32 ActiveCount() const;
    bool IsPrepared() const;
    bool HasQueuedAction() const {return bQueuedGather||bQueuedRelease;}
    void VolleyFinished(AFPSIceSpikeVolley* Volley);
    /** Hold the bound key while the group hovers: red trajectory preview until the release. */
    void SetAimPreview(bool bActive);
    bool IsAimPreviewActive() const {return bAimPreview;}
    void Cancel();
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> SpikeMeshes;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> ShardMesh;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> IceMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> IceShellMaterial;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> ImpactFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ImpactSound;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> Motes;
    UPROPERTY(Transient) TObjectPtr<UNiagaraSystem> ColdMist;
    TWeakObjectPtr<AFPSIceSpikeVolley> Active;
    bool bQueuedGather=false,bQueuedRelease=false;
    bool bAimPreview=false;
    FString Message;
    double MessageUntil=0;
    FFPSLeftHandNotice HandNotice;
    void ServiceQueue();
    void LaunchAtContact();
    void Feedback(const FString& Text);
    void RejectHeldLeftHand();
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
};
