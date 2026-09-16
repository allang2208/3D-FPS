#include "VoxelBuildPrefabActor.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"

AVoxelBuildPrefabActor::AVoxelBuildPrefabActor()
{
    PrimaryActorTick.bCanEverTick=false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("PrefabRoot")));
    MeshComponent=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("PrefabMesh"));
    MeshComponent->SetupAttachment(GetRootComponent());
    MeshComponent->SetMobility(EComponentMobility::Movable);
    MeshComponent->SetCollisionProfileName(TEXT("BlockAll"));
    MeshComponent->SetCollisionObjectType(ECC_WorldDynamic);
    MeshComponent->SetCanEverAffectNavigation(false);
}

FIntVector AVoxelBuildPrefabActor::RotatedFootprint(FIntVector Footprint,int32 QuarterTurns)
{
    const int32 Turns=((QuarterTurns%4)+4)%4;
    return (Turns%2)?FIntVector(Footprint.Y,Footprint.X,Footprint.Z):Footprint;
}

FTransform AVoxelBuildPrefabActor::ComputeTransform(const FVoxelBuildPrefab& Definition,UStaticMesh* Mesh,FIntVector Cell,int32 QuarterTurns)
{
    const FIntVector Size=RotatedFootprint(Definition.Footprint,QuarterTurns);
    const FVector SizeCm=FVector(Size)*20.;
    const FQuat Rotation(FRotator(0.,(((QuarterTurns%4)+4)%4)*90.,0.));
    const FVector BoundsOrigin=Mesh?Mesh->GetBounds().Origin:FVector::ZeroVector;
    const FVector Location=FVector(Cell)*20.+SizeCm*.5-Rotation.RotateVector(BoundsOrigin)+Definition.PivotOffsetCm;
    return FTransform(Rotation,Location);
}

void AVoxelBuildPrefabActor::Configure(FName InId,FIntVector InCell,int32 InYaw,UStaticMesh* Mesh,UMaterialInterface* Surface,UPhysicalMaterial* Contact)
{
    Id=InId;Cell=InCell;QuarterTurns=InYaw;
    if(!MeshComponent)return;
    MeshComponent->SetStaticMesh(Mesh);
    if(Surface)MeshComponent->SetMaterial(0,Surface);
    if(Contact)MeshComponent->SetPhysMaterialOverride(Contact);
    Tags.AddUnique(TEXT("VoxelBuildPrefab"));
}
