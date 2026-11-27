#include "PlayerSkillRenderPreparation.h"
#include "Animation/AnimSequence.h"
#include "Components/DecalComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstanceController.h"
#include "Particles/ParticleSystem.h"
#include "Sound/SoundBase.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/UnrealType.h"
#include "RHIGlobals.h"

FPlayerSkillRenderPreparation::~FPlayerSkillRenderPreparation()
{
    if(WarmHost.IsValid())WarmHost->Destroy();
}

AActor* FPlayerSkillRenderPreparation::Host(UWorld* World)
{
    if(WarmHost.IsValid())return WarmHost.Get();
    FActorSpawnParameters Spawn;Spawn.ObjectFlags|=RF_Transient;
    auto* Owner=World->SpawnActor<AActor>(Spawn);
    if(!Owner)return nullptr;
    Owner->SetActorHiddenInGame(true);Owner->SetActorEnableCollision(false);Owner->SetActorTickEnabled(false);
    // Native spline effects resolve their source from this root, without
    // spawning a spell actor or invoking any gameplay/replication callbacks.
    auto* Spline=NewObject<USplineComponent>(Owner);Owner->AddInstanceComponent(Spline);Owner->SetRootComponent(Spline);
    Spline->SetCollisionEnabled(ECollisionEnabled::NoCollision);Spline->SetCanEverAffectNavigation(false);
    Spline->ClearSplinePoints(false);Spline->AddSplinePoint(FVector::ZeroVector,ESplineCoordinateSpace::Local,false);
    Spline->AddSplinePoint(FVector(100,0,0),ESplineCoordinateSpace::Local,true);Spline->RegisterComponent();
    WarmHost=Owner;return Owner;
}

void FPlayerSkillRenderPreparation::SkipCurrent()
{
    if(auto* Component=CurrentComponent.Get())
    {
        if(auto* Owner=Component->GetOwner())Owner->RemoveInstanceComponent(Component);
        Component->DestroyComponent();
    }
    CurrentComponent.Reset();CurrentAsset.Reset();AssetPreparation.Reset();bActivated=false;
}

bool FPlayerSkillRenderPreparation::Tick(UObject* Asset,UWorld* World,bool bAllowRepresentative,bool& bDeferred)
{
    bDeferred=false;
    if(!Asset||!World)return true;
    // Headless worlds still load assets and deliver gameplay consumer bindings,
    // but cannot render/advance these hidden GPU representatives. Compiling and
    // activating them here caused entry hitches followed by readiness timeouts.
    if(GUsingNullRHI || World->GetNetMode()==NM_DedicatedServer)
    {SkipCurrent();return true;}
    if(CurrentAsset.Get()!=Asset)
    {
        // Actual skills own separate runtime components. A completed hidden
        // representative must not retain a second set of GPU buffers until travel.
        SkipCurrent();CurrentAsset=Asset;
    }
    if(auto* System=Cast<UNiagaraSystem>(Asset))
    {
        // Dragon Breath and StormDomainV4 own real, reusable volumes on the caster. Never
        // allocate a second fluid grid as a generic preparation representative.
        if(System->GetPathName().Contains(TEXT("/DragonBreath20261013/"))||
            System->GetPathName().Contains(TEXT("/StormDomainV4/NS_StormDomainVolume")))return true;
        if(!AssetPreparation.PollScripts(System))return false;
        if(!bAllowRepresentative){SkipCurrent();bDeferred=true;return true;}
        auto* FX=Cast<UNiagaraComponent>(CurrentComponent.Get());
        if(!FX)
        {
            auto* Owner=Host(World);if(!Owner)return false;
            AssetPreparation.RequestPSOs(System);
            FX=NewObject<UNiagaraComponent>(Owner);Owner->AddInstanceComponent(FX);FX->SetupAttachment(Owner->GetRootComponent());
            FX->SetAutoActivate(false);FX->SetAutoDestroy(false);FX->SetAsset(System);
            // UE 5.8 exposes these instance overrides as reflected properties,
            // without C++ setters. Prevent authored synchronous warmup loops on
            // this representative; actual spell components keep their settings.
            if(auto* Override=FindFProperty<FBoolProperty>(UNiagaraComponent::StaticClass(),TEXT("bOverrideWarmupSettings")))Override->SetPropertyValue_InContainer(FX,true);
            if(auto* Count=FindFProperty<FIntProperty>(UNiagaraComponent::StaticClass(),TEXT("WarmupTickCount")))Count->SetPropertyValue_InContainer(FX,0);
            FX->SetAllowScalability(false);FX->SetVisibility(false);FX->SetRenderingEnabled(false);
            FX->SetCastShadow(false);FX->SetCanEverAffectNavigation(false);
            FX->SetSystemFixedBounds(FBox(FVector(-512),FVector(512)));
            FX->RegisterComponent();FX->PrecachePSOs();CurrentComponent=FX;return false;
        }
        if(FX->IsPSOPrecaching())return false;
        if(!bActivated){FX->Activate(false);bActivated=true;return false;}
        const auto Instance=FX->GetSystemInstanceController();
        if(FX->IsComplete())return Instance&&Instance->GetAge()>0.f; // Must actually have run, not merely be awaiting activation.
        if(!Instance||Instance->IsPendingSpawn()||!Instance->GetAreDataInterfacesInitialized()||Instance->GetAge()<.10f)return false;
        FX->SetPaused(true);return true;
    }
    if(auto* Sound=Cast<USoundBase>(Asset))
    {UGameplayStatics::PrimeSound(Sound);return true;}
    if(auto* Cascade=Cast<UParticleSystem>(Asset))
    {
        return AssetPreparation.PollPSOs(Cascade);
    }
#if WITH_EDITOR
    // UE 5.8 keeps IsCompiling protected; poll the public usable-data state
    // without blocking this preparation tick on animation compression.
    if(auto* Animation=Cast<UAnimSequence>(Asset))return Animation->IsCompressedDataValid();
    if(auto* Mesh=Cast<UStaticMesh>(Asset);Mesh&&Mesh->IsCompiling())return false;
    if(auto* Mesh=Cast<USkeletalMesh>(Asset);Mesh&&Mesh->IsCompiling())return false;
    if(auto* Material=Cast<UMaterialInterface>(Asset);Material&&Material->GetMaterial()->IsCompiling())return false;
#endif
    if(!Asset->IsA<UStaticMesh>()&&!Asset->IsA<USkeletalMesh>()&&!Asset->IsA<UMaterialInterface>())return true;
    if(!bAllowRepresentative){SkipCurrent();bDeferred=true;return true;}
    if(auto* Primitive=Cast<UPrimitiveComponent>(CurrentComponent.Get()))return !Primitive->IsPSOPrecaching();
    if(auto* Decal=Cast<UDecalComponent>(CurrentComponent.Get()))return !Decal->GetPSOPrecacheComponentData().IsPSOPrecaching();
    auto* Owner=Host(World);if(!Owner)return false;
    USceneComponent* Component=nullptr;
    if(auto* Material=Cast<UMaterialInterface>(Asset))
    {
        const auto Domain=Material->GetMaterial()->MaterialDomain;
        if(Domain==MD_DeferredDecal)
        {auto* Decal=NewObject<UDecalComponent>(Owner);Decal->SetDecalMaterial(Material);Component=Decal;}
        else if(Domain==MD_Surface)
        {
            auto* Plane=Cast<UStaticMesh>(FSoftObjectPath(TEXT("/Engine/BasicShapes/Plane.Plane")).ResolveObject());
            if(!Plane)return false;
            auto* Mesh=NewObject<UStaticMeshComponent>(Owner);Mesh->SetStaticMesh(Plane);Mesh->SetMaterial(0,Material);Component=Mesh;
        }
        else return true; // Post-process resources initialize on package load; no scene mesh permutation.
    }
    else if(auto* AssetMesh=Cast<UStaticMesh>(Asset))
    {auto* Mesh=NewObject<UStaticMeshComponent>(Owner);Mesh->SetStaticMesh(AssetMesh);Component=Mesh;}
    else if(auto* SkeletalAsset=Cast<USkeletalMesh>(Asset))
    {auto* Mesh=NewObject<USkeletalMeshComponent>(Owner);Mesh->SetSkeletalMesh(SkeletalAsset);Component=Mesh;}
    if(!Component)return true;
    Owner->AddInstanceComponent(Component);Component->SetupAttachment(Owner->GetRootComponent());
    Component->SetVisibility(false);Component->SetCanEverAffectNavigation(false);
    if(auto* Primitive=Cast<UPrimitiveComponent>(Component))
    {Primitive->SetCollisionEnabled(ECollisionEnabled::NoCollision);Primitive->SetCastShadow(false);}
    Component->RegisterComponent();
    Component->SetComponentTickEnabled(false);
    if(auto* Primitive=Cast<UPrimitiveComponent>(Component))Primitive->PrecachePSOs();
    else if(auto* Decal=Cast<UDecalComponent>(Component))Decal->PrecachePSOs();
    CurrentComponent=Component;return false;
}
