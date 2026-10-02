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
public:
    UFPSDoorPushComponent();
    void Advance(float DeltaSeconds);
    void UpdatePresentation();
    bool IsActive() const {return bActive;}
    float GetPresentationWeight() const;
    void Cancel();
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
    bool CanStart() const;
    bool Probe(FHitResult& Hit) const;
    bool BeginPush(const FHitResult& Hit);
    void ApplyLoadedHands();
};
