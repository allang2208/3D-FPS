#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "DoorPushPoseLayer.h"
#include "FPSDoorPushComponent.generated.h"

class UFPSCastingMeshComponent;
class USkeletalMeshComponent;
struct FStreamableHandle;

/** Sprint into a closed interaction door; one contact owns opening, never damage. */
UCLASS(ClassGroup=(Movement))
class FPSGAME_API UFPSDoorPushComponent : public UActorComponent
{
    GENERATED_BODY()
    friend class UFPSPlayerBodyComponent;
public:
    UFPSDoorPushComponent();
    void Advance(float DeltaSeconds);
    void UpdatePresentation();
    bool IsActive() const {return bActive;}
    float GetPresentationWeight() const;
    void Cancel(bool bCompleted=false);
    bool RequestDoorInteraction(AActor* Target);
    /** 本工程原生门族（平开门/双开门/窗/铁门/键门/拖拽门/滑动门/旋转门）——E 键走服务器权威开关。 */
    static bool IsNativeDoor(AActor* Target);
    /** E 松开：把按下的那扇门在当前角度冻结（拖拽门用，其他门为空操作）。 */
    bool HasPressedDoor() const { return PressedDoor.IsValid(); }
    void ReleasePressedDoor();
    void ApplyHandPose(UFPSCastingMeshComponent& Mesh);
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    UPROPERTY(Transient) TObjectPtr<UFPSCastingMeshComponent> FallbackHands;
    TWeakObjectPtr<UFPSCastingMeshComponent> ActiveHands;
    TWeakObjectPtr<AActor> Door,LastDoor;
    TSharedPtr<FStreamableHandle> Load;
    FDoorPushPoseLayer PoseLayer;
    float Age=0.f,SprintAge=0.f,ProbeAge=0.f;
    bool bActive=false,bContactResolved=false;
    bool CanStart(FString* OutReason=nullptr) const;
    bool Probe(FHitResult& Hit) const;
    bool BeginPush(const FHitResult& Hit);
    void ApplyLoadedHands();
    bool ServerCanInteract(AActor* Target,bool bSprint,FString* OutReason=nullptr) const;
    void AdvanceAuthority(float DeltaSeconds);
    void PlayImpact();
    UFUNCTION(Server,Reliable) void ServerBeginPush(uint16 Sequence,AActor* Target);
    UFUNCTION(Server,Reliable) void ServerContactPush(uint16 Sequence);
    UFUNCTION(Server,Reliable) void ServerCancelPush(uint16 Sequence);
    UFUNCTION(Server,Reliable) void ServerToggleDoor(AActor* Target);
    UFUNCTION(Server,Reliable) void ServerReleaseDoor(AActor* Target);
    UFUNCTION(Client,Reliable) void ClientPushResult(uint16 Sequence,bool bOpened);
    UFUNCTION(NetMulticast,Unreliable) void MulticastPushImpact(FVector_NetQuantize Location);
    uint16 LocalSequence=0,ServerSequence=0;
    TWeakObjectPtr<AActor> ServerDoor,PressedDoor;
    float ServerAge=0.f;
    double LastServerRequest=-1.;
    /** LastDoor 仍抑制即时连发；一次失败的尝试在 SameDoorRetryAt 之后允许同门重试（>服务端 .2s 节流窗）。 */
    double SameDoorRetryAt=0.;
    double LastDebugAt=0.;
    bool bServerContact=false,bAwaitingImpact=false;

};
