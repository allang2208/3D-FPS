#include "ProductionBreakEffect.h"
#include "ProductionHarvestAssets.h"
#include "Components/SceneComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Particles/ParticleSystem.h"
#include "Particles/ParticleSystemComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraComponent.h"

AProductionBreakEffect::AProductionBreakEffect()
{
    PrimaryActorTick.bCanEverTick=true;PrimaryActorTick.TickInterval=.05f;
    RootComponent=CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
}
void AProductionBreakEffect::Start(bool Wood,uint32 Seed,bool Landing)
{
    SetLifeSpan(2.4f);
    if(auto* Template=Cast<UParticleSystem>(ProductionHarvestAssets::Destruction(Wood).ResolveObject()))
    {
        Dust=NewObject<UParticleSystemComponent>(this);AddInstanceComponent(Dust);Dust->SetupAttachment(RootComponent);
        Dust->bAutoActivate=false;Dust->SetTemplate(Template);Dust->SetRelativeScale3D(FVector(Wood?.7f:1.f));
        Dust->SetCastShadow(false);Dust->SetCullDistance(5000.f);Dust->RegisterComponent();Dust->ActivateSystem(true);
    }
    if(Wood)
    {
        if(auto* System=Cast<UNiagaraSystem>(ProductionHarvestAssets::Leaves().ResolveObject()))
        {
            Leaves=NewObject<UNiagaraComponent>(this);AddInstanceComponent(Leaves);Leaves->SetupAttachment(RootComponent);
            Leaves->bAutoActivate=false;Leaves->SetAsset(System);Leaves->SetRelativeLocation(FVector(0,0,Landing?90:250));
            Leaves->SetRelativeScale3D(FVector(.35f));Leaves->SetCastShadow(false);Leaves->SetCullDistance(5000.f);
            Leaves->RegisterComponent();Leaves->Activate(true);
        }
        return;
    }
    auto* Mesh=Cast<UStaticMesh>(ProductionHarvestAssets::Debris().ResolveObject());if(!Mesh)return;
    const auto Bounds=Mesh->GetBounds();FRandomStream Random(Seed);
    for(int32 N=0;N<6;++N)
    {
        const float Scale=Random.FRandRange(9,18)/FMath::Max(1.f,float(Bounds.BoxExtent.GetMax()));
        auto* Body=NewObject<UBoxComponent>(this);AddInstanceComponent(Body);Body->SetupAttachment(RootComponent);
        Body->SetRelativeLocation(FVector(Random.FRandRange(-18,18),Random.FRandRange(-18,18),25+N*7));
        Body->SetBoxExtent((Bounds.BoxExtent*Scale).ComponentMax(FVector(3)));
        Body->SetCollisionEnabled(ECollisionEnabled::PhysicsOnly);Body->SetCollisionObjectType(ECC_PhysicsBody);
        Body->SetCollisionResponseToAllChannels(ECR_Ignore);Body->SetCollisionResponseToChannel(ECC_WorldStatic,ECR_Block);
        Body->SetCanEverAffectNavigation(false);Body->SetLinearDamping(.8f);Body->SetAngularDamping(2.f);Body->SetUseCCD(true);
        Body->RegisterComponent();Bodies.Add(Body);
        auto* Piece=NewObject<UStaticMeshComponent>(this);AddInstanceComponent(Piece);Piece->SetupAttachment(Body);
        Piece->SetStaticMesh(Mesh);Piece->SetRelativeScale3D(FVector(Scale));Piece->SetRelativeLocation(-Bounds.Origin*Scale);
        Piece->SetCollisionEnabled(ECollisionEnabled::NoCollision);Piece->SetCastShadow(false);Piece->SetCullDistance(4000.f);Piece->RegisterComponent();
        Body->SetSimulatePhysics(true);Body->SetMassOverrideInKg(NAME_None,.2f);
        FVector Velocity=Random.VRand();Velocity.Z=FMath::Abs(Velocity.Z)+.8f;
        Body->SetPhysicsLinearVelocity(Velocity*Random.FRandRange(150,230));Body->SetPhysicsAngularVelocityInDegrees(Random.VRand()*220);
    }
}
void AProductionBreakEffect::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    if(Age>.35f&&Leaves&&Leaves->IsActive())Leaves->Deactivate();
    if(Age>.7f&&Dust&&Dust->IsActive())Dust->DeactivateSystem();
    if(Age>1.4f&&!Stopped)
    {
        Stopped=true;
        for(auto& Body:Bodies){Body->SetSimulatePhysics(false);Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);}
    }
    if(Age>1.7f)for(auto& Body:Bodies)Body->SetWorldScale3D(FVector(FMath::Clamp((2.3f-Age)/.6f,.01f,1.f)));
}
