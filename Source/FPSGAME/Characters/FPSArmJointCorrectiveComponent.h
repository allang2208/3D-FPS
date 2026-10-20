#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "FPSArmJointCorrectiveComponent.generated.h"

class USkeletalMeshComponent;
class USkeletalMesh;

/**
 * Drives pose-space corrective morphs (JC_*) on first-person arm meshes from the evaluated pose.
 * Elbow keys follow the upper/fore-arm angle; wrist keys follow the hand swing measured in the
 * lowerarm_twist_01 frame, so pronation carried by the twist bones never reads as a bend.
 * Grip examples (JC_Grip_<L|R>_<index>_<middle>_<ring>_<pinky>) are a radial basis on the four MCP
 * angles past bind; the example angles are read from the morph name.
 * Only meshes that contain the JC_ morphs are touched; weights take effect at the next pose evaluation.
 * Followers (leader pose) carry no pose of their own: their weights are set on the leader, from the
 * leader's pose, and reach them through the leader's morph-target curves by name.
 * Authoring: SourceAssets/BareSkinV9M4_20261017/correctives.py, grip_correctives.py; rollout in
 * SourceAssets/BareSkinV9Rollout_20261017.
 */
UCLASS(ClassGroup=(Player), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSArmJointCorrectiveComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UFPSArmJointCorrectiveComponent();
    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

private:
    // Cosmetic and local only: a dedicated server never ticks it; on clients and listen servers it only works
    // for the pawn this machine controls or currently views (spectating), not for every remote player.
    bool IsShownLocally() const;
    struct FSide
    {
        int32 Upper=INDEX_NONE,Lower=INDEX_NONE,Hand=INDEX_NONE,Twist=INDEX_NONE,Middle=INDEX_NONE;
        FVector F0=FVector::ForwardVector,R0=FVector::RightVector,Z0=FVector::UpVector;
        float RestElbow=0.f;
        FName Elbow[3],ElbowExtension,Wrist[4];
        // Finger bases (index..pinky): metacarpal, proximal, middle phalanx and the bind angle.
        int32 Meta[4]={INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE},Prox[4]={INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE},Mid[4]={INDEX_NONE,INDEX_NONE,INDEX_NONE,INDEX_NONE};
        float RestMCP[4]={0.f,0.f,0.f,0.f};
        struct FGrip{FName Name;float Extra[4]={0.f,0.f,0.f,0.f};};
        TArray<FGrip> Grips;
        // Pose examples (JC_Pose_<L|R>_<elbow>_<flex>_<dev>_<roll>_<index>_<middle>_<ring>_<pinky>, "m" = minus):
        // radial basis on the whole arm signature, for transitions (reload, melee, inspect) the grips miss.
        // Roll = hand roll about the forearm relative to lowerarm and bind.
        FQuat RelHand=FQuat::Identity;FVector AxisL=FVector::ForwardVector;
        struct FPoseEx{FName Name;float Sig[8]={0.f,0.f,0.f,0.f,0.f,0.f,0.f,0.f};};
        TArray<FPoseEx> Poses;
        bool bValid=false;
    };
    struct FRig
    {
        // Pose source: the mesh itself, or the leader it follows.
        TWeakObjectPtr<USkeletalMeshComponent> Mesh;
        TWeakObjectPtr<const USkeletalMesh> Asset;
        FSide Sides[2];
    };
    void Rescan();
    static bool Build(USkeletalMeshComponent* Mesh,const TArray<const USkeletalMesh*>& Carriers,FRig& Out);
    static void Drive(USkeletalMeshComponent* Mesh,const FSide& Side);
    TArray<FRig> Rigs;
    float RescanTimer=0.f;
};
