#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "IceWallTypes.h"
#include "FPSLeftHandNotice.h"
#include "FPSIceWallComponent.generated.h"

class AFPSIceWall;
class UFPSFireballComponent;
class UColdSteelStatusModel;
class UStaticMesh;
class UMaterialInterface;
class UParticleSystem;
class USoundBase;

UCLASS(ClassGroup=(Skills),meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSIceWallComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSIceWallComponent();
    UFUNCTION(BlueprintCallable,Category="Skills|IceWall") void Trigger();
    bool IsPrepared() const { return Seed.IsValid()&&bGathered&&!bReleaseRequested; }
    bool HasQueuedAction() const { return bQueuedGather||bReleaseRequested; }
    bool IsPlacementActive() const;
    bool ToggleShape();
    void SuspendPreview();
    void InterruptPending(bool bCancelSeed);
    void Cancel();
    FString StatusText() const;
    float CooldownFraction() const;
    bool IsHandOccupiedNotice() const;
    float HandNoticeAlpha() const;
    float HandNoticeRise() const;
    bool ValidatePlacement(const FIceWallPlacement& Placement,const FIceWallCast& Cast,bool bAllowEnemies,FString& Reason) const;
    void WallEnded(AFPSIceWall* Wall);
protected:
    virtual void BeginPlay() override;
    virtual void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick) override;
    virtual void EndPlay(EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TArray<TObjectPtr<UStaticMesh>> BlockMeshes;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> IceMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInterface> PreviewMaterial;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> BreakFX;
    UPROPERTY(Transient) TObjectPtr<USoundBase> BreakSound;
    UPROPERTY(Transient) TObjectPtr<USoundBase> CastSound;
    TWeakObjectPtr<AFPSIceWall> Seed,Preview;
    TArray<TWeakObjectPtr<AFPSIceWall>> ReleasedWalls;
    FIceWallPlacement Displayed,Committed;
    EIceWallShape Shape=EIceWallShape::High;
    bool bQueuedGather=false,bGathered=false,bReleaseRequested=false;
    float PaidMana=0,PreparedAge=0,PreviewAge=0;
    FString Message;
    double MessageUntil=0;
    FFPSLeftHandNotice HandNotice;
    void ServiceQueue();
    void Gathered();
    void LaunchAtContact();
    void UpdatePreview();
    void Feedback(const FString& Text);
    void RejectHeldHand();
    bool InputAvailable() const;
    FVector SeedOrigin() const;
    UColdSteelStatusModel* Model() const;
    UFPSFireballComponent* Hands() const;
    AFPSIceWall* SpawnWall(bool bGhost,const FIceWallCast& Cast);
};
