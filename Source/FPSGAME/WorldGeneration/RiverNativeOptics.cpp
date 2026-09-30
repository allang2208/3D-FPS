#include "RiverPilotFXSubsystem.h"
#include "FluidPresentationSubsystem.h"
#include "TemperateHillsWorld.h"
#include "WaterImpactFootprints.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/WorldSettings.h"
#include "Materials/MaterialInstanceDynamic.h"

void URiverPilotFXSubsystem::BeginNativeOptics()
{
    UWorld* World=GetWorld();
    LastNativeUpdate=World->GetTimeSeconds();
    NativeLightSpawnHandle=World->AddOnActorSpawnedHandler(
        FOnActorSpawned::FDelegate::CreateUObject(this,&URiverPilotFXSubsystem::RegisterNativeWaterLight));
    NativeUnderwaterLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        NativeUnderwaterTemplate.ToSoftObjectPath(),FStreamableDelegate::CreateWeakLambda(this,[this]()
        {PrepareNativeUnderwater();NativeUnderwaterLoad.Reset();}));
    World->GetTimerManager().SetTimer(NativeOpticsTimer,this,&URiverPilotFXSubsystem::UpdateNativeOptics,1.f/30.f,true);
}

void URiverPilotFXSubsystem::RegisterNativeWaterLight(AActor* Actor)
{
    if(!Actor)return;
    NativeLights.RemoveAll([](const auto& Light){return !Light.IsValid();});
    TInlineComponentArray<UDirectionalLightComponent*> Lights(Actor);
    for(auto* Light:Lights)
    {
        if(NativeLights.Contains(Light))continue;
        if(NativeLights.Num()<8)NativeLights.Add(Light);
    }
}

void URiverPilotFXSubsystem::PrepareNativeUnderwater()
{
    auto* Parent=NativeUnderwaterTemplate.Get();
    if(!Parent||NativeUnderwaterVolume||!GetWorld())return;
    NativeUnderwaterMID=UMaterialInstanceDynamic::Create(Parent,this);
    NativeUnderwaterMID->SetScalarParameterValue(TEXT("UnderwaterAmount"),1.f);
    auto* Owner=GetWorld()->GetWorldSettings();
    NativeUnderwaterVolume=NewObject<UPostProcessComponent>(Owner,NAME_None,RF_Transient);
    Owner->AddInstanceComponent(NativeUnderwaterVolume);
    NativeUnderwaterVolume->bUnbound=true;
    NativeUnderwaterVolume->Priority=90.f;
    NativeUnderwaterVolume->BlendWeight=0;
    NativeUnderwaterVolume->Settings.WeightedBlendables.Array.Add(FWeightedBlendable(1.f,NativeUnderwaterMID.Get()));
    NativeUnderwaterVolume->RegisterComponent();
}

bool URiverPilotFXSubsystem::FindNativeImmersion(const FVector& View,FFluidWaterContact& Contact) const
{
    bool Found=false;
    double NearestDepth=DBL_MAX;
    // The river's immutable spatial index and actual generated floor define its volume.
    if(OwnerRiver.IsValid()&&RiverPlan&&WaterMID)
    {
        const auto Sample=RiverPlan->Sample(View.X,View.Y);
        const double Depth=Sample.WaterZ-View.Z;
        if(Sample.Distance<Sample.HalfWidth&&Depth>0&&Depth<=400
            &&View.Z>OwnerRiver->Height(View.X,View.Y))
        {
            Contact.Position=FVector(View.X,View.Y,Sample.WaterZ);
            Contact.Normal=FVector::UpVector;
            Contact.Material=WaterMID;
            Contact.Depth=Depth;
            Contact.Static=false;
            NearestDepth=Depth;Found=true;
        }
    }
    for(const auto& Surface:StaticSurfaces)
    {
        const auto* Component=Surface.Component.Get();
        if(Surface.ImmersionDepthCm<=0||!Component||!Surface.Material.IsValid()
            ||!Component->IsRegistered()||!Component->IsVisible()||Component->GetOwner()->IsHidden())continue;
        const auto& Transform=Component->GetComponentTransform();
        const FVector Local=Transform.InverseTransformPosition(View);
        const FVector2D XY(Local);
        for(const auto& Patch:Surface.Footprint->Patches)
        {
            const double LocalDepth=Patch.Z-Local.Z;
            if(LocalDepth<=0||LocalDepth>Surface.ImmersionDepthCm||!Patch.Bounds.IsInsideOrOn(XY))continue;
            bool Inside=false;
            for(int32 I=0,J=Patch.Polygon.Num()-1;I<Patch.Polygon.Num();J=I++)
            {
                const auto& A=Patch.Polygon[I];const auto& B=Patch.Polygon[J];
                if((A.Y>XY.Y)!=(B.Y>XY.Y)&&XY.X<(B.X-A.X)*(XY.Y-A.Y)/(B.Y-A.Y)+A.X)Inside=!Inside;
            }
            if(!Inside)continue;
            const FVector Position=Transform.TransformPosition(FVector(Local.X,Local.Y,Patch.Z));
            const double Depth=Position.Z-View.Z;
            if(Depth<=0||Depth>=NearestDepth)continue;
            Contact.Position=Position;
            Contact.Normal=Component->GetUpVector();
            Contact.Material=Surface.Material;
            Contact.Depth=Depth;
            Contact.Static=true;
            NearestDepth=Depth;Found=true;
        }
    }
    return Found;
}

void URiverPilotFXSubsystem::UpdateNativeOptics()
{
    UWorld* World=GetWorld();
    auto* PC=World?World->GetFirstPlayerController():nullptr;
    if(!PC)
    {
        if(NativeUnderwaterVolume)NativeUnderwaterVolume->BlendWeight=0;
        return;
    }
    FVector Eye;FRotator Rotation;PC->GetPlayerViewPoint(Eye,Rotation);
    const double Now=World->GetTimeSeconds();
    const float Delta=FMath::Clamp(float(Now-LastNativeUpdate),0.f,.1f);
    LastNativeUpdate=Now;
    if(Now>=NextNativeLightUpdate)
    {
        NextNativeLightUpdate=Now+.25;
        UDirectionalLightComponent* Sun=nullptr;
        for(const auto& Entry:NativeLights)
            if(auto* Light=Entry.Get();Light&&Light->IsVisible()&&Light->bAffectsWorld
                &&(!Sun||Light->Intensity>Sun->Intensity))Sun=Light;
        const FVector Direction=Sun?-Sun->GetForwardVector():FVector::UpVector;
        NativeDaylight=Sun?FMath::Clamp(Sun->Intensity/10.f,0.f,1.f)
            *FMath::Clamp(float(Direction.Z)*3.f,0.f,1.f):0.f;
        auto Apply=[this,&Direction](UMaterialInstanceDynamic* Material)
        {
            if(!Material)return;
            Material->SetVectorParameterValue(TEXT("NativeSunDirection"),FLinearColor(Direction));
            Material->SetScalarParameterValue(TEXT("NativeCausticDaylight"),NativeDaylight);
        };
        Apply(WaterMID);
        StaticSurfaces.RemoveAll([](const auto& S){return !S.Component.IsValid();});
        for(const auto& Surface:StaticSurfaces)
            if(Surface.ImmersionDepthCm>0&&Surface.Component->Bounds.GetBox().ComputeSquaredDistanceToPoint(Eye)<FMath::Square(9500.f))
                Apply(Surface.Material.Get());
        if(NativeUnderwaterMID)NativeUnderwaterMID->SetScalarParameterValue(TEXT("WaterDaylight"),NativeDaylight);
    }
    if(!NativeUnderwaterMID||!NativeUnderwaterVolume)return;
    FFluidWaterContact Contact;
    bool Immersed=FindNativeImmersion(Eye,Contact);
    if(Immersed&&Contact.Static)
    {
        // Fountain columns may contain a stone bowl or a pillar. One budgeted trace
        // prevents the post effect leaking through that solid floor into a lower room.
        if(auto* Budget=World->GetSubsystem<UFluidPresentationSubsystem>();Budget&&!Budget->ReserveGeometryQueries(1))return;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(NativeWaterColumn),false);
        Params.AddIgnoredActor(PC->GetPawn());
        Immersed=!World->LineTraceTestByChannel(Contact.Position-Contact.Normal*.5,Eye,ECC_Visibility,Params);
    }
    if(!Immersed)
    {
        NativeUnderwaterVolume->BlendWeight=0; // Never tint a dry room after teleport/streaming.
        return;
    }
    NativeUnderwaterMID->SetScalarParameterValue(TEXT("WaterLevelCm"),Contact.Position.Z);
    const float Target=FMath::Clamp(Contact.Depth/12.f,0.f,1.f);
    NativeUnderwaterVolume->BlendWeight=FMath::FInterpTo(NativeUnderwaterVolume->BlendWeight,Target,Delta,12.f);
}

void URiverPilotFXSubsystem::EndNativeOptics()
{
    if(auto* World=GetWorld())
    {
        World->GetTimerManager().ClearTimer(NativeOpticsTimer);
        World->RemoveOnActorSpawnedHandler(NativeLightSpawnHandle);
    }
    if(NativeUnderwaterLoad){NativeUnderwaterLoad->CancelHandle();NativeUnderwaterLoad.Reset();}
    if(NativeUnderwaterVolume)
    {
        if(auto* Owner=NativeUnderwaterVolume->GetOwner())Owner->RemoveInstanceComponent(NativeUnderwaterVolume);
        NativeUnderwaterVolume->DestroyComponent();NativeUnderwaterVolume=nullptr;
    }
    NativeUnderwaterMID=nullptr;NativeLights.Reset();
}
