#pragma once

#include "CoreMinimal.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "FPSMeleeMoveRequest.h"
#include "FPSCharacterMovementComponent.generated.h"

/**
 * 联机移动意图位（sprint/ADS 走速档 + 滑铲态）随移动包同帧传输：客户端在 SavedMove 的
 * CompressedFlags 里打包，服务端在 UpdateFromCompressedFlags 里解包——两端用同一份
 * MaxWalkSpeed/摩擦依据，不再走独立 RPC（时序天然错开）。
 */
class FSavedMove_FPSCharacter : public FSavedMove_Character
{
public:
    typedef FSavedMove_Character Super;
    FSavedMove_FPSCharacter();
    virtual void Clear() override;
    virtual uint8 GetCompressedFlags() const override;
    virtual void SetMoveFor(ACharacter* InCharacter, float InDeltaTime, FVector const& NewAccel, class FNetworkPredictionData_Client_Character& ClientData) override;
    virtual void PrepMoveFor(ACharacter* InCharacter) override;
    virtual bool CanCombineWith(const FSavedMovePtr& NewMove, ACharacter* InCharacter, float MaxDelta) const override;
    virtual bool IsImportantMove(const FSavedMovePtr& LastAckedMove) const override;
    uint32 DodgeSequence=0;
    FVector DodgeRequestDirection=FVector::ZeroVector;
    float DodgeRequestTime=0.f;
    FFPSMeleeMoveRequest MeleeRequest;
    float MeleeStep=0.f;
    bool bMeleeMomentumStart=false,bSavedMeleeMomentum=false;
    float SavedSlideAge=0.f,SavedSlideRemaining=0.f;
    bool bSavedSlideDownhill=false;
    uint32 SlideJumpSequence=0;
    bool bSlideJumpStart=false;

private:
    uint8 bSavedWantsToSprint : 1;
    uint8 bSavedWantsToAim : 1;
    uint8 bSavedWantsToSlide : 1;
    uint8 bSavedWantsToMount : 1;
};

class FNetworkPredictionData_Client_FPSCharacter : public FNetworkPredictionData_Client_Character
{
public:
    typedef FNetworkPredictionData_Client_Character Super;
    FNetworkPredictionData_Client_FPSCharacter(const UCharacterMovementComponent& ClientMovement);
    virtual FSavedMovePtr AllocateNewMove() override;
};

struct FFPSNetworkMoveData : FCharacterNetworkMoveData
{
    using Super=FCharacterNetworkMoveData;
    uint32 DodgeSequence=0;
    FVector_NetQuantizeNormal DodgeDirection=FVector::ZeroVector;
    float DodgeStartedAt=0.f;
    FFPSMeleeMoveRequest MeleeRequest;
    float ReplayMeleeStep=0.f;
    bool bReplayMeleeMomentumStart=false;
    uint32 SlideJumpSequence=0;
    bool bReplaySlideJump=false;
    virtual void ClientFillNetworkMoveData(const FSavedMove_Character& Move,ENetworkMoveType Type) override;
    virtual bool Serialize(UCharacterMovementComponent& Movement,FArchive& Ar,UPackageMap* Map,ENetworkMoveType Type) override;
};
struct FFPSNetworkMoveDataContainer : FCharacterNetworkMoveDataContainer
{
    FFPSNetworkMoveData Moves[3];
    FFPSNetworkMoveDataContainer(){NewMoveData=&Moves[0];PendingMoveData=&Moves[1];OldMoveData=&Moves[2];}
};

/** Native swept walking, with local first-person compensation for discrete stair corrections. */
UCLASS()
class FPSGAME_API UFPSCharacterMovementComponent : public UCharacterMovementComponent
{
    GENERATED_BODY()
public:
    UFPSCharacterMovementComponent();
    virtual float GetMaxSpeed() const override;

    /** 客户端写入（本机控制 pawn）：随压缩标志进 ServerMove；服务端 UpdateFromCompressedFlags 读回。
     *  本地与服务端都直接读这个字段算 MaxWalkSpeed，同源不分叉。 */
    uint8 bWantsToSprint : 1;
    uint8 bWantsToAim : 1;
    /** 滑铲状态位（镜像角色 bIsSliding）：服务端副本按它启停同一套滑铲物理。 */
    uint8 bWantsToSlide : 1;
    /** Restrictive movement intent only; support approval and weapon bonuses remain server-owned. */
    uint8 bWantsToMount : 1;
    bool IsBipodMovementLocked() const;
    virtual void UpdateFromCompressedFlags(uint8 Flags) override;
    virtual class FNetworkPredictionData_Client* GetPredictionData_Client() const override;

    void SetStairVisualRoot(USceneComponent* InRoot) { StairVisualRoot = InRoot; }

    // Predicted dodge intent travels with the move that starts the root motion.
    bool StartDodge(const FVector& Direction, float DistanceCM, float DurationSeconds);
    void QueueDodgeRequest(const FVector& Direction);
    uint32 DodgeRequestSequence=0;
    FVector DodgeRequestDirection=FVector::ZeroVector;
    float DodgeRequestTime=0.f;
    virtual void MoveAutonomous(float ClientTimeStamp,float DeltaTime,uint8 CompressedFlags,const FVector& NewAccel) override;
    virtual void PerformMovement(float DeltaSeconds) override;
    void CancelDodge();
    bool IsDodging() const;
    // Server-issued displacement participates in native movement correction/replay.
    void ApplyImpactPush(const FVector& Direction,float DistanceCM);
    bool HasImpactPush() const;
    virtual float SlideAlongSurface(const FVector& Delta,float Time,const FVector& Normal,FHitResult& Hit,bool bHandleImpact=true) override;
    float GetDodgeProgress() const;
    FVector GetDodgeDirection() const { return DodgeDirection; }

    // One grounded capsule sweep, with no residual velocity. Returns actual displacement.
    FVector ApplyMeleeLungeStep(const FVector& Direction, float DistanceCM);
    void BeginMeleeLungeRequest(EFPSMeleeMove Kind,const FVector& Direction);
    void RecordMeleeLungeStep(float Distance);
    bool IsMeleeLungeRejected() const {return RejectedMeleeSequence!=0&&RejectedMeleeSequence==MeleeRequest.Sequence;}
    FFPSMeleeMoveRequest MeleeRequest;
    float PendingMeleeStep=0.f;
    bool bPendingMeleeMomentum=false;
    bool HasMeleeDashMomentum() const {return bMeleeDashMomentum;}
    void RestoreMeleeDashMomentum(bool Active){bMeleeDashMomentum=Active;}
    void QueueSlideJumpRequest();
    uint32 SlideJumpRequestSequence=0;
    bool bPendingSlideJump=false;

    // Carry a released airborne dash through native collision and landing.
    // Local single-player action; horizontal speed decays until rest or new input.
    bool BeginMeleeDashMomentum(const FVector& IncomingVelocity);
    virtual void CalcVelocity(float DeltaTime, float Friction, bool bFluid, float BrakingDeceleration) override;
    virtual void StopMovementImmediately() override;

    // Centimetres per second; constant interpolation has no spring or exponential tail.
    UPROPERTY(EditDefaultsOnly, Category="Movement|Stairs", meta=(ClampMin="1", Units="cm/s"))
    float StairVisualSpeed = 220.f;

    UPROPERTY(EditDefaultsOnly, Category="Movement|Stairs", meta=(ClampMin="0"))
    float StairSpeedToWalkSpeed = .75f;

    float GetStairVisualOffset() const { return StairVisualOffset; }
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual bool StepUp(const FVector& GravDir, const FVector& Delta, const FHitResult& Hit, FStepDownResult* OutStepDownResult = nullptr) override;
    virtual void AdjustFloorHeight() override;
    virtual void OnTeleported() override;
    virtual bool DoJump(bool bReplayingMoves, float DeltaTime) override;
    virtual bool IsValidLandingSpot(const FVector& CapsuleLocation, const FHitResult& Hit) const override;

protected:
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    // Accepted native corrections only, also used by third-person monster presentation.
    float GetFrameStairDisplacement() const { return FrameStairDisplacement; }

private:
    FFPSNetworkMoveDataContainer FPSMoveData;
    void StartImpactPush(const FVector& Direction,float DistanceCM,float Age);
    UFUNCTION(Client,Reliable) void ClientImpactPush(FVector_NetQuantizeNormal Direction,float DistanceCM,double StartedAt);
    bool bExecutingImpactPush=false;
    uint32 LastServerDodgeSequence=0;
    uint32 LastServerSlideJumpSequence=0;
    UFUNCTION(Client,Reliable) void ClientRejectDodge(uint32 Sequence);
    void ProcessMeleeNetworkMove(const FFPSNetworkMoveData& Data,bool Authority);
    bool AuthorizeMeleeMove(const FFPSMeleeMoveRequest& Request,float& Budget,float& Recovery) const;
    UFUNCTION(Client,Reliable) void ClientRejectMeleeMove(uint32 Sequence);
    uint32 LastServerMeleeSequence=0,RejectedMeleeSequence=0;
    float ServerMeleeDistance=0.f,ServerMeleeBudget=0.f;
    double ServerMeleeRecoveryUntil=0.;
    bool bServerMeleeBlocked=false;
    void UpdateDodgeState();
    /** 服务端侧最后一次处理远端 move 的真实时刻（UpdateFromCompressedFlags 打点）。 */
    double LastServerMoveAppliedAt = 0.0;
    uint16 DodgeRootMotionId = 0;
    double DodgeStartedAt = 0.0;
    float ActiveDodgeDuration = .3f;
    FVector DodgeDirection = FVector::ZeroVector;
    UPROPERTY(Transient) TObjectPtr<USceneComponent> StairVisualRoot;
    float StairVisualOffset = 0.f;
    float FrameStairDisplacement = 0.f;
    bool bCaptureStairs = false;
    bool bLastFrameSteppedUp = false;
    bool bLeavingStairJump = false;
    bool bMeleeDashMomentum = false;
};
