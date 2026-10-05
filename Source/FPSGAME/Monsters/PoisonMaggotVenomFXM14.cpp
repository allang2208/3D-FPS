#include "PoisonMaggotVenomFX.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"

namespace
{
bool M14DetailNear(UWorld* World,const FVector& Position,float Range)
{
    if(const auto* PC=World->GetFirstPlayerController())
    {
        FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);
        return FVector::DistSquared(Eye,Position)<FMath::Square(Range);
    }
    return false;
}
}

void UPoisonMaggotVenomFX::InitializeM14Films(UWorld& World)
{
    if(!M14FilmMaterial)return;
    M14FilmRenderer=NewObject<UInstancedStaticMeshComponent>(this);
    auto* Renderer=M14FilmRenderer.Get();
    Renderer->SetMobility(EComponentMobility::Movable);
    Renderer->SetStaticMesh(PlaneMesh);Renderer->SetMaterial(0,M14FilmMaterial);
    Renderer->SetCollisionEnabled(ECollisionEnabled::NoCollision);Renderer->SetGenerateOverlapEvents(false);
    Renderer->SetCanEverAffectNavigation(false);Renderer->SetCastShadow(false);
    Renderer->bReceivesDecals=false;Renderer->bAffectDistanceFieldLighting=false;
    Renderer->SetNumCustomDataFloats(3);Renderer->PreAllocateInstancesMemory(M14FilmCount);
    M14FilmTransforms.Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),M14FilmCount);
    Renderer->AddInstances(M14FilmTransforms,false,false,false);Renderer->RegisterComponentWithWorld(&World);
}

void UPoisonMaggotVenomFX::AddM14Muzzle(const FVector& Position,const FVector& Velocity)
{
    if(!bReady||!M14DetailNear(GetWorld(),Position,2500.f))return;
    const FVector Direction=Velocity.GetSafeNormal();
    // A brief fan of stretched liquid connects the emerging shot to its mouth.
    for(int32 I=0;I<7;++I)
    {
        const FVector Side=FVector::VectorPlaneProject(Random.VRand(),Direction);
        AddFragment(0,Position+Side*Random.FRandRange(1.f,4.f),
            Velocity*Random.FRandRange(.28f,.52f)+Side*Random.FRandRange(18.f,45.f),
            Random.FRandRange(.11f,.22f),Random.FRandRange(1.f,1.8f),I<2?7.f:3.f,220.f,1.f);
    }
    // Heavier drips fall below the lip as the main liquid clears the opening.
    for(int32 I=0;I<2;++I)
        AddFragment(0,Position-FVector(0,0,4.f),Direction*65.f+FVector(0,0,-30.f),.30f,1.4f,2.8f,400.f,1.f);
}

void UPoisonMaggotVenomFX::AddM14Trail(const FVector& Position,const FVector& Velocity,int32 Sample)
{
    if(!bReady||!M14DetailNear(GetWorld(),Position,3000.f))return;
    const FVector Direction=Velocity.GetSafeNormal();
    const FVector Side=FVector::VectorPlaneProject(Random.VRand(),Direction);
    // Dense short ligaments near the bulb break into larger drops farther back.
    AddFragment(0,Position-Direction*19.f+Side*1.3f,Velocity*Random.FRandRange(.18f,.28f)+Side*20.f,
        Random.FRandRange(.23f,.37f),Random.FRandRange(1.1f,1.9f),Random.FRandRange(2.f,3.4f),240.f,1.f);
    if(Sample%3==0&&M14DetailNear(GetWorld(),Position,1800.f))
        AddFragment(0,Position-Direction*14.f,Velocity*.34f+Side*7.f,.16f,1.1f,11.f,100.f,1.f);
}

void UPoisonMaggotVenomFX::AddM14Impact(const FHitResult& Hit,const FVector& IncomingVelocity)
{
    if(!bReady)return;
    const int32 PreviousMark=MarkCursor;
    AddImpact(Hit,IncomingVelocity); // Existing mist, residue and collision handling.
    if(!M14DetailNear(GetWorld(),Hit.ImpactPoint,3000.f))return;
    const FVector N=Hit.ImpactNormal.GetSafeNormal();
    const FVector Tangent=FVector::VectorPlaneProject(IncomingVelocity,N)*.11f;
    for(int32 I=0;I<9;++I)
    {
        const FVector Side=FVector::VectorPlaneProject(Random.VRand(),N).GetSafeNormal();
        AddFragment(0,Hit.ImpactPoint+N*2.f,Side*Random.FRandRange(95.f,205.f)+N*Random.FRandRange(55.f,105.f)+Tangent,
            Random.FRandRange(.26f,.46f),Random.FRandRange(1.3f,2.4f),Random.FRandRange(2.5f,5.f),440.f,1.f,Hit.ImpactPoint,N);
    }
    // Enlarge only the mark allocated by this M14 hit, never another caller's.
    if(MarkCursor!=PreviousMark&&Marks.Num()==MarkCount)
        Marks[(MarkCursor-1)%MarkCount]->DecalSize=FVector(5.f,28.f,34.f);
    // A pawn capsule isn't a visible contact surface. It receives droplets only.
    if(!M14FilmRenderer||Cast<APawn>(Hit.GetActor()))return;
    if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        if(Budget->AllocateDetail(Hit.ImpactPoint,1,true)==0)return;
    const int32 Index=M14FilmCursor++%M14FilmCount;
    FM14Film& Film=M14Films[Index];if(Film.Life<=0.f)++ActiveParticles;
    Film.Position=Hit.ImpactPoint+N*.8f;
    FVector Along=Tangent;
    if(Along.IsNearlyZero()){FVector Across;N.FindBestAxisVectors(Along,Across);}
    Film.Rotation=FRotationMatrix::MakeFromZX(N,Along).ToQuat();
    Film.Age=0;Film.Life=.40f;Film.Size=Random.FRandRange(48.f,64.f);Film.Seed=Random.FRand();
}

void UPoisonMaggotVenomFX::TickM14Films(float DeltaTime)
{
    if(!M14FilmRenderer)return;
    bool Dirty=false;
    for(int32 I=0;I<M14FilmCount;++I)
    {
        FM14Film& Film=M14Films[I];if(Film.Life<=0.f)continue;
        Dirty=true;Film.Age+=DeltaTime;
        if(Film.Age>=Film.Life)
        {
            Film.Life=0;--ActiveParticles;
            M14FilmTransforms[I]=FTransform(FQuat::Identity,Film.Position,FVector::ZeroVector);
            M14FilmRenderer->SetCustomDataValue(I,0,0,false);continue;
        }
        const float Age=Film.Age/Film.Life;
        const float Spread=1.f-FMath::Pow(1.f-Age,3.f);
        const float Size=Film.Size*(.22f+.78f*Spread)*.01f;
        M14FilmTransforms[I]=FTransform(Film.Rotation,Film.Position,FVector(Size*1.15f,Size,Size));
        M14FilmRenderer->SetCustomDataValue(I,0,FMath::Min(1.f,Age/.07f)*FMath::Pow(1.f-Age,1.4f),false);
        M14FilmRenderer->SetCustomDataValue(I,1,Film.Seed,false);
        M14FilmRenderer->SetCustomDataValue(I,2,Age,false);
    }
    if(Dirty)M14FilmRenderer->BatchUpdateInstancesTransforms(0,M14FilmTransforms,true,true,true);
}
