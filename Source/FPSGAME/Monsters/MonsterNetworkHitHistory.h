#pragma once
#include "CoreMinimal.h"

class AActor;
class ACharacter;
class USkeletalMeshComponent;
struct FHitResult;

/** Bounded authority pose history for the four spatially classified hit surfaces. */
class FMonsterNetworkHitHistory
{
public:
    static bool Supports(const AActor* Owner);
    explicit FMonsterNetworkHitHistory(ACharacter* Owner);
    void Capture();
    bool Resolve(FHitResult& Hit,double At) const;
private:
    struct FPose
    {
        double At=0.;
        bool bTentacleActive=false;
        TArray<FTransform> Frames;
    };
    struct FHull
    {
        int32 Bone=INDEX_NONE;
        FTransform Local;
        TArray<FPlane> Planes;
    };
    bool PoseAt(double At,FPose& Out) const;
    bool HeartContact(const FHitResult& Hit,const FPose& Pose,FHitResult& Out) const;
    double Clock() const;
    TWeakObjectPtr<ACharacter> Character;
    TWeakObjectPtr<USkeletalMeshComponent> Mesh;
    TArray<FName> Bones;
    TArray<FHull> Hulls;
    TArray<FPose> History;
    double TentacleStartedAt=-1.;
    bool bWasTentacleActive=false;
};
