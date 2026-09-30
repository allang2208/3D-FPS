#include "FPSShatterFXSubsystem.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/PointLightComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInstanceDynamic.h"

namespace ShatterVFX
{
    static TAutoConsoleVariable<int32> Enabled(TEXT("fps.ShatterFX"),1,TEXT("Violet shatter presentation; does not change ricochet damage."));
    static TAutoConsoleVariable<float> Emission(TEXT("fps.ShatterFX.Emission"),1.6f,TEXT("Violet trace emission; saturation is retained by a separate pale core."));
    static TAutoConsoleVariable<float> Width(TEXT("fps.ShatterFX.WidthCM"),2.8f,TEXT("Base core diameter in cm, with bounded screen-size compensation."));
    static TAutoConsoleVariable<float> Hold(TEXT("fps.ShatterFX.HoldSeconds"),.04f,TEXT("Stationary trace hold after real projectile termination."));
    static TAutoConsoleVariable<float> Fade(TEXT("fps.ShatterFX.FadeSeconds"),.16f,TEXT("Trace fade after its hold; no simulation slowdown."));
    const FLinearColor Violet(.30f,.065f,1.f);
}

bool UFPSShatterFXSubsystem::DoesSupportWorldType(EWorldType::Type Type) const
{return Type==EWorldType::Game||Type==EWorldType::PIE;}
TStatId UFPSShatterFXSubsystem::GetStatId() const
{RETURN_QUICK_DECLARE_CYCLE_STAT(FPSShatterFX,STATGROUP_Tickables);}

void UFPSShatterFXSubsystem::OnWorldBeginPlay(UWorld& World)
{
    Super::OnWorldBeginPlay(World);
    if(World.GetNetMode()==NM_DedicatedServer)return;
    const TArray<FSoftObjectPath> Paths={MaterialAsset.ToSoftObjectPath(),CrystalAsset.ToSoftObjectPath(),CylinderAsset.ToSoftObjectPath(),PlaneAsset.ToSoftObjectPath()};
    AssetLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this](){Prepare();AssetLoad.Reset();}));
}

void UFPSShatterFXSubsystem::Prepare()
{
    if(bReady||!MaterialAsset.Get()||!CrystalAsset.Get()||!CylinderAsset.Get()||!PlaneAsset.Get())return;
    // Four fixed instance batches share the entire world's visual budget. No
    // component creation, material loads or mesh rebuilds in a combat callback.
    const int32 Counts[GroupCount]={BeamCount,BeamCount,ShardCount,FlareCount};
    for(int32 G=0;G<GroupCount;++G)
    {
        auto* R=NewObject<UInstancedStaticMeshComponent>(this);
        R->SetMobility(EComponentMobility::Movable);
        R->SetStaticMesh(G==ShardGroup?CrystalAsset.Get():G==FlareGroup?PlaneAsset.Get():CylinderAsset.Get());
        auto* MID=UMaterialInstanceDynamic::Create(MaterialAsset.Get(),this);
        MID->SetScalarParameterValue(TEXT("Layer"),G==ShardGroup?3.f:G==FlareGroup?2.f:float(G));
        MID->SetVectorParameterValue(TEXT("Tint"),ShatterVFX::Violet);
        MID->SetScalarParameterValue(TEXT("Emission"),G==HaloGroup?.35f:G==FlareGroup?2.f:1.6f);
        R->SetMaterial(0,MID);
        R->SetCollisionEnabled(ECollisionEnabled::NoCollision);R->SetGenerateOverlapEvents(false);
        R->SetCanEverAffectNavigation(false);R->SetCastShadow(false);
        R->bReceivesDecals=false;R->bAffectDistanceFieldLighting=false;
        R->SetVisibleInRayTracing(false);
        R->SetNumCustomDataFloats(3);
        Transforms[G].Init(FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),Counts[G]);
        R->PreAllocateInstancesMemory(Counts[G]);R->AddInstances(Transforms[G],false,true,false);
        R->RegisterComponentWithWorld(GetWorld());
        Renderers.Add(R);Materials.Add(MID);
    }
    for(int32 I=0;I<2;++I)
    {
        auto* L=NewObject<UPointLightComponent>(this);
        L->SetMobility(EComponentMobility::Movable);L->SetCastShadows(false);
        L->SetLightColor(ShatterVFX::Violet);L->SetIntensityUnits(ELightUnits::Lumens);
        L->SetAttenuationRadius(160.f);L->SetSourceRadius(3.f);
        L->SetIndirectLightingIntensity(0.f);L->SetVolumetricScatteringIntensity(0.f);
        L->SetVisibility(false);L->RegisterComponentWithWorld(GetWorld());Lights.Add(L);
    }
    bReady=true;
}

void UFPSShatterFXSubsystem::Write(int32 G,int32 I,const FTransform& Transform,float Alpha,float Length,float Age)
{
    Transforms[G][I]=Transform;
    Renderers[G]->SetCustomDataValue(I,0,Alpha,false);
    Renderers[G]->SetCustomDataValue(I,1,Length,false);
    Renderers[G]->SetCustomDataValue(I,2,Age,false);
    Dirty[G]=true;
}
void UFPSShatterFXSubsystem::Hide(int32 G,int32 I)
{Write(G,I,FTransform(FQuat::Identity,FVector::ZeroVector,FVector::ZeroVector),0.f);}

int32 UFPSShatterFXSubsystem::MoteSlot(FMote* Pool,int32 Count) const
{
    int32 Oldest=0;
    for(int32 I=0;I<Count;++I)
    {if(!Pool[I].Active)return I;if(Pool[I].Born<Pool[Oldest].Born)Oldest=I;}
    return Oldest;
}
void UFPSShatterFXSubsystem::SpawnMote(bool bShard,const FVector& Point,const FVector& Velocity,float Scale,float Life,float Strength)
{
    FMote* Pool=bShard?Shards:Flares;
    auto& P=Pool[MoteSlot(Pool,bShard?ShardCount:FlareCount)];
    P.Origin=Point;P.Velocity=Velocity;P.Born=GetWorld()->GetTimeSeconds();
    P.Life=Life;P.Strength=Strength;P.Active=true;
    P.Rotation=bShard?FRotationMatrix::MakeFromZ(Velocity.GetSafeNormal()).Rotator():FRotator::ZeroRotator;
    P.Spin=FRotator(Random.FRandRange(-500,500),Random.FRandRange(-700,700),Random.FRandRange(-500,500));
    P.Size=bShard?FVector(Random.FRandRange(1.6f,3.1f),Random.FRandRange(2.f,3.8f),Random.FRandRange(7.f,17.f))*Scale
        :FVector(Scale,Scale,Scale);
}

void UFPSShatterFXSubsystem::Burst(const FVector& Point,const FVector& Normal,EShatterBurst Kind)
{
    if(!bReady||ShatterVFX::Enabled.GetValueOnGameThread()==0)return;
    const bool bArrival=Kind==EShatterBurst::Arrival;
    const float Scale=Kind==EShatterBurst::Kill?1.f:bArrival?.56f:.72f;
    const int32 Count=Kind==EShatterBurst::Kill?16:bArrival?5:9;
    const FVector Facing=Normal.IsNearlyZero()?FVector::UpVector:Normal.GetSafeNormal();
    const FVector Origin=Point+Facing*2.f;
    SpawnMote(false,Origin,FVector::ZeroVector,60.f*Scale,.15f,1.f);
    for(int32 I=0;I<Count;++I)
    {
        const FVector Direction=(Random.VRand()+Facing*.28f+FVector::UpVector*.12f).GetSafeNormal();
        SpawnMote(true,Origin,Direction*Random.FRandRange(110,340)*Scale,Scale,Random.FRandRange(.25f,.4f),Random.FRandRange(.65f,1.f));
    }
    for(int32 I=0;I<(bArrival?2:5);++I)
        SpawnMote(false,Origin,Random.VRand()*Random.FRandRange(40,125)*Scale,Random.FRandRange(3,6)*Scale,.32f,.55f);
    // Only originating bursts borrow the two tiny world lights. A many-target
    // kill never creates a light per victim or a stack of origin flashes.
    if(!bArrival)
    {
        const int32 I=Pulses[0].Born<Pulses[1].Born?0:1;
        Pulses[I]={Origin,GetWorld()->GetTimeSeconds(),Scale};
    }
    bActive=true;
}

void UFPSShatterFXSubsystem::Trace(UObject* Source,int32 Id,const FVector& Start,const FVector& End,bool bFinished)
{
    if(!bReady||!Source||ShatterVFX::Enabled.GetValueOnGameThread()==0||FVector::DistSquared(Start,End)<.01f)return;
    int32 Found=INDEX_NONE,Free=INDEX_NONE,Oldest=0;
    for(int32 I=0;I<BeamCount;++I)
    {
        if(Beams[I].Active&&Beams[I].Source.Get()==Source&&Beams[I].Id==Id){Found=I;break;}
        if(!Beams[I].Active&&Free==INDEX_NONE)Free=I;
        if(Beams[I].Born<Beams[Oldest].Born)Oldest=I;
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(Found==INDEX_NONE)
    {
        Found=Free==INDEX_NONE?Oldest:Free;
        auto& B=Beams[Found];B=FBeam{};B.Source=Source;B.Id=Id;B.Origin=Start;B.Born=Now;B.Active=true;
    }
    auto& B=Beams[Found];B.Head=End;
    if(bFinished&&!B.Finished){B.Finished=true;B.Ended=Now;}
    bActive=true;
}
void UFPSShatterFXSubsystem::EndTrace(UObject* Source,int32 Id)
{
    for(auto& B:Beams)if(B.Active&&B.Source.Get()==Source&&B.Id==Id&&!B.Finished)
    {B.Finished=true;B.Ended=GetWorld()->GetTimeSeconds();break;}
}

void UFPSShatterFXSubsystem::Tick(float DeltaTime)
{
    const double Now=GetWorld()->GetTimeSeconds();
    const bool bEnabled=ShatterVFX::Enabled.GetValueOnGameThread()!=0;
    FVector Eye=FVector::ZeroVector;FRotator View=FRotator::ZeroRotator;
    float FOV=90.f;int32 Width=1920,Height=1080;
    if(auto* PC=GetWorld()->GetFirstPlayerController())
    {PC->GetPlayerViewPoint(Eye,View);PC->GetViewportSize(Width,Height);if(PC->PlayerCameraManager)FOV=PC->PlayerCameraManager->GetFOVAngle();}
    const float CMPerDepthPixel=2.f*FMath::Tan(FMath::DegreesToRadians(FOV*.5f))/FMath::Max(1,Width);
    const float Hold=FMath::Clamp(ShatterVFX::Hold.GetValueOnGameThread(),0.f,.3f);
    const float Fade=FMath::Clamp(ShatterVFX::Fade.GetValueOnGameThread(),.01f,.5f);
    Materials[CoreGroup]->SetScalarParameterValue(TEXT("Emission"),FMath::Clamp(ShatterVFX::Emission.GetValueOnGameThread(),0.f,6.f));
    bActive=false;
    for(int32 I=0;I<BeamCount;++I)
    {
        auto& B=Beams[I];if(!B.Active)continue;
        if(!B.Source.IsValid()&&!B.Finished){B.Finished=true;B.Ended=Now;}
        const float Age=B.Finished?float(Now-B.Ended):0.f;
        if(!bEnabled||(B.Finished&&Age>=Hold+Fade))
        {B.Active=false;Hide(CoreGroup,I);Hide(HaloGroup,I);continue;}
        const float Alpha=Age<=Hold?1.f:FMath::Pow(FMath::Clamp(1.f-(Age-Hold)/Fade,0.f,1.f),1.7f);
        const FVector Span=B.Head-B.Origin,Center=(B.Head+B.Origin)*.5f;
        const float Length=Span.Size();
        const float Depth=FMath::Max(1.f,float(FVector::DotProduct(Center-Eye,View.Vector())));
        const float Diameter=FMath::Clamp(FMath::Max(ShatterVFX::Width.GetValueOnGameThread(),Depth*CMPerDepthPixel*1.5f),.8f,6.f);
        const FQuat Rotation=FRotationMatrix::MakeFromZ(Span).ToQuat();
        Write(CoreGroup,I,FTransform(Rotation,Center,FVector(Diameter,Diameter,Length)/100.f),Alpha,Length,Age);
        Write(HaloGroup,I,FTransform(Rotation,Center,FVector(Diameter*3.5f,Diameter*3.5f,Length)/100.f),Alpha*.36f,Length,Age);
        bActive=true;
    }
    for(int32 G=ShardGroup;G<=FlareGroup;++G)
    {
        FMote* Pool=G==ShardGroup?Shards:Flares;
        const int32 Count=G==ShardGroup?ShardCount:FlareCount;
        for(int32 I=0;I<Count;++I)
        {
            auto& P=Pool[I];if(!P.Active)continue;
            const float Age=FMath::Max(0.f,float(Now-P.Born));
            if(!bEnabled||Age>=P.Life){P.Active=false;Hide(G,I);continue;}
            const float T=Age/P.Life;
            const FVector At=P.Origin+P.Velocity*((1.f-FMath::Exp(-4.f*Age))/4.f)-FVector(0,0,55.f*Age*Age);
            const bool bShard=G==ShardGroup;
            const FQuat Rotation=bShard?(P.Rotation+P.Spin*Age).Quaternion():FRotationMatrix::MakeFromZ(Eye-At).ToQuat();
            const float Growth=bShard?1.f:1.f+Age*2.f;
            const float Alpha=P.Strength*(bShard?FMath::Pow(1.f-T,1.5f):FMath::Pow(1.f-T,2.2f));
            Write(G,I,FTransform(Rotation,At,P.Size*(Growth/100.f)),Alpha,0,Age);
            bActive=true;
        }
    }
    for(int32 I=0;I<2;++I)
    {
        const float Age=float(Now-Pulses[I].Born);
        const bool bLit=bEnabled&&Pulses[I].Strength>0.f&&Age<.13f;
        Lights[I]->SetVisibility(bLit);
        if(bLit){Lights[I]->SetWorldLocation(Pulses[I].Position);Lights[I]->SetIntensity(65.f*Pulses[I].Strength*FMath::Exp(-Age*28.f));bActive=true;}
    }
    for(int32 G=0;G<GroupCount;++G)if(Dirty[G])
    {Renderers[G]->BatchUpdateInstancesTransforms(0,Transforms[G],true,true,true);Dirty[G]=false;}
}

void UFPSShatterFXSubsystem::Deinitialize()
{
    bReady=false;bActive=false;
    if(AssetLoad){AssetLoad->CancelHandle();AssetLoad.Reset();}
    for(const auto& R:Renderers)if(IsValid(R))R->DestroyComponent();
    for(const auto& L:Lights)if(IsValid(L))L->DestroyComponent();
    Renderers.Reset();Materials.Reset();Lights.Reset();
    Super::Deinitialize();
}
