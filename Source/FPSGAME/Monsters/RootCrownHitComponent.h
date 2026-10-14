#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "RootCrownHitComponent.generated.h"

class ARootCrownRigPreview;

struct FRootCrownHitHull
{
    FName Bone;
    FTransform Local=FTransform::Identity;
    TArray<FPlane> Planes;
};
struct FRootCrownHitPose
{
    double At=0.;
    FVector CapsuleCenter=FVector::ZeroVector;
    TArray<FTransform> Frames;
};

/** Authority-only bounded anatomical history for the existing remote weapon contact RPC. */
UCLASS()
class FPSGAME_API URootCrownHitComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    URootCrownHitComponent();
    void InitializeSurface();
    virtual void TickComponent(float Dt,ELevelTick Type,FActorComponentTickFunction* Function) override;
    bool ResolveRemoteContact(const FVector& Start,const FVector& Point,double At,bool Melee,FName ReportedComponent,FHitResult& Out) const;
private:
    bool ResolveAt(const FVector& Start,const FVector& Point,double At,bool Melee,bool CapsuleContact,FHitResult& Out) const;
    TWeakObjectPtr<ARootCrownRigPreview> Crown;
    TArray<FRootCrownHitHull> Hulls;
    TArray<FRootCrownHitPose> History;
};
