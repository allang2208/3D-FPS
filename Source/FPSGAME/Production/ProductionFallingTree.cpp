#include "ProductionFallingTree.h"
#include "ProductionResource.h"
#include "ProductionHarvestSubsystem.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
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
    auto* Mesh=Cast<USkeletalMesh>(Resource.Mesh.ResolveObject());Tree->SetSkeletalMesh(Mesh);
    SetActorTransform(Resource.Transform); InitialRotation=Resource.Transform.GetRotation();
    FVector Away=Direction; Away.Z=0;
    if (!Away.Normalize()) Away=FVector::ForwardVector;
    FallAxis=FVector::CrossProduct(FVector::UpVector,Away);
    EffectSeed=Resource.Seed;LandingPoint=GetActorLocation()+Away*200;
    if(auto* World=Resource.World.Get())
    {
        LandingPoint.Z=World->Height(LandingPoint.X,LandingPoint.Y)+20;
        // Follow the donor's terrain-aware landing angle using a few trunk samples.
        const float Height=Mesh?Mesh->GetBounds().BoxExtent.Z*2*Resource.Transform.GetScale3D().Z:1200.f;
        for(float Degrees=12;Degrees<=96;Degrees+=3)
        {
            const FQuat Rotation(FallAxis,FMath::DegreesToRadians(Degrees));bool Touches=false;
            for(float Fraction:{.35f,.65f,.9f})
            {
                const FVector Sample=GetActorLocation()+Rotation.RotateVector(FVector::UpVector*Height*Fraction);
                if(Sample.Z<=World->Height(Sample.X,Sample.Y)+15){Touches=true;break;}
            }
            if(Touches){LandingAngle=Degrees-3;break;}
        }
    }
    SetLifeSpan(3.4f);
}
void AProductionFallingTree::Tick(float Delta)
{
    Super::Tick(Delta); Elapsed+=Delta;
    const float T=FMath::Clamp(Elapsed/2.8f,0.f,1.f);
    SetActorRotation(FQuat(FallAxis,FMath::DegreesToRadians(LandingAngle)*FMath::Pow(T,2.1f))*InitialRotation);
    if(T>=1&&!Landed)
    {
        Landed=true;
        if(auto* Harvest=GetWorld()->GetSubsystem<UProductionHarvestSubsystem>())Harvest->Burst(true,LandingPoint,EffectSeed,true);
    }
    if(Elapsed>=3.05f){Tree->SetVisibility(false,true);SetActorTickEnabled(false);}
}
