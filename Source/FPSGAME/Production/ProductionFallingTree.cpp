#include "ProductionFallingTree.h"
#include "ProductionResource.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"

AProductionFallingTree::AProductionFallingTree()
{
    PrimaryActorTick.bCanEverTick=true;
    Tree=CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("FallingTree"));
    RootComponent=Tree; Tree->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Tree->SetCanEverAffectNavigation(false); Tree->SetComponentTickEnabled(false);
}
void AProductionFallingTree::InitializeFall(const FProductionResource& Resource,const FVector& Direction)
{
    Tree->SetSkeletalMesh(Cast<USkeletalMesh>(Resource.Mesh.ResolveObject()));
    SetActorTransform(Resource.Transform); InitialRotation=Resource.Transform.GetRotation();
    FVector Away=Direction; Away.Z=0;
    if (!Away.Normalize()) Away=FVector::ForwardVector;
    FallAxis=FVector::CrossProduct(FVector::UpVector,Away);
    SetLifeSpan(3.4f);
}
void AProductionFallingTree::Tick(float Delta)
{
    Super::Tick(Delta); Elapsed+=Delta;
    const float T=FMath::Clamp(Elapsed/2.8f,0.f,1.f);
    SetActorRotation(FQuat(FallAxis,FMath::DegreesToRadians(88.f)*T*T)*InitialRotation);
    if (T>=1) SetActorTickEnabled(false);
}
