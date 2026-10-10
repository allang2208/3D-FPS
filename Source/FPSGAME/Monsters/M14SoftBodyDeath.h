#pragma once
#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Components/ActorComponent.h"
#include "Engine/AssetUserData.h"
#include "M14SoftBodyDeath.generated.h"

class USkeletalMesh;
class USkeleton;
class USkeletalMeshComponent;
class UPoseableMeshComponent;

USTRUCT()
struct FM14SoftNode
{
    GENERATED_BODY()
    UPROPERTY() FVector Rest=FVector::ZeroVector; // Mesh-local centimetres.
    UPROPERTY() TArray<int32> SourceBones;
    UPROPERTY() TArray<float> SourceWeights;
    UPROPERTY() int32 RenderBone=INDEX_NONE;
};
USTRUCT()
struct FM14SoftEdge
{
    GENERATED_BODY()
    UPROPERTY() int32 A=0;
    UPROPERTY() int32 B=0;
    UPROPERTY() uint8 Kind=0; // Tissue, legacy rigid frame, legacy attachment, reinforced tissue.
};
USTRUCT()
struct FM14SoftTet
{
    GENERATED_BODY()
    UPROPERTY() TArray<int32> Nodes;
};
USTRUCT()
struct FM14RigidPatch
{
    GENERATED_BODY()
    UPROPERTY() TArray<int32> Nodes;
    UPROPERTY() FVector Center=FVector::ZeroVector;
    UPROPERTY() TArray<FVector> SupportOffsets;
    UPROPERTY() int32 RenderBone=INDEX_NONE;
    UPROPERTY() int32 SourceBone=INDEX_NONE;
};

/** Cooked proxy and binding. The original live mesh and its animation rig stay intact. */
UCLASS(BlueprintType)
class FPSGAME_API UM14SoftBodyData : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="M14|Proxy") TObjectPtr<USkeletalMesh> CorpseMesh;
    UPROPERTY() TArray<FM14SoftNode> Nodes;
    UPROPERTY() TArray<FM14SoftEdge> Edges;
    UPROPERTY() TArray<FM14SoftTet> Tets;
    UPROPERTY() TArray<FM14RigidPatch> Hardware;
    UPROPERTY() TArray<FName> SourceBoneNames;
    UPROPERTY() TArray<FTransform> SourceRefFrames;
    UPROPERTY() int32 SoftNodeCount=0;
    UPROPERTY() float SpacingCm=24.f;
    /** No authored shove, locomotion drift or temporary foot anchors. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Monster|Corpse") bool bCollapseInPlace=false;
    /** Appendage nodes whose tissue must not act as a compressive support strut. */
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Monster|Corpse") TArray<int32> UnsupportedNodes;
    UFUNCTION(BlueprintCallable,Category="M14|Authoring")
    static bool BuildCorpse(USkeletalMesh* Mesh,USkeleton* CorpseSkeleton,UM14SoftBodyData* Data,const FString& CageFile,const FString& EmbeddingFile);
    UFUNCTION(BlueprintCallable,Category="Monster|Corpse Authoring")
    static bool ExportSurface(USkeletalMesh* Mesh,const FString& File,const TArray<FName>& OmitBranches);
    UFUNCTION(BlueprintCallable,Category="Monster|Corpse Authoring")
    static void BindToLivingMesh(USkeletalMesh* Mesh,UM14SoftBodyData* Data);
};

/** Per-mesh cooked death binding, shared by every character/skin using this mesh. */
UCLASS()
class FPSGAME_API UMonsterSoftCorpseBinding : public UAssetUserData
{
    GENERATED_BODY()
public:
    UPROPERTY() TObjectPtr<UM14SoftBodyData> Data;
};

/** Shared continuous corpse solver. M14 or the corpse component owns its clock. */
UCLASS()
class FPSGAME_API UM14SoftBodyDeathComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    bool Start(USkeletalMeshComponent* LivingMesh,UM14SoftBodyData* InData,const FVector& InheritedVelocity);
    bool Advance(float Dt);
    bool IsActive() const { return Data!=nullptr; }
    int32 SimulatedBodyCount() const { return 32; } // Shared-budget cost reservation, not tetrahedron count.
    bool CanReleaseCorpseBudget() const { return bSettled||QuietSeconds>.2f; }
    void FreezeForBudget();
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
private:
    void Substep(float Dt);
    void RefreshContact(int32 Index);
    void ProjectContacts();
    void LimitSurfaceStrain();
    void DampInternalVelocity(float Dt);
    void ProjectHardware();
    void SelfContacts();
    void UpdateMesh();
    void ReleaseBudget();
    FVector ToWorld(const FVector& P) const { return Origin+P*100.; }
    FVector ToSimulation(const FVector& P) const { return (P-Origin)*.01; }
    UPROPERTY(Transient) TObjectPtr<UM14SoftBodyData> Data;
    UPROPERTY(Transient) TObjectPtr<UPoseableMeshComponent> Display;
    TArray<FVector> Positions,Previous,Velocities,PredictedVelocities,Initial,GroundPoint,GroundNormal,TracePosition,WallPoint,WallNormal;
    TArray<float> InvMass,Lengths,Volumes,EdgeLambda,VolumeLambda,BarrierLambda;
    TArray<FQuat> HardwareRotation;
    TArray<FTransform> BindFrames;
    TArray<FIntPoint> SelfContactPairs;
    TArray<uint8> Grounded;
    TArray<uint8> RelaxedEdges,RelaxedTets;
    FVector Origin=FVector::ZeroVector;
    FTransform MeshToWorld;
    float Accumulator=0.f,Elapsed=0.f,QuietSeconds=0.f,BudgetRetry=0.f;
    int32 ContactCursor=0;
    bool bSettled=false,bBudget=false;
    float WorldSpacingCm=24.f;
};
