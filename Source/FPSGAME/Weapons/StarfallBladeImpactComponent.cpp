#include "StarfallBladeImpactComponent.h"
#include "StarfallImpactCameraShake.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInterface.h"
#include "Sound/SoundBase.h"
#include "UObject/ConstructorHelpers.h"

UStarfallBladeImpactComponent::UStarfallBladeImpactComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    // Hard references are resolved with the class, never by a hit-time load.
#define STARFALL_ASSET(Type, Member, Name) \
    { static ConstructorHelpers::FObjectFinder<Type> Asset(TEXT("/Game/Weapons/AzureRunesword20260913/StarfallGuard20261030/ImpactRefinementV2/" Name "." Name)); Member=Asset.Object; }
    STARFALL_ASSET(UStaticMesh,CrystalMesh,"SM_StarfallCrystal");
    STARFALL_ASSET(UStaticMesh,PlaneMesh,"SM_StarfallPlane");
    STARFALL_ASSET(UStaticMesh,ShellMesh,"SM_StarfallShell");
    STARFALL_ASSET(UStaticMesh,WispMesh,"SM_StarfallCross");
    STARFALL_ASSET(UMaterialInterface,CrystalMaterial,"M_StarfallCrystal");
    STARFALL_ASSET(UMaterialInterface,LayerMaterial,"M_StarfallLayers");
    STARFALL_ASSET(UMaterialInterface,ShellMaterial,"M_StarfallShell");
    STARFALL_ASSET(UMaterialInterface,BladeMaterial,"M_StarfallBladeContact");
    STARFALL_ASSET(USoundBase,ImpactSound,"S_StarfallCrystalImpact");
#undef STARFALL_ASSET
}

void UStarfallBladeImpactComponent::Prepare(UStaticMeshComponent* InBlade, UPointLightComponent* InLight)
{
    if(GetNetMode()==NM_DedicatedServer || Crystals || !InBlade || !CrystalMesh || !PlaneMesh || !ShellMesh || !WispMesh
        || !CrystalMaterial || !LayerMaterial || !ShellMaterial || !BladeMaterial)return;
    Blade=InBlade; Light=InLight;
    Blade->SetMaterial(0,BladeMaterial);
    auto Configure=[this](UStaticMeshComponent* Component,UStaticMesh* Mesh,UMaterialInterface* Material)
    {
        GetOwner()->AddInstanceComponent(Component);
        Component->SetupAttachment(GetOwner()->GetRootComponent());
        Component->SetAbsolute(true,true,true);
        Component->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Component->SetCanEverAffectNavigation(false);
        Component->SetCastShadow(false);
        Component->SetReceivesDecals(false);
        Component->SetOwnerNoSee(Blade->bOwnerNoSee);
        Component->SetStaticMesh(Mesh);
        Component->SetMaterial(0,Material);
        Component->SetVisibility(false);
        Component->RegisterComponent();
        Component->SetScalarParameterValueOnMaterials(TEXT("ImpactAge"),0.f);
    };
    Crystals=NewObject<UInstancedStaticMeshComponent>(GetOwner());
    Crystals->SetNumCustomDataFloats(4);
    Configure(Crystals,CrystalMesh,CrystalMaterial);
    Wisps=NewObject<UInstancedStaticMeshComponent>(GetOwner());
    Wisps->SetNumCustomDataFloats(4);
    Configure(Wisps,WispMesh,LayerMaterial);
    Surface=NewObject<UInstancedStaticMeshComponent>(GetOwner());
    Surface->SetNumCustomDataFloats(4);
    Configure(Surface,PlaneMesh,LayerMaterial);
    Shell=NewObject<UStaticMeshComponent>(GetOwner());
    Configure(Shell,ShellMesh,ShellMaterial);
}

bool UStarfallBladeImpactComponent::PlayImpact(const FHitResult& Hit,const FVector& Incoming,float Radius)
{
    if(!Crystals || Age>=0.f)return false;
    Age=0.f; BlastRadius=Radius;
    Normal=Hit.ImpactNormal.GetSafeNormal(UE_SMALL_NUMBER,-Incoming.GetSafeNormal());
    const AActor* Target=Hit.GetActor();
    bSurfaceImpact=!(Target && (Target->IsA<APawn>() || Target->FindComponentByClass<UMonsterCombatComponent>()));
    Origin=Hit.ImpactPoint+Normal*(bSurfaceImpact?2.5f:0.f);
    SurfaceRotation=FRotationMatrix::MakeFromZ(Normal).ToQuat();
    for(UStaticMeshComponent* Component:{static_cast<UStaticMeshComponent*>(Crystals),static_cast<UStaticMeshComponent*>(Wisps),static_cast<UStaticMeshComponent*>(Surface),Shell.Get()})
        Component->SetWorldLocationAndRotation(Origin,FQuat::Identity);
    FRandomStream Random(FMath::Rand());
    auto Direction=[&]()
    {
        FVector D=Random.VRand();
        if(bSurfaceImpact && FVector::DotProduct(D,Normal)<0.f)D=-D;
        return (D+Normal*(bSurfaceImpact?.26f:.06f)).GetSafeNormal();
    };
    auto Add=[&](UInstancedStaticMeshComponent* Component,const FTransform& Transform,float Kind,float Seed,float Delay,float Duration)
    {
        const int32 Index=Component->AddInstance(Transform);
        Component->SetCustomDataValue(Index,0,Kind,false);
        Component->SetCustomDataValue(Index,1,Seed,false);
        Component->SetCustomDataValue(Index,2,Delay,false);
        Component->SetCustomDataValue(Index,3,Duration,true);
    };
    CrystalParticles.Reserve(24); WispParticles.Reserve(50);
    for(int32 I=0;I<24;++I)
    {
        const FVector D=Direction();
        FParticle P;
        const float Size=I<7?Random.FRandRange(4.f,7.5f):Random.FRandRange(1.4f,3.6f);
        P.Initial=FTransform(Random.VRand().Rotation(),D*Random.FRandRange(4.f,12.f),FVector(Size,Size*Random.FRandRange(.65f,1.2f),Size));
        P.Velocity=D*Random.FRandRange(230.f,580.f);
        P.SpinAxis=Random.VRand();P.Spin=Random.FRandRange(-8.f,8.f);
        P.Delay=Random.FRandRange(0.f,.035f);P.Duration=Random.FRandRange(.65f,1.22f);
        Add(Crystals,P.Initial,0.f,Random.FRand(),P.Delay,P.Duration);
        CrystalParticles.Add(P);
    }
    for(int32 I=0;I<50;++I)
    {
        FParticle P; const FVector D=Direction();
        const bool bCore=I==0; const bool bFilament=I>=45;
        const float Size=bCore?Radius*.14f:bFilament?Random.FRandRange(21.f,37.f):Random.FRandRange(.8f,2.f);
        const FVector Scale=bCore||bFilament?FVector(Size):FVector(Size*Random.FRandRange(3.f,7.f),Size*.45f,Size*.45f);
        P.Initial=FTransform(D.Rotation(),bCore?FVector::ZeroVector:D*Random.FRandRange(6.f,24.f),Scale);
        P.Velocity=bCore?FVector::ZeroVector:D*(bFilament?Random.FRandRange(55.f,115.f):Random.FRandRange(400.f,740.f));
        P.SpinAxis=Random.VRand();P.Spin=bFilament?Random.FRandRange(-.8f,.8f):0.f;
        P.Delay=bCore?0.f:Random.FRandRange(0.f,bFilament?.10f:.04f);
        P.Duration=bCore?.085f:bFilament?Random.FRandRange(.8f,1.24f):Random.FRandRange(.22f,.62f);
        P.Growth=bCore?1.25f:bFilament?1.8f:0.f;
        Add(Wisps,P.Initial,bCore?1.f:bFilament?3.f:0.f,Random.FRand(),P.Delay,P.Duration);
        WispParticles.Add(P);
    }
    if(bSurfaceImpact)
    {
        Add(Surface,FTransform(SurfaceRotation,FVector::ZeroVector,FVector(Radius*.035f/.9f)),2.f,Random.FRand(),0.f,.5f);
        Add(Surface,FTransform(SurfaceRotation,Normal*.3f,FVector(Radius*.33f)),4.f,Random.FRand(),.06f,.85f);
        Surface->SetVisibility(true);
    }
    else {Shell->SetWorldScale3D(FVector(Radius*.035f));Shell->SetVisibility(true);}
    Crystals->SetVisibility(true);Wisps->SetVisibility(true);
    Blade->SetVisibility(true); // A phase RepNotify can precede the impact RPC.
    Blade->SetScalarParameterValueOnMaterials(TEXT("ImpactProgress"),-.15f);
    Blade->SetScalarParameterValueOnMaterials(TEXT("MagicGlowStrength"),2.1f);
    if(Light)
    {
        Light->SetWorldLocation(Origin+Normal*12.f);
        Light->SetLightColor(FLinearColor(.10f,.42f,1.f));
        Light->SetAttenuationRadius(Radius*1.25f);Light->SetIntensity(8500.f);
    }
    if(ImpactSound)UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,Hit.ImpactPoint,.8f);
    UGameplayStatics::PlayWorldCameraShake(this,UStarfallImpactCameraShake::StaticClass(),Hit.ImpactPoint,0.f,Radius*2.f,1.5f,false);
    SetComponentTickEnabled(true);
    return true;
}

void UStarfallBladeImpactComponent::TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* Function)
{
    Super::TickComponent(Delta,TickType,Function);
    Age+=Delta;
    if(Age<.11f)Blade->SetScalarParameterValueOnMaterials(TEXT("ImpactProgress"),FMath::Lerp(-.15f,1.15f,FMath::Clamp(Age/.10f,0.f,1.f)));
    else Blade->SetVisibility(false);
    if(Light)Light->SetIntensity(8500.f*FMath::Square(FMath::Clamp(1.f-Age/.14f,0.f,1.f)));
    auto Animate=[this](UInstancedStaticMeshComponent* Component,const TArray<FParticle>& Particles,bool bCrystal)
    {
        Component->SetScalarParameterValueOnMaterials(TEXT("ImpactAge"),Age);
        for(int32 I=0;I<Particles.Num();++I)
        {
            const FParticle& P=Particles[I];
            const float Time=FMath::Clamp(Age-P.Delay,0.f,P.Duration);
            const float Travel=(1.f-FMath::Exp(-2.8f*Time))/2.8f;
            FVector Offset=P.Initial.GetLocation()+P.Velocity*Travel;
            if(bCrystal)
            {
                Offset+=FVector(0,0,-75.f*Time*Time);
                if(bSurfaceImpact)Offset+=Normal*FMath::Max(0.0,2.0-FVector::DotProduct(Offset,Normal));
            }
            const float Growth=1.f+P.Growth*(1.f-FMath::Exp(-5.f*Time));
            const FTransform Transform(FQuat(P.SpinAxis,P.Spin*Time)*P.Initial.GetRotation(),Offset,P.Initial.GetScale3D()*Growth);
            Component->UpdateInstanceTransform(I,Transform,false,I==Particles.Num()-1,true);
        }
    };
    Animate(Crystals,CrystalParticles,true);Animate(Wisps,WispParticles,false);
    const float T=FMath::Clamp(Age/.30f,0.f,1.f);
    const float Radius=BlastRadius*FMath::InterpEaseOut(.035f,1.f,T,2.f);
    if(bSurfaceImpact)
    {
        Surface->SetScalarParameterValueOnMaterials(TEXT("ImpactAge"),Age);
        Surface->UpdateInstanceTransform(0,FTransform(SurfaceRotation,FVector::ZeroVector,FVector(Radius/.9f)),false,true,true);
        if(Age>=.94f)Surface->SetVisibility(false);
    }
    else
    {
        Shell->SetWorldScale3D(FVector(Radius));
        Shell->SetScalarParameterValueOnMaterials(TEXT("ImpactAge"),Age);
        if(Age>=.5f)Shell->SetVisibility(false);
    }
    if(Age>=Lifetime)
    {
        Crystals->SetVisibility(false);Wisps->SetVisibility(false);
        Surface->SetVisibility(false);Shell->SetVisibility(false);
        if(Light)Light->SetIntensity(0.f);
        SetComponentTickEnabled(false);
    }
}
