#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/NetSerialization.h"
#include "HorseRosterTypes.h"
#include "HorseRiderComponent.generated.h"

class AController;
class AStableRidingHorse;
class AFPSGAMECharacter;
class USkeletalMeshComponent;
class UAnimSequence;
class USkeletalMesh;
struct FMinimalViewInfo;

UENUM()
enum class ERiderPhase : uint8 { OnFoot, Mounting, Seated, Dismounting };

USTRUCT()
struct FHorseRideState
{
    GENERATED_BODY()
    UPROPERTY() TObjectPtr<AStableRidingHorse> Horse;
    UPROPERTY() ERiderPhase Phase=ERiderPhase::OnFoot;
    UPROPERTY() float Since=0;
    UPROPERTY() bool bFromRight=false;
    UPROPERTY() bool bLeapExit=false;
    UPROPERTY() FVector_NetQuantize10 ThrowVelocity=FVector::ZeroVector;
    UPROPERTY() FTransform Start;
    UPROPERTY() FVector Ground=FVector::ZeroVector;
};

UCLASS()
class FPSGAME_API UHorseRiderComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UHorseRiderComponent();
    void BeginPlay() override;
    void EndPlay(EEndPlayReason::Type Reason) override;
    void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& Props) const override;
    void TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Fn) override;
    bool Active() const { return State.Phase!=ERiderPhase::OnFoot; }
    bool Transferring() const { return State.Phase==ERiderPhase::Mounting||State.Phase==ERiderPhase::Dismounting; }
    static bool IsRiding(const AActor* Actor);
    static AStableRidingHorse* MountOf(const AActor* Actor);
    static bool UsesSaddleHands(const AActor* Actor);
    bool PressUse(AStableRidingHorse* Horse);
    bool ReleaseUse();
    void RequestHorseJump();
    void ToggleOwnedHorse();
    UFUNCTION(Client,Reliable) void ClientMountRoster(FGuid Profile,const FStableMountRoster& Roster);
    UFUNCTION(Server,Reliable) void ServerSelectMount(FGuid Id);
    UFUNCTION(Client,Reliable) void ClientHorseNotice(const FString& Message);
    UFUNCTION(Client,Reliable) void ClientHorseClock(int64 UtcTicks,double ServerSeconds);
    UFUNCTION(Server,Reliable) void ServerRequestHorseClock();
    int64 HorseUtcNow() const;
    bool MayUseResident(AStableRidingHorse& Horse);
    AStableRidingHorse* GetOwnedHorse() const {return OwnedHorse.Get();}
    FVector SeatedViewOffset() const { return State.Phase==ERiderPhase::Seated?EyeInertia*GaitViewScale:FVector::ZeroVector; }
    void SetForward(float Value) { Axes.Y=Value; }
    void SetTurn(float Value) { Axes.X=Value; }
    void SetCanter(bool Value) { bCanter=Value; }
    float EyeHeightOffset() const;
    FVector SaddleViewCorrection() const { return State.Phase==ERiderPhase::Seated?ViewSeatCorrection:FVector::ZeroVector; }
    static bool IsCantering(const AActor* Actor);
    static bool IsSeated(const AActor* Actor);
    FRotator CanterCameraRotation() const { return CanterRotation*GaitViewScale; }
    void LeaveSeatForLeap();
    void ThrowFromHorse(AStableRidingHorse& Horse);
    AStableRidingHorse* GetMount() const { return State.Horse.Get(); }
    AStableRidingHorse* NearbyForDisplay();
    void ApplyPose(USkeletalMeshComponent& Mesh,TArray<FTransform>& Bones);
    UAnimSequence* FixedTransferFor(const USkeletalMesh* Asset);
    float SeatProgress() const { return MountAmount(); }
    float TransferSeconds() const { return FMath::Max(0.f, Clock()-State.Since); }
    bool IsMounting() const { return State.Phase==ERiderPhase::Mounting; }
private:
    double NextNearbyScan=0.;
    TWeakObjectPtr<AStableRidingHorse> NearbyHorse;
    friend class UHorseTransferFramesCommandlet;
    friend class UHorseGroundContactReviewCommandlet;
    friend struct FHorseNetworkReview;
    static FString TransferPackage(bool Female,bool Right,bool Mount);
    UAnimSequence* LoadTransfer(const USkeletalMesh* Asset,bool Right,bool Mount);
    void BuildContactPose(USkeletalMeshComponent& Mesh,TArray<FTransform>& Bones);
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> TransferClip;
    TWeakObjectPtr<const USkeletalMesh> TransferBody;
    bool bClipFromRight=false,bClipMount=false;
    FRotator RiderFacing(float Progress) const;
    UPROPERTY(ReplicatedUsing=ApplyState) FHorseRideState State;
    UFUNCTION() void ApplyState();
    UFUNCTION(Server,Reliable) void ServerUse(AStableRidingHorse* Target,bool bHold);
    UFUNCTION(Server,Reliable) void ServerDrive(AStableRidingHorse* Target,int8 Forward,int8 Turn,bool Fast);
    UPROPERTY(Replicated) TObjectPtr<AStableRidingHorse> OwnedHorse;
    TWeakObjectPtr<AStableRidingHorse> DismissAfterDismount;
    double NextHorseCall=0.;
    bool ClaimHorse(AStableRidingHorse& Horse);
    bool FindRecallSpot(FVector Eye,FRotator Look,float HalfVerticalFov,const AStableRidingHorse* Existing,FTransform& Out) const;
    UFUNCTION(Server,Reliable) void ServerToggleMount(FVector_NetQuantize Eye,FRotator Look,float HalfVerticalFov);
    int64 ServerUtcSample=0;
    double ClockSampleSeconds=0.;
    UFUNCTION(Server,Reliable) void ServerHorseJump(AStableRidingHorse* Target);
    TWeakObjectPtr<AFPSGAMECharacter> Player;
    TWeakObjectPtr<AStableRidingHorse> AppliedHorse,DepartedHorse;
    TWeakObjectPtr<AController> InputOwner;
    TWeakObjectPtr<AStableRidingHorse> PressedHorse,LedHorse;
    FTimerHandle HoldTimer;
    bool bUsePressed=false,bHoldHandled=false;
    bool bAwaitingHorseImpact=false;
    double UseStarted=0.;
    void HandleHold();
    bool CanCompleteUse() const;
    bool bApplied=false,bSavedControllerYaw=true,bCanter=false,bLastCanter=false;
    FVector2D Axes=FVector2D::ZeroVector;
    FIntPoint LastDrive=FIntPoint::ZeroValue;
    float LastHeading=0,EyeBob=0,EntryYawTravel=0,AppliedEntryYaw=0;
    FRotator CanterRotation=FRotator::ZeroRotator;
    static constexpr float GaitViewScale=.7f;
    FVector EyeInertia=FVector::ZeroVector;
    TWeakObjectPtr<AStableRidingHorse> ViewSeatHorse;
    FVector RestSeatLocal=FVector::ZeroVector;
    FVector ViewSeatCorrection=FVector::ZeroVector;
    float ViewStrideWeight=0.f;
    float SeatCompression=0.f;
    float CanterEnvelope=0.f;
    TWeakObjectPtr<class USkeletalMesh> PoseAsset;
    TArray<FTransform> ReferenceCS;
    TBitArray<> SaddleLegBones;
    TMap<int32,FQuat> GripLocalTurns;
    AStableRidingHorse* Focus() const;
    bool SideSpot(const AStableRidingHorse& Horse,FVector& Out,bool bRight,bool bCheckApproach) const;
    bool ClearGround(const AStableRidingHorse& Horse,const FVector& Position) const;
    float Clock() const;
    float MountAmount() const;
    FVector RiderRoot(float Progress) const;
    void SetPhase(ERiderPhase Phase);
    void Release();
    void UpdateInput();
};
