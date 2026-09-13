#include "VoxelCollapseFragment.h"
#include "VoxelBuildWorld.h"
#include "VoxelBuildGeometry.h"
#include "Components/DynamicMeshComponent.h"
#include "Engine/DamageEvents.h"

AVoxelCollapseFragment::AVoxelCollapseFragment()
{
    PrimaryActorTick.bCanEverTick=false;
    Body=CreateDefaultSubobject<UDynamicMeshComponent>(TEXT("CompoundDebris"));SetRootComponent(Body);
    Body->SetMobility(EComponentMobility::Movable);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Body->SetCanEverAffectNavigation(false);Body->SetGenerateOverlapEvents(false);
    Body->CollisionType=CTF_UseSimpleAsComplex;Body->bEnableComplexCollision=false;
    Body->SetDeferredCollisionUpdatesEnabled(true,false);
    Body->SetTangentsType(EDynamicMeshComponentTangentsMode::AutoCalculated);
    Body->SetNotifyRigidBodyCollision(true);Body->BodyInstance.bUseCCD=true;
    Body->SetLinearDamping(.08);Body->SetAngularDamping(.3);
    Body->OnComponentHit.AddDynamic(this,&AVoxelCollapseFragment::OnCollision);
    SetCanBeDamaged(true);
}

void AVoxelCollapseFragment::Initialize(AVoxelBuildWorld* OwnerWorld,const FVoxelFragmentSave& InState,
    TSharedPtr<FVoxelGeometry> Geometry,const TArray<TObjectPtr<UMaterialInterface>>& Materials)
{
    Building=OwnerWorld;State=InState;SetActorTransform(State.Transform);
    Body->SetPhysMaterialOverride(OwnerWorld->ContactMaterial());
    Mass=Geometry->MassKg;Shapes=Geometry->Collision.BoxElems.Num();DesiredCenter=Geometry->MassCenter;
    for(int32 I=0;I<Materials.Num();++I)Body->SetMaterial(I,Materials[I]);
    Body->SetMesh(MoveTemp(Geometry->Mesh));Body->SetSimpleCollisionShapes(Geometry->Collision,true);
    Body->SetMassOverrideInKg(NAME_None,Mass,true);
    SetActorHiddenInGame(true);
}

void AVoxelCollapseFragment::EnableWaitingCollision()
{
    if(bReplacing)return;
    SetActorHiddenInGame(false);Body->SetCollisionProfileName(TEXT("BlockAll"));
    Body->SetCollisionObjectType(ECC_PhysicsBody);
}

void AVoxelCollapseFragment::Activate()
{
    if(bReplacing||bStarted)return;
    EnableWaitingCollision();Body->SetSimulatePhysics(true);Body->SetMassOverrideInKg(NAME_None,Mass,true);
    Body->SetCenterOfMass(DesiredCenter-GetActorTransform().InverseTransformPosition(Body->GetCenterOfMass()));
    Body->SetPhysicsLinearVelocity(State.Velocity);Body->SetPhysicsAngularVelocityInRadians(State.AngularVelocity);
    PreviousVelocity=State.Velocity;bStarted=true;
    if(State.bSleeping)Body->PutAllRigidBodiesToSleep();else Body->WakeAllRigidBodies();
}

bool AVoxelCollapseFragment::IsMoving() const {return bStarted&&!bReplacing&&Body->IsAnyRigidBodyAwake();}

void AVoxelCollapseFragment::SampleVelocity()
{
    if(bStarted&&!bReplacing)PreviousVelocity=Body->GetPhysicsLinearVelocity();
}

FVoxelFragmentSave AVoxelCollapseFragment::Snapshot() const
{
    auto Result=State;Result.Transform=GetActorTransform();
    if(bStarted&&!bReplacing)
    {
        Result.Velocity=Body->GetPhysicsLinearVelocity();Result.AngularVelocity=Body->GetPhysicsAngularVelocityInRadians();
        Result.bSleeping=!Body->IsAnyRigidBodyAwake();
    }
    return Result;
}

void AVoxelCollapseFragment::UpdateCellDamage(TArray<FVoxelDebrisCell> Cells)
{
    State.Cells=MoveTemp(Cells);
}

void AVoxelCollapseFragment::FreezeForReplacement()
{
    State=Snapshot();bReplacing=true;Body->SetSimulatePhysics(false);
}

float AVoxelCollapseFragment::TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    if(!Building.IsValid()||bReplacing||Amount<=0)return 0;
    if(Event.IsOfType(FPointDamageEvent::ClassID))
    {
        const auto& Point=static_cast<const FPointDamageEvent&>(Event);
        Building->QueueFragmentDamage(this,Point.HitInfo.ImpactPoint-Point.HitInfo.ImpactNormal*.25,Amount,0,0);
    }
    else if(Event.IsOfType(FRadialDamageEvent::ClassID))
    {
        const auto& Radial=static_cast<const FRadialDamageEvent&>(Event);
        Building->QueueFragmentDamage(this,Radial.Origin,Amount,Radial.Params.OuterRadius,0);
    }
    else return 0;
    return Super::TakeDamage(Amount,Event,EventInstigator,Causer);
}

void AVoxelCollapseFragment::OnCollision(UPrimitiveComponent* Component,AActor* Other,UPrimitiveComponent* OtherComponent,FVector Impulse,const FHitResult& Hit)
{
    if(!Building.IsValid()||bReplacing||!bStarted)return;
    const auto* OtherFragment=Cast<AVoxelCollapseFragment>(Other);
    if(OtherFragment&&GetUniqueID()>OtherFragment->GetUniqueID())return;
    const double Now=GetWorld()->GetTimeSeconds();if(Now-LastImpactTime<.12)return;
    const FVector OtherVelocity=OtherComponent?OtherComponent->GetComponentVelocity():FVector::ZeroVector;
    const float Speed=float(FMath::Abs(FVector::DotProduct(PreviousVelocity-OtherVelocity,Hit.ImpactNormal))*.01);
    const float EffectiveMass=OtherFragment?Mass*OtherFragment->MassKg()/(Mass+OtherFragment->MassKg()):Mass;
    const float Energy=FMath::Min(.5f*EffectiveMass*Speed*Speed,float(Impulse.Size())*.01f*Speed*.5f);
    if(Speed<.8f||Energy<20)return;
    LastImpactTime=Now;
    const bool OtherBuilding=OtherFragment||Other==Building.Get();
    Building->QueueFragmentDamage(this,Hit.ImpactPoint,0,FMath::Clamp(FMath::Sqrt(Energy)*.7f,15.f,100.f),Energy*(OtherBuilding?.5f:1.f));
    Building->QueueCollapseImpact(Other,Hit,Energy*(OtherBuilding?.5f:1.f));
}
