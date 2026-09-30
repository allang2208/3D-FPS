#include "WardBreakableGlass.h"

#include "Components/AudioComponent.h"
#include "../Weapons/FPSImpactFXSubsystem.h"
#include "Engine/DamageEvents.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Sound/SoundAttenuation.h"
#include "TimerManager.h"

UWardBreakableGlass::UWardBreakableGlass()
{
    PrimaryComponentTick.bCanEverTick=false;
    SetMobility(EComponentMobility::Movable);
    SetCollisionProfileName(TEXT("BlockAllDynamic"));
    SetCanEverAffectNavigation(false);
    SetCastShadow(false);
    bReceivesDecals=false;
    ComponentTags.Add(TEXT("Impact.Glass"));
}

void UWardBreakableGlass::ReceiveComponentDamage(float DamageAmount,const FDamageEvent& DamageEvent,
    AController* EventInstigator,AActor* DamageCauser)
{
    Super::ReceiveComponentDamage(DamageAmount,DamageEvent,EventInstigator,DamageCauser);
    HandleDamage(DamageAmount,DamageEvent,DamageCauser);
}

void UWardBreakableGlass::HandleDamage(float DamageAmount,const FDamageEvent& Event,AActor* Causer)
{
    if(DamageAmount<=0.f || bBroken)return;
    if(Event.IsOfType(FPointDamageEvent::ClassID))
    {
        const auto& Point=static_cast<const FPointDamageEvent&>(Event);
        // A hit on the surviving metal leaf must not break an untouched pane.
        if(Point.HitInfo.GetComponent()==this)BreakAt(Point.HitInfo.ImpactPoint,Point.ShotDirection);
    }
    else if(Event.IsOfType(FRadialDamageEvent::ClassID))
    {
        const auto& Radial=static_cast<const FRadialDamageEvent&>(Event);
        for(const auto& Hit:Radial.ComponentHits)
            if(Hit.GetComponent()==this){BreakAt(Hit.ImpactPoint,Hit.ImpactPoint-Radial.Origin);break;}
    }
    else BreakAt(GetComponentLocation(),Causer?GetComponentLocation()-Causer->GetActorLocation():GetForwardVector());
}

bool UWardBreakableGlass::BreakAt(const FVector& HitPoint,const FVector& Direction)
{
    if(bBroken || !GetOwner() || !GetOwner()->HasAuthority())return false;
    bBroken=true;
    ComponentTags.AddUnique(TEXT("Glass.Broken"));
    if(auto* Impacts=GetWorld()->GetSubsystem<UFPSImpactFXSubsystem>())Impacts->ClearImpactDecalsForComponent(this);
    SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);
    SetVisibility(false,true);
    if(UWorld* World=GetWorld())
        if(auto* FX=World->GetSubsystem<UWardGlassFXSubsystem>())
            FX->BreakPane(this,HitPoint,Direction.GetSafeNormal(SMALL_NUMBER,GetForwardVector()));
    return true;
}

bool UWardBreakableGlass::BreakHit(const FHitResult& Hit,const FVector& Direction)
{
    auto* Pane=Cast<UWardBreakableGlass>(Hit.GetComponent());
    return Pane && Pane->BreakAt(Hit.ImpactPoint,Direction);
}

UWardBreakableGlass* UWardBreakableGlass::IntactPane(AActor* Actor)
{
    auto* Pane=IsValid(Actor)?Actor->FindComponentByClass<UWardBreakableGlass>():nullptr;
    return Pane && !Pane->bBroken?Pane:nullptr;
}

FVector UWardBreakableGlass::TargetPoint(AActor* Actor)
{
    if(auto* Pane=IntactPane(Actor))return Pane->GetComponentLocation();
    return Actor->GetActorLocation();
}

void UWardBreakableGlass::BreakInRadius(UWorld* World,const FVector& Center,float Radius,AActor* Causer)
{
    if(!World || Radius<=0 || (Causer && !Causer->HasAuthority()))return;
    FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WardGlassBlast),false,Causer);
    TArray<FOverlapResult> Overlaps;
    World->OverlapMultiByObjectType(Overlaps,Center,FQuat::Identity,Objects,FCollisionShape::MakeSphere(Radius),Query);
    // Capture exposure before breaking any pane; the same blast cannot leak through
    // the obstacle it is just removing to shatter another pane behind it.
    TArray<TPair<UWardBreakableGlass*,FVector>> Exposed;
    for(const auto& Overlap:Overlaps)
    {
        auto* Pane=Cast<UWardBreakableGlass>(Overlap.GetComponent());
        if(!Pane || Pane->bBroken)continue;
        FVector Point;
        const float Distance=Pane->GetClosestPointOnCollision(Center,Point);
        if(Distance<0 || Distance>Radius)continue;
        if(Distance==0)Point=Center;
        FHitResult Cover;
        if(World->LineTraceSingleByChannel(Cover,Center,Point+(Point-Center).GetSafeNormal()*2.f,ECC_Visibility,Query)
            && Cover.GetComponent()!=Pane)continue;
        Exposed.Emplace(Pane,Point);
    }
    for(const auto& Entry:Exposed)Entry.Key->BreakAt(Entry.Value,Entry.Value-Center);
}

AWardGlassDoor::AWardGlassDoor()
{
    SetCanBeDamaged(true);
    MetalLeaf=Cast<UStaticMeshComponent>(GetDefaultSubobjectByName(TEXT("DoorLeaf")));
    if(MetalLeaf)MetalLeaf->ComponentTags.AddUnique(TEXT("Impact.Metal"));
    GlassPane=CreateDefaultSubobject<UWardBreakableGlass>(TEXT("BreakableGlass"));
    GlassPane->SetupAttachment(MetalLeaf);
    GlassPane->SetRelativeLocation(FVector(0.f,0.f,13.3f));
}

float AWardGlassDoor::TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    const float Applied=Super::TakeDamage(Amount,Event,EventInstigator,Causer);
    if(GlassPane)GlassPane->HandleDamage(Applied,Event,Causer);
    return Applied;
}

void AWardGlassDoor::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    // Follow the existing door's anti-crush policy without restoring broken glass.
    if(GlassPane && !GlassPane->bBroken && MetalLeaf)
    {
        const auto Response=MetalLeaf->GetCollisionResponseToChannel(ECC_Pawn);
        if(GlassPane->GetCollisionResponseToChannel(ECC_Pawn)!=Response)
            GlassPane->SetCollisionResponseToChannel(ECC_Pawn,Response);
    }
}

AWardGlassWindow::AWardGlassWindow()
{
    PrimaryActorTick.bCanEverTick=false;
    SetCanBeDamaged(true);
    GlassPane=CreateDefaultSubobject<UWardBreakableGlass>(TEXT("BreakableGlass"));
    SetRootComponent(GlassPane);
}

float AWardGlassWindow::TakeDamage(float Amount,const FDamageEvent& Event,AController* EventInstigator,AActor* Causer)
{
    const float Applied=Super::TakeDamage(Amount,Event,EventInstigator,Causer);
    if(GlassPane)GlassPane->HandleDamage(Applied,Event,Causer);
    return Applied;
}

AWardGlassBurst::AWardGlassBurst()
{
    PrimaryActorTick.bCanEverTick=false;
    Fragments=CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Fragments"));
    SetRootComponent(Fragments);
    Fragments->SetMobility(EComponentMobility::Movable);
    Fragments->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Fragments->SetCanEverAffectNavigation(false);
    Fragments->SetCastShadow(false);
    Fragments->bReceivesDecals=false;
    Fragments->SetCullDistance(10000.f);
    // WPO travels roughly two metres, including gravity, from the original pane.
    Fragments->SetBoundsScale(6.f);
    Glints=CreateDefaultSubobject<UNiagaraComponent>(TEXT("GlassGlints"));
    Glints->SetupAttachment(Fragments);
    Glints->SetAutoActivate(false);
    Glints->SetCanEverAffectNavigation(false);
    Audio=CreateDefaultSubobject<UAudioComponent>(TEXT("ShatterAudio"));
    Audio->SetupAttachment(Fragments);
    Audio->bAutoActivate=false;
    Audio->bOverrideAttenuation=true;
    Audio->AttenuationOverrides.bAttenuate=true;
    Audio->AttenuationOverrides.bSpatialize=true;
    Audio->AttenuationOverrides.AttenuationShape=EAttenuationShape::Sphere;
    Audio->AttenuationOverrides.AttenuationShapeExtents=FVector(180.f,0.f,0.f);
    Audio->AttenuationOverrides.FalloffDistance=2500.f;
}

void AWardGlassBurst::Play(const UWardBreakableGlass* Pane,const FVector& HitPoint,const FVector& ShotDirection)
{
    GetWorldTimerManager().ClearTimer(ReleaseTimer);
    Glints->DeactivateImmediate();Audio->Stop();
    SetActorTransform(Pane->GetComponentTransform()); // Never attach this snapshot to the moving door.
    Fragments->SetStaticMesh(Pane->FractureMesh);
    if(!Material || MaterialSource!=Pane->FractureMaterial)
    {
        MaterialSource=Pane->FractureMaterial;
        Material=UMaterialInstanceDynamic::Create(MaterialSource,this);
    }
    Fragments->SetMaterial(0,Material);
    FHitResult Ground;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WardGlassFloor),false,Pane->GetOwner());
    if(const AActor* Parent=Pane->GetOwner()->GetAttachParentActor())Query.AddIgnoredActor(Parent);
    Query.AddIgnoredActor(this);
    const FVector Origin=Pane->GetComponentLocation();
    // Probe off the pane plane so an observation-window sill is not mistaken for the floor.
    const FVector PaneNormal=Pane->GetForwardVector();
    const FVector FloorSample=Origin+PaneNormal*(FVector::DotProduct(ShotDirection,PaneNormal)>=0.f?55.f:-55.f);
    const float FloorZ=GetWorld()->LineTraceSingleByChannel(Ground,FloorSample,FloorSample-FVector(0,0,700),ECC_Visibility,Query)
        ? Ground.ImpactPoint.Z : Origin.Z-Pane->PaneDimensions.Y*.5f;
    Material->SetScalarParameterValue(TEXT("Born"),GetWorld()->GetTimeSeconds());
    Material->SetScalarParameterValue(TEXT("FloorZ"),FloorZ);
    Material->SetVectorParameterValue(TEXT("PaneSize"),FLinearColor(Pane->PaneDimensions));
    Material->SetVectorParameterValue(TEXT("PaneOrigin"),FLinearColor(Origin));
    Material->SetVectorParameterValue(TEXT("PaneY"),FLinearColor(Pane->GetRightVector()));
    Material->SetVectorParameterValue(TEXT("PaneZ"),FLinearColor(Pane->GetUpVector()));
    Material->SetVectorParameterValue(TEXT("HitPoint"),FLinearColor(HitPoint));
    Material->SetVectorParameterValue(TEXT("ShotDirection"),FLinearColor(ShotDirection.GetSafeNormal()));
    SetActorHiddenInGame(false);
    if(Pane->ImpactParticles)
    {
        Glints->SetAsset(Pane->ImpactParticles);
        // This shared impact asset also contains bullet-hole emitters. Disable
        // them only on the shatter component, before activation, on every reuse.
        for(const auto& Emitter:Pane->ImpactParticles->GetEmitterHandles())
            if(Emitter.GetName().ToString().Contains(TEXT("Decal")))Glints->SetEmitterEnable(Emitter.GetName(),false);
        Glints->SetWorldLocationAndRotation(HitPoint,FRotationMatrix::MakeFromZ(ShotDirection).Rotator());
        Glints->Activate(true);
    }
    if(Pane->BreakSound)
    {
        Audio->SetSound(Pane->BreakSound);Audio->SetWorldLocation(HitPoint);
        Audio->SetVolumeMultiplier(.85f);Audio->SetPitchMultiplier(FMath::FRandRange(.87f,1.02f));Audio->Play();
    }
    GetWorldTimerManager().SetTimer(ReleaseTimer,this,&AWardGlassBurst::Park,4.1f,false);
}

void AWardGlassBurst::Park()
{
    SetActorHiddenInGame(true);Glints->DeactivateImmediate();Audio->Stop();
}

bool UWardGlassFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{
    return Type==EWorldType::Game || Type==EWorldType::PIE;
}

void UWardGlassFXSubsystem::BreakPane(const UWardBreakableGlass* Pane,const FVector& HitPoint,const FVector& ShotDirection)
{
    if(GetWorld()->GetNetMode()==NM_DedicatedServer || !Pane->FractureMesh || !Pane->FractureMaterial)return;
    if(Bursts.Num()<6)
    {
        FActorSpawnParameters Params;
        Params.ObjectFlags|=RF_Transient;
        Params.SpawnCollisionHandlingOverride=ESpawnActorCollisionHandlingMethod::AlwaysSpawn;
        auto* Burst=GetWorld()->SpawnActor<AWardGlassBurst>(Params);
        if(!Burst)return;
        Bursts.Add(Burst);
        Burst->Play(Pane,HitPoint,ShotDirection);
    }
    else
    {
        Bursts[Cursor]->Play(Pane,HitPoint,ShotDirection);
        Cursor=(Cursor+1)%Bursts.Num();
    }
}

void UWardGlassFXSubsystem::Deinitialize()
{
    for(AWardGlassBurst* Burst:Bursts)if(IsValid(Burst))Burst->Destroy();
    Bursts.Empty();Super::Deinitialize();
}
