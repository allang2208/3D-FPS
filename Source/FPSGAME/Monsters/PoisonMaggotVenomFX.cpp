#include "PoisonMaggotVenomFX.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
float CosmeticViewDistanceSquared(UWorld* World, const FVector& Position)
{
    if (const auto* PC = World ? World->GetFirstPlayerController() : nullptr)
    {
        FVector Eye; FRotator Rotation;
        PC->GetPlayerViewPoint(Eye, Rotation);
        return FVector::DistSquared(Eye, Position);
    }
    return TNumericLimits<float>::Max();
}
}

UPoisonMaggotVenomFX::UPoisonMaggotVenomFX()
{
    ConstructorHelpers::FObjectFinder<UStaticMesh> Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
    ConstructorHelpers::FObjectFinder<UStaticMesh> Plane(TEXT("/Engine/BasicShapes/Plane.Plane"));
    ConstructorHelpers::FObjectFinder<UMaterialInterface> Drops(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomDroplet.M_VenomDroplet"));
    ConstructorHelpers::FObjectFinder<UMaterialInterface> Mist(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomMist.M_VenomMist"));
    ConstructorHelpers::FObjectFinder<UMaterialInterface> Wet(TEXT("/Game/Monsters/PoisonMaggot/VenomLiquid20260915/M_VenomWetFilm.M_VenomWetFilm"));
    SphereMesh = Sphere.Object; PlaneMesh = Plane.Object;
    DropMaterial = Drops.Object; MistMaterial = Mist.Object; WetMaterial = Wet.Object;
}

bool UPoisonMaggotVenomFX::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type == EWorldType::Game || Type == EWorldType::PIE;
}

void UPoisonMaggotVenomFX::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if (World.GetNetMode() == NM_DedicatedServer || !SphereMesh || !PlaneMesh || !DropMaterial || !MistMaterial || !WetMaterial) return;
    for (int32 Group = 0; Group < 2; ++Group)
    {
        auto* Renderer = NewObject<UInstancedStaticMeshComponent>(this);
        Renderer->SetMobility(EComponentMobility::Movable);
        Renderer->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Renderer->SetGenerateOverlapEvents(false);
        Renderer->SetCanEverAffectNavigation(false);
        Renderer->SetCastShadow(false);
        Renderer->bReceivesDecals = false;
        Renderer->bAffectDistanceFieldLighting = false;
        Renderer->SetStaticMesh(Group == 0 ? SphereMesh : PlaneMesh);
        Renderer->SetMaterial(0, Group == 0 ? DropMaterial : MistMaterial);
        // Alpha, stable cosmetic seed, normalized lifetime for the density atlas.
        Renderer->SetNumCustomDataFloats(3);
        const int32 Count = Group == 0 ? DropCount : MistCount;
        Renderer->PreAllocateInstancesMemory(Count);
        Transforms[Group].Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),Count);
        Renderer->AddInstances(Transforms[Group],false,false,false);
        Renderer->RegisterComponentWithWorld(&World);
        Renderers.Add(Renderer);
    }
    for (int32 Index = 0; Index < MarkCount; ++Index)
    {
        auto* Mark = NewObject<UDecalComponent>(this);
        Mark->SetMobility(EComponentMobility::Movable);
        Mark->SetDecalMaterial(WetMaterial);
        Mark->SetVisibility(false);
        Mark->SetFadeScreenSize(.0004f);
        Mark->RegisterComponentWithWorld(&World);
        // Each pooled decal retains its own impact seed/time, with no per-hit MID allocation.
        Mark->CreateDynamicMaterialInstance();
        Marks.Add(Mark);
    }
    bReady = true;
}

void UPoisonMaggotVenomFX::AddFragment(int32 Group, const FVector& Position, const FVector& Velocity,
    float Life, float Size, float Stretch, float Gravity, float Opacity, const FVector& PlanePoint, const FVector& PlaneNormal)
{
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    if(Budget&&Budget->AllocateDetail(Position,1,!PlaneNormal.IsNearlyZero())==0)return;
    const int32 Count = Group == 0 ? DropCount : MistCount;
    const int32 Index = Cursors[Group]++ % Count;
    FFragment& P = Fragments[(Group == 0 ? 0 : DropCount) + Index];
    if (P.Life <= 0) ++ActiveParticles;
    P.Position = Position; P.Velocity = Velocity;P.CollisionPosition=Position;P.NextCollision=.06f;
    P.Wind=Group==1&&Budget?Budget->WindAt(Position):FVector::ZeroVector;
    if(!PlaneNormal.IsNearlyZero())P.Wind=FVector::VectorPlaneProject(P.Wind,PlaneNormal);
    P.PlanePoint = PlanePoint; P.PlaneNormal = PlaneNormal;
    P.Age = 0; P.Life = Life; P.Size = Size; P.Stretch = Stretch;
    P.Gravity = Gravity; P.Opacity = Opacity; P.Seed = Random.FRand();
}

void UPoisonMaggotVenomFX::AddTrail(const FVector& Position, const FVector& Velocity, bool bMist)
{
    if (!bReady) return;
    const float DistanceSquared = CosmeticViewDistanceSquared(GetWorld(), Position);
    if (DistanceSquared > FMath::Square(3500.f)) return;
    const FVector Direction = Velocity.GetSafeNormal();
    AddFragment(0, Position - Direction*4.f, Velocity*Random.FRandRange(.14f,.27f)+Random.VRand()*15.f,
        Random.FRandRange(.16f,.26f), Random.FRandRange(.50f,1.1f), Random.FRandRange(1.8f,2.8f), 160.f,1.f);
    if (bMist && DistanceSquared < FMath::Square(1800.f))
    {
        // Brief stretched ligaments break away from the main liquid mass.
        AddFragment(0,Position-Direction*7.f,Velocity*.24f+Random.VRand()*10.f,
            Random.FRandRange(.12f,.20f),Random.FRandRange(.45f,.75f),Random.FRandRange(4.f,7.f),100.f,1.f);
        AddFragment(1, Position-Direction*7.f, Velocity*.06f+Random.VRand()*9.f+FVector(0,0,5),
            Random.FRandRange(.40f,.60f),Random.FRandRange(10.f,15.f),1.f,-5.f,.19f);
    }
}

void UPoisonMaggotVenomFX::AddBottleImpact(const FVector& Position, const FVector& Normal, const FVector& IncomingVelocity, float Radius)
{
    if (!bReady) return;
    const float DistanceSquared = CosmeticViewDistanceSquared(GetWorld(),Position);
    if (DistanceSquared > FMath::Square(5500.f)) return;
    const bool bNear = DistanceSquared < FMath::Square(2000.f);
    const float Scale = FMath::Clamp(Radius/200.f,.5f,1.75f);
    const FVector N = Normal.GetSafeNormal();
    const FVector Origin = Position+N*3.f;
    const FVector Tangent = FVector::VectorPlaneProject(IncomingVelocity,N)*.06f;
    for (int32 Index=0;Index<(bNear?16:6);++Index)
    {
        const FVector Side = FVector::VectorPlaneProject(Random.VRand(),N).GetSafeNormal();
        AddFragment(0,Origin,Side*Random.FRandRange(90.f,190.f)*Scale+N*Random.FRandRange(70.f,145.f)+Tangent,
            Random.FRandRange(.38f,.72f),Random.FRandRange(.85f,2.1f)*Scale,
            Random.FRandRange(1.7f,3.5f),420.f,1.f,Position,N);
    }
    for (int32 Index=0;Index<(bNear?4:1);++Index)
        AddFragment(1,Origin+N*4.f,N*13.f+Random.VRand()*17.f,
            Random.FRandRange(.70f,1.10f),Random.FRandRange(32.f,49.f)*Scale,1.f,-4.f,.24f,Position,N);
}

void UPoisonMaggotVenomFX::AddPoolVapor(const FVector& Position, const FVector& Normal, float Radius)
{
    if (!bReady || CosmeticViewDistanceSquared(GetWorld(),Position)>FMath::Square(2000.f)) return;
    const FVector Side = FVector::VectorPlaneProject(Random.VRand(),Normal).GetSafeNormal();
    const FVector Origin = Position+Side*(Radius*Random.FRandRange(.1f,.65f))+Normal*7.f;
    AddFragment(1,Origin,Normal*9.f+Side*5.f,Random.FRandRange(.85f,1.20f),
        Random.FRandRange(27.f,42.f),1.f,-3.f,.17f,Position,Normal);
}

void UPoisonMaggotVenomFX::AddImpact(const FHitResult& Hit, const FVector& IncomingVelocity)
{
    if (!bReady) return;
    const float DistanceSquared = CosmeticViewDistanceSquared(GetWorld(), Hit.ImpactPoint);
    if (DistanceSquared > FMath::Square(5500.f)) return;
    const bool bNear = DistanceSquared < FMath::Square(2000.f);
    const FVector Normal = Hit.ImpactNormal.GetSafeNormal();
    const FVector Origin = Hit.ImpactPoint + Normal*1.2f;
    const FVector Tangent = FVector::VectorPlaneProject(IncomingVelocity,Normal)*.12f;
    for (int32 Index = 0; Index < (bNear ? 9 : 4); ++Index)
    {
        const FVector Side = FVector::VectorPlaneProject(Random.VRand(),Normal).GetSafeNormal();
        const FVector Velocity = Normal*Random.FRandRange(35.f,85.f)+Side*Random.FRandRange(35.f,120.f)+Tangent;
        AddFragment(0,Origin,Velocity,Random.FRandRange(.20f,.42f),Random.FRandRange(.55f,1.5f),
            Random.FRandRange(1.4f,2.7f),360.f,1.f,Hit.ImpactPoint,Normal);
    }
    for (int32 Index = 0; Index < (bNear ? 3 : 1); ++Index)
        AddFragment(1,Origin+Normal*3.f,Normal*12.f+Random.VRand()*8.f+FVector(0,0,8),
            Random.FRandRange(.85f,1.25f),Random.FRandRange(18.f,27.f),1.f,-5.f,.28f,Hit.ImpactPoint,Normal);

    // Project residue only onto physical scenery. A player capsule is not a
    // visible skin surface, so it receives the splash but no floating decal.
    auto* Surface = Hit.GetComponent();
    if (!Surface || Cast<APawn>(Hit.GetActor())) return;
    auto* Mark = Marks[MarkCursor++ % MarkCount].Get();
    Mark->DetachFromComponent(FDetachmentTransformRules::KeepWorldTransform);
    Mark->SetWorldLocation(Hit.ImpactPoint + Normal*.25f);
    FRotator Rotation = (-Normal).Rotation(); Rotation.Roll = Random.FRandRange(-180.f,180.f);
    Mark->SetWorldRotation(Rotation);
    Mark->DecalSize = FVector(5.f,Random.FRandRange(11.f,17.f),Random.FRandRange(12.f,21.f));
    Mark->AttachToComponent(Surface,FAttachmentTransformRules::KeepWorldTransform,Hit.BoneName);
    if (auto* Material = Cast<UMaterialInstanceDynamic>(Mark->GetDecalMaterial()))
    {
        Material->SetScalarParameterValue(TEXT("ImpactSeed"),Random.FRand());
        Material->SetScalarParameterValue(TEXT("ImpactTime"),GetWorld()->GetTimeSeconds());
    }
    Mark->SetVisibility(true);
    Mark->SetFadeOut(4.5f,2.5f,false);
}

void UPoisonMaggotVenomFX::Tick(float DeltaTime)
{
    FVector Eye = FVector::ZeroVector; FRotator ViewRotation;
    if (auto* PC = GetWorld()->GetFirstPlayerController()) PC->GetPlayerViewPoint(Eye,ViewRotation);
    for (int32 Group = 0; Group < 2; ++Group)
    {
        bool Dirty = false;
        const int32 Count = Group == 0 ? DropCount : MistCount;
        auto* Renderer = Renderers[Group].Get();
        for (int32 Index = 0; Index < Count; ++Index)
        {
            FFragment& P = Fragments[(Group == 0 ? 0 : DropCount) + Index];
            if (P.Life <= 0) continue;
            Dirty = true;
            P.Age += DeltaTime;
            if (Group == 1)
            {
                // A small deterministic curl; no collision traces or new simulation pass.
                FVector Curl(FMath::Sin(P.Age*3.1f+P.Seed*19.f),
                    FMath::Cos(P.Age*2.7f+P.Seed*13.f),.3f);
                if (!P.PlaneNormal.IsNearlyZero()) Curl = FVector::VectorPlaneProject(Curl,P.PlaneNormal);
                const float Drag=FMath::Exp(-.7f*DeltaTime);
                P.Velocity=P.Velocity*Drag+P.Wind*(1.f-Drag)+Curl*(7.f*DeltaTime);
            }
            P.Position += P.Velocity*DeltaTime-FVector(0,0,.5f*P.Gravity*DeltaTime*DeltaTime);
            P.Velocity.Z -= P.Gravity*DeltaTime;
            if(Group==1&&P.Age>=P.NextCollision)
            {
                if(auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
                    if(Budget->MoveMist(P.Position,P.Velocity,P.CollisionPosition,2.f))P.Opacity*=.72f;
                P.CollisionPosition=P.Position;P.NextCollision=P.Age+.10f;
            }
            const float PlaneDistance = FVector::DotProduct(P.Position-P.PlanePoint,P.PlaneNormal);
            if (P.Age >= P.Life || (!P.PlaneNormal.IsNearlyZero() && PlaneDistance < .2f))
            {
                P.Life = 0; --ActiveParticles;
                Transforms[Group][Index] = FTransform(FQuat::Identity,P.Position,FVector::ZeroVector);
                Renderer->SetCustomDataValue(Index,0,0,false);
                continue;
            }
            const float Age = P.Age/P.Life;
            if (Group == 0)
            {
                const float Size = P.Size*(1.f-Age*Age)*.01f;
                const FQuat Rotation = FRotationMatrix::MakeFromX(P.Velocity.GetSafeNormal()).ToQuat();
                Transforms[Group][Index] = FTransform(Rotation,P.Position,FVector(Size*P.Stretch,Size,Size));
            }
            else
            {
                const float Size = P.Size*(.65f+.85f*Age)*.01f;
                const FQuat Facing = FRotationMatrix::MakeFromZ((Eye-P.Position).GetSafeNormal()).ToQuat();
                const FQuat Roll(FVector::UpVector,P.Seed*2.f*PI+Age*.3f);
                Transforms[Group][Index] = FTransform(Facing*Roll,P.Position,FVector(Size,Size,Size));
                const float Fade = FMath::Min(1.f,Age/.10f)*FMath::Pow(1.f-Age,1.25f);
                Renderer->SetCustomDataValue(Index,0,P.Opacity*Fade,false);
                Renderer->SetCustomDataValue(Index,1,P.Seed,false);
                Renderer->SetCustomDataValue(Index,2,Age,false);
            }
        }
        if (Dirty) Renderer->BatchUpdateInstancesTransforms(0,Transforms[Group],true,true,true);
    }
}

void UPoisonMaggotVenomFX::Deinitialize()
{
    bReady = false;
    for (const auto& Renderer : Renderers) if (Renderer) Renderer->DestroyComponent();
    for (const auto& Mark : Marks) if (Mark) Mark->DestroyComponent();
    Renderers.Empty(); Marks.Empty(); ActiveParticles = 0;
    Super::Deinitialize();
}

TStatId UPoisonMaggotVenomFX::GetStatId() const
{
    RETURN_QUICK_DECLARE_CYCLE_STAT(PoisonMaggotVenomFX,STATGROUP_Tickables);
}
