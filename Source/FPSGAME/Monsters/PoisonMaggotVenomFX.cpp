#include "PoisonMaggotVenomFX.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/DecalComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "Materials/MaterialInterface.h"
#include "UObject/ConstructorHelpers.h"

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
        Renderer->SetNumCustomDataFloats(2);
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
        Marks.Add(Mark);
    }
    bReady = true;
}

void UPoisonMaggotVenomFX::AddFragment(int32 Group, const FVector& Position, const FVector& Velocity,
    float Life, float Size, float Stretch, float Gravity, float Opacity, const FVector& PlanePoint, const FVector& PlaneNormal)
{
    const int32 Count = Group == 0 ? DropCount : MistCount;
    const int32 Index = Cursors[Group]++ % Count;
    FFragment& P = Fragments[(Group == 0 ? 0 : DropCount) + Index];
    if (P.Life <= 0) ++ActiveParticles;
    P.Position = Position; P.Velocity = Velocity;
    P.PlanePoint = PlanePoint; P.PlaneNormal = PlaneNormal;
    P.Age = 0; P.Life = Life; P.Size = Size; P.Stretch = Stretch;
    P.Gravity = Gravity; P.Opacity = Opacity; P.Seed = Random.FRand();
}

void UPoisonMaggotVenomFX::AddTrail(const FVector& Position, const FVector& Velocity, bool bMist)
{
    if (!bReady) return;
    const FVector Direction = Velocity.GetSafeNormal();
    AddFragment(0, Position - Direction*4.f, Velocity*Random.FRandRange(.14f,.27f)+Random.VRand()*15.f,
        Random.FRandRange(.16f,.26f), Random.FRandRange(.50f,1.1f), Random.FRandRange(1.8f,2.8f), 160.f,1.f);
    if (bMist)
        AddFragment(1, Position-Direction*7.f, Velocity*.06f+Random.VRand()*9.f+FVector(0,0,5),
            Random.FRandRange(.28f,.42f),Random.FRandRange(8.f,13.f),1.f,-5.f,.15f);
}

void UPoisonMaggotVenomFX::AddImpact(const FHitResult& Hit, const FVector& IncomingVelocity)
{
    if (!bReady) return;
    const FVector Normal = Hit.ImpactNormal.GetSafeNormal();
    const FVector Origin = Hit.ImpactPoint + Normal*1.2f;
    const FVector Tangent = FVector::VectorPlaneProject(IncomingVelocity,Normal)*.12f;
    for (int32 Index = 0; Index < 9; ++Index)
    {
        const FVector Side = FVector::VectorPlaneProject(Random.VRand(),Normal).GetSafeNormal();
        const FVector Velocity = Normal*Random.FRandRange(35.f,85.f)+Side*Random.FRandRange(35.f,120.f)+Tangent;
        AddFragment(0,Origin,Velocity,Random.FRandRange(.20f,.42f),Random.FRandRange(.55f,1.5f),
            Random.FRandRange(1.4f,2.7f),360.f,1.f,Hit.ImpactPoint,Normal);
    }
    for (int32 Index = 0; Index < 2; ++Index)
        AddFragment(1,Origin+Normal*2.f,Normal*18.f+Random.VRand()*12.f+FVector(0,0,10),
            Random.FRandRange(.30f,.48f),Random.FRandRange(15.f,22.f),1.f,-7.f,.23f,Hit.ImpactPoint,Normal);

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
            P.Position += P.Velocity*DeltaTime-FVector(0,0,.5f*P.Gravity*DeltaTime*DeltaTime);
            P.Velocity.Z -= P.Gravity*DeltaTime;
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
                const float Fade = FMath::Min(1.f,Age/.12f)*FMath::Square(1.f-Age);
                Renderer->SetCustomDataValue(Index,0,P.Opacity*Fade,false);
                Renderer->SetCustomDataValue(Index,1,P.Seed,false);
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
