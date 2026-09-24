#include "VoxelBuildPrefabActor.h"
#include "Engine/World.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
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

bool AVoxelBuildPrefabActor::BeginFall(UStaticMesh* FallbackMesh,float LifeSeconds)
{
    if(MeshComponent&&!MeshComponent->GetStaticMesh()&&FallbackMesh)MeshComponent->SetStaticMesh(FallbackMesh);
    if(!MeshComponent||!MeshComponent->GetStaticMesh())return false;
    MeshComponent->SetMobility(EComponentMobility::Movable);
    MeshComponent->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
    MeshComponent->SetCollisionProfileName(TEXT("BlockAll"));
    MeshComponent->SetSimulatePhysics(true);
    if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())Fluid->RegisterWaterBody(MeshComponent);
    if(!MeshComponent->IsSimulatingPhysics())return false;
    MeshComponent->AddImpulse(FVector(FMath::FRandRange(-40.f,40.f),FMath::FRandRange(-40.f,40.f),0.f),NAME_None,true);
    if(LogicActor)
    {
        // 逻辑构件只留外观：挂到刚体网格上跟随落体，停止交互、Tick，并让碰撞完全由刚体承担。
        LogicActor->AttachToComponent(MeshComponent,FAttachmentTransformRules::KeepWorldTransform);
        LogicActor->Tags.AddUnique(TEXT("VoxelDetached"));
        LogicActor->SetActorTickEnabled(false);
        TInlineComponentArray<UPrimitiveComponent*> Primitives;
        LogicActor->GetComponents(Primitives);
        for(UPrimitiveComponent* Primitive:Primitives)Primitive->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        // 外观交给逻辑构件（窗框＋两扇、门框＋门板）：占位网格只当物理体，不重复画同一块几何。
        MeshComponent->SetVisibility(false);
    }
    SetLifeSpan(FMath::Max(1.f,LifeSeconds));
    // 标记为落体件：它已不在 AVoxelBuildWorld::Prefabs 记录里，拆除路径要据此区分处理
    // （见 IsFalling() 的说明）。
    bFalling=true;
    return true;
}
