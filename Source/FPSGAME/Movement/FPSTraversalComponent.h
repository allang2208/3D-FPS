#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSTraversalRules.h"
#include "FPSTraversalComponent.generated.h"

class ACharacter;

USTRUCT(BlueprintType)
struct FPSGAME_API FFPSTraversalHandhold
{
    GENERATED_BODY()
    UPROPERTY(BlueprintReadOnly) FVector Position = FVector::ZeroVector;
    UPROPERTY(BlueprintReadOnly) FVector Normal = FVector::UpVector;
};

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
    UPROPERTY() TArray<TObjectPtr<UPrimitiveComponent>> Supports;
    UPROPERTY(BlueprintReadOnly) TArray<FFPSTraversalHandhold> Handholds;
};

// Owned by the character. Queries on press and while an airborne jump request is held.
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
    bool TryStart(bool bAvailable, bool bLogRejection=true);
    void SetJumpHeld(bool bHeld);
    static bool IsStableSurface(const UPrimitiveComponent* Surface);
    void Advance(float DeltaSeconds);
    void UpdatePresentation(float DeltaSeconds);
    void Cancel();
    UFUNCTION(BlueprintPure, Category="FPS|Traversal") bool IsTraversing() const { return bTraversing; }
    UFUNCTION(BlueprintPure, Category="FPS|Traversal") bool IsCameraRecovering() const { return bReturningCamera; }
    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="FPS|Traversal") bool bLastTraversalSucceeded=false;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void InitializePresentation();
    void RunRuntimeAudit();
    void RunVillageAudit();
    void RunAirAudit();
    void RunBoundaryAudit();
    void TryAirCatch();
    void Finish(bool bSuccess);
    bool IsBlockingSupport(const UPrimitiveComponent* Surface) const;
    FVector SweepCamera(FVector From,FVector To) const;
    void UpdateCameraReturn(float DeltaSeconds);
    UPROPERTY(Transient) TObjectPtr<class USkeletalMeshComponent> Arms;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> VaultClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> MantleClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> ClimbClip;
    UPROPERTY(Transient) TObjectPtr<class UAnimSequence> ActiveClip;
    bool bTraversing = false;
    bool bJumpHeld = false;
    bool bJumpRequestConsumed = false;
    bool bSavedControllerYaw = true;
    bool bReturningCamera=false;
    float CameraReturnSpeed=0.f;
    FVector CameraReturnCapsule=FVector::ZeroVector;
    FQuat LastCameraRotation=FQuat::Identity;
    float Elapsed=0.f, Duration=0.f, ClipDuration=0.f, Contact=0.f, Release=0.f;
    float PlaybackRate=1.f;
    FVector EntryVelocity=FVector::ZeroVector;
    float EntryLiftTangent=0.f;
    FRotator EntryView;
    FVector StartLocation, StartCamera, LastCamera, StartFoot, EdgeCorrection, EndCorrection;
    FVector CameraLocalOffset;
    FVector LastExitLocation=FVector::ZeroVector;
    FQuat Facing;
    FTransform ObstacleTransform;
    TArray<FTransform> SupportTransforms;
    bool bRuntimeAudit=false;
    int32 AuditCase=0,AuditStage=0,AuditFailures=0,AuditAmmo=0,AuditFrame=0;
    float AuditAt=0,AuditCaptureAt=-1;
    TArray<FTransform> AuditVillageStarts;
    FVector AirAuditPreviousCamera=FVector::ZeroVector;
    float AirAuditMaxCameraStep=0.f;
    FVector AuditPreviousCapsule=FVector::ZeroVector;
    float AuditMaxRecoverySpeed=0.f;
    bool bAirAuditStarted=false;
    UPROPERTY(Transient) TObjectPtr<AActor> AuditWall;
    UPROPERTY(Transient) TObjectPtr<AActor> AirAuditRoof;
    bool bDebugQueries = false;
};
