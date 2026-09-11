#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSTraversalRules.h"
#include "FPSTraversalComponent.generated.h"

class ACharacter;

USTRUCT(BlueprintType)
struct FPSGAME_API FFPSTraversalTarget
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) EFPSTraversalAction Action = EFPSTraversalAction::None;
    UPROPERTY(BlueprintReadOnly) FFPSTraversalProbe Probe;
    UPROPERTY(BlueprintReadOnly) FVector FrontEdge = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FVector WallNormal = FVector::ForwardVector;
    UPROPERTY(BlueprintReadOnly) FVector Destination = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FVector RaisedStart = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FVector RaisedEnd = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FString Reason;
    UPROPERTY(BlueprintReadOnly) TObjectPtr<UPrimitiveComponent> Obstacle = nullptr;
};

// Owned by the character. Queries only on input and during a pending hold.
UCLASS(ClassGroup=(Movement), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSTraversalComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSTraversalComponent();
    UFUNCTION(BlueprintCallable, Category="FPS|Traversal")
    FFPSTraversalTarget FindTarget(bool bJumpPressed, bool bAvailable) const;
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="FPS|Traversal")
    FFPSTraversalTarget LastJumpTarget;
    void InspectJump(bool bAvailable);
    // Single-player executor. Returns false without consuming jump when unavailable.
    bool TryStart(bool bAvailable);
    bool BeginJumpHold(bool bAvailable);
    bool ReleaseJumpHold(); // True when a short wall press should become a normal jump.
    void AdvanceJumpHold(float DeltaSeconds);
    void Advance(float DeltaSeconds);
    void UpdatePresentation();
    void Cancel();
    UFUNCTION(BlueprintPure, Category="FPS|Traversal") bool IsTraversing() const { return bTraversing; }
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void InitializePresentation();
    void RunRuntimeAudit();
    void Finish(bool bSuccess);
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> VaultClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> MantleClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> ClimbClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> ActiveClip;
    bool bPendingJumpHold = false;
    float JumpHoldElapsed = 0.f;
    TWeakObjectPtr<UPrimitiveComponent> HoldObstacle;
    bool bTraversing = false;
    bool bSavedControllerYaw = true;
    float Elapsed=0.f, Duration=0.f, ClipDuration=0.f, Contact=0.f, Release=0.f;
    FRotator EntryView;
    FVector StartLocation, StartCamera, LastCamera, StartFoot, EdgeCorrection, EndCorrection;
    FVector CameraLocalOffset;
    FVector LastExitLocation=FVector::ZeroVector;
    FQuat Facing;
    FTransform ObstacleTransform;
    bool bRuntimeAudit=false;
    int32 AuditCase=0,AuditStage=0,AuditFailures=0,AuditAmmo=0,AuditFrame=0;
    float AuditAt=0,AuditCaptureAt=-1;
    UPROPERTY(Transient) TObjectPtr<AActor> AuditWall;
    bool bDebugQueries = false;
};
