#include "CastingToolRackComponent.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"

namespace
{
    constexpr float HookX[4]={8.f,27.f,43.f,57.f};
    constexpr float Frequency[4]={.86f,1.02f,.95f,.79f};
    constexpr float Damping[4]={.46f,.67f,.39f,.42f};
    constexpr float RackResponse[4]={.72f,.34f,1.f,.80f};
    constexpr float RackSideLimit[4]={3.8f,2.4f,4.5f,3.2f};

    void SwapMeshKeepingMaterials(UStaticMeshComponent* Component,UStaticMesh* Mesh)
    {
        // FBX reimports may compact unused slots; transfer overrides by slot name, not index.
        TArray<TPair<FName,UMaterialInterface*>> Materials;
        if(const UStaticMesh* Previous=Component->GetStaticMesh())
            for(int32 Index=0;Index<Previous->GetStaticMaterials().Num();++Index)
                Materials.Emplace(Previous->GetStaticMaterials()[Index].MaterialSlotName,Component->GetMaterial(Index));
        Component->SetStaticMesh(Mesh);
        Component->EmptyOverrideMaterials();
        for(const auto& Material:Materials)
        {
            const int32 Index=Mesh->GetMaterialIndex(Material.Key);
            if(Index!=INDEX_NONE)Component->SetMaterial(Index,Material.Value);
        }
    }

    // Like the PKM carry handle: spring, damping, soft stop and a low-restitution hard stop.
    void Advance(double& Angle,double& Speed,double Target,double Omega,double Zeta,double Limit,double Dt)
    {
        const double Soft=Limit*.8;
        const double Stop=FMath::Max(0.,Angle-Soft)-FMath::Max(0.,-Angle-Soft);
        Speed+=(Omega*Omega*(Target-Angle)-2.*Zeta*Omega*Speed-160.*Stop)*Dt;
        Angle+=Speed*Dt;
        if(FMath::Abs(Angle)>Limit)
        {
            Angle=FMath::Clamp(Angle,-Limit,Limit);
            if(Angle*Speed>0.)Speed*=-.08;
        }
    }
}

UCastingToolRackComponent::UCastingToolRackComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickInterval=1.f/60.f;
    PrimaryComponentTick.TickGroup=TG_PostPhysics;
    for(const TCHAR* Name:{TEXT("SM_CastingStationBareRack"),TEXT("SM_RackTongs"),
        TEXT("SM_RackHammer"),TEXT("SM_RackFile"),TEXT("SM_RackPoker")})
        RackAssets.Add(TSoftObjectPtr<UStaticMesh>(FSoftObjectPath(FString::Printf(
            TEXT("/Game/Props/CastingStation20260926/%s.%s"),Name,Name))));
}

void UCastingToolRackComponent::Configure(UStaticMeshComponent* Station)
{
    if(!Station||AssetLoad||!GetWorld()||!GetWorld()->IsGameWorld())return;
    Body=Station;OriginalMesh=Station->GetStaticMesh();
    TArray<FSoftObjectPath> Paths;
    for(const auto& Asset:RackAssets)Paths.Add(Asset.ToSoftObjectPath());
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateUObject(this,&UCastingToolRackComponent::AssetsReady));
}

void UCastingToolRackComponent::AssetsReady()
{
    auto* Station=Body.Get();
    if(!Station||Station->IsSimulatingPhysics()||Station->GetStaticMesh()!=OriginalMesh)return;
    for(const auto& Asset:RackAssets)if(!Asset.Get())return;
    // Retain water MIDs and other overrides when replacing the merged preview mesh.
    SwapMeshKeepingMaterials(Station,RackAssets[0].Get());
    for(int32 Index=0;Index<4;++Index)
    {
        auto* Tool=NewObject<UStaticMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        GetOwner()->AddInstanceComponent(Tool);
        Tool->SetMobility(EComponentMobility::Movable);
        Tool->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Tool->SetGenerateOverlapEvents(false);
        Tool->SetCanEverAffectNavigation(false);
        Tool->SetStaticMesh(RackAssets[Index+1].Get());
        Tool->SetupAttachment(Station);
        // Authored origin = eye inner rim against the underside of the fixed hook.
        Tool->SetRelativeLocation(FVector(HookX[Index],44.f,94.30f));
        Tool->RegisterComponent();
        HangingTools.Add(Tool);
    }
    ResetMotion();
    SetComponentTickEnabled(true);
}

void UCastingToolRackComponent::ResetMotion()
{
    for(int32 Index=0;Index<4;++Index)
    {
        Angles[Index]=Speeds[Index]=FVector2D::ZeroVector;
        if(HangingTools.IsValidIndex(Index)&&HangingTools[Index])
            HangingTools[Index]->SetRelativeRotation(FQuat::Identity);
    }
    LocalWind=FVector::ZeroVector;WindClock=.2f;
    if(Body.IsValid())LastMount=Body->GetComponentTransform();
    bMotionReady=false;
}

void UCastingToolRackComponent::TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick)
{
    Super::TickComponent(Delta,TickType,ThisTick);
    auto* Station=Body.Get();
    if(!Station||Station->IsSimulatingPhysics())
    {
        // Detached building pieces keep their rigid tool attachments, without cosmetic forces.
        SetComponentTickEnabled(false);return;
    }
    const FTransform Mount=Station->GetComponentTransform();
    auto* Controller=GetWorld()->GetFirstPlayerController();
    FVector Eye;FRotator View;
    if(Controller)Controller->GetPlayerViewPoint(Eye,View);
    const bool bNear=Controller&&FVector::DistSquared(Eye,Mount.GetLocation())<FMath::Square(3000.);
    SetComponentTickInterval(bNear?1.f/60.f:.5f);
    if(!bNear||!Station->IsVisible())
    {
        if(bMotionReady)ResetMotion();
        return;
    }
    if(Delta>.25f||FVector::DistSquared(Mount.GetLocation(),LastMount.GetLocation())>FMath::Square(80.)
        ||Mount.GetRotation().AngularDistance(LastMount.GetRotation())>.5)
        ResetMotion();
    LastMount=Mount;bMotionReady=true;
    WindClock+=Delta;
    if(WindClock>=.2f)
    {
        WindClock=0;
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
            LocalWind=Mount.InverseTransformVectorNoScale(
                Fluid->WindWithGustAt(Mount.TransformPosition(FVector(32,44,94.3))));
    }
    // Small pressure fluctuations scale the shared wind, never create a different direction.
    const double Time=GetWorld()->GetTimeSeconds();
    const double Buffeting=1.+.14*FMath::Sin(Time*1.73)+.08*FMath::Sin(Time*2.79);
    const double Side=FMath::Clamp(LocalWind.X*FMath::Abs(LocalWind.X)*.00035,-4.,4.)*Buffeting;
    const double Depth=FMath::Clamp(LocalWind.Y*FMath::Abs(LocalWind.Y)*.00019,-2.,2.)*Buffeting;
    const double Duration=FMath::Clamp(double(Delta),0.,.06);
    const int32 Steps=FMath::Max(1,FMath::CeilToInt(Duration*240.));
    const double Dt=Duration/Steps;
    for(int32 Index=0;Index<4;++Index)
    {
        const double Omega=2.*PI*Frequency[Index];
        for(int32 Step=0;Step<Steps;++Step)
        {
            Advance(Angles[Index].X,Speeds[Index].X,Side*RackResponse[Index],Omega,Damping[Index],RackSideLimit[Index],Dt);
            Advance(Angles[Index].Y,Speeds[Index].Y,Depth*RackResponse[Index],Omega,Damping[Index]+.1,2.4,Dt);
        }
        // For a hanging -Z lever, positive X rotation moves its tip toward +Y.
        const FQuat AlongRail(FVector::YAxisVector,FMath::DegreesToRadians(-Angles[Index].X));
        const FQuat AcrossRail(FVector::XAxisVector,FMath::DegreesToRadians(Angles[Index].Y));
        HangingTools[Index]->SetRelativeRotation(AlongRail*AcrossRail);
    }
}

void UCastingToolRackComponent::OnComponentDestroyed(bool bDestroyingHierarchy)
{
    SetComponentTickEnabled(false);
    if(AssetLoad)AssetLoad->CancelHandle();
    for(UStaticMeshComponent* Tool:HangingTools)if(IsValid(Tool))Tool->DestroyComponent();
    HangingTools.Empty();
    if(auto* Station=Body.Get();Station&&OriginalMesh&&Station->GetStaticMesh()==RackAssets[0].Get())
        SwapMeshKeepingMaterials(Station,OriginalMesh);
    AssetLoad.Reset();Body.Reset();OriginalMesh=nullptr;
    Super::OnComponentDestroyed(bDestroyingHierarchy);
}
