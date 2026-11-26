#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "SmithSignMotion.generated.h"

class UStaticMeshComponent;

// Two parallel chains share their hinge axis. Only the links and the hanging load move.
UCLASS()
class USmithSignMotion : public UActorComponent
{
    GENERATED_BODY()
public:
    USmithSignMotion();
    static void BindToAssembly(AActor& Assembly);
    void Mount(UStaticMeshComponent& ChainPair, UStaticMeshComponent& Sign);
    virtual void TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void UpdateRange();
    void Pose(float Chain,float Panel);
    TWeakObjectPtr<UStaticMeshComponent> Links,Board;
    FTransform ChainRest,BoardRest;
    FTimerHandle RangeTimer;
    float Angle=0.f,Speed=0.f,LinkAngle=0.f,LinkSpeed=0.f;
    float WindClock=0.f,Target=0.f,DistanceWeight=0.f;
    float GustPhase=0.f;
    bool bDetailed=false;
};
