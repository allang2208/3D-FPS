#include "TemperateHillsWorld.h"
#include "ForestVillageMap.h"
#include "HillsNightRaidSubsystem.h"
#include "VT/RuntimeVirtualTexture.h"
#include "TemperateHillsChapel.h"
#include "TemperateHillsPCG.h"
#include "TemperateHillsVisibility.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "../FPSWeatherManager.h"
#include "../Production/ProductionOreRocks.h"
#include "TemperateHillsBackdrop.h"
#include "TemperateHillsGroundLayers.h"
#include "RiverPilotFXSubsystem.h"
#include "NiagaraSystem.h"
#include "../UI/TransitLoadingSubsystem.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "Async/Async.h"
#include "Algo/AllOf.h"
#include "Components/DynamicMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/InstancedSkinnedMeshComponent.h"
#include "Animation/TransformProviderData.h"
#include "Components/CapsuleComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/StreamableManager.h"
#include "Engine/LevelStreamingDynamic.h"
#include "Engine/GameViewportClient.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "MaterialShared.h"
#include "RHIGlobals.h"
#include "HAL/IConsoleManager.h"
#include "PCGGraph.h"
#include "PCGComponent.h"
#include "PCGWorldActor.h"
#include "RuntimeGen/PCGGenSourceManager.h"
#include "PCGGraphExecutionStateInterface.h"
#include "Subsystems/PCGSubsystem.h"
#include "ContentStreaming.h"
#include "RenderCommandFence.h"
#include "Misc/ScopeExit.h"

#include "TemperateHillsStreamingPrivate.h"
void ATemperateHillsWorld::BuildValleyFog()
{
    auto& S=*Streaming;const auto* Pawn=UGameplayStatics::GetPlayerPawn(this,0);
    const FVector Center=Pawn?Pawn->GetActorLocation():GetStartLocation();
    const auto* Weather=SkyWeather.Get();
    const double Hour=Weather?Weather->NormalizedDayTime*24.:9.;
    const double Dawn=FMath::SmoothStep(3.5,6.5,Hour)*(1.-FMath::SmoothStep(6.5,10.5,Hour));
    const double Wetness=Weather?Weather->GetSurfaceWetness():0.;
    const double Rain=Weather?Weather->GetEffectiveRainIntensity():0.;
    const double Wind=Weather?FMath::Clamp(Weather->GetWeatherWind().Size2D()/632.4555,0.,1.):.2;
    // Remaining surface moisture carries a little mist after rain. Strong wind
    // disperses it; clear midday never carries the old permanent white blanket.
    const float Mist=FMath::Clamp(.20+.65*Dawn+.35*Wetness+.15*Rain,.20,1.15)*(1.-.35*Wind);
    auto SetDensity=[](UStaticMeshComponent* Mesh,float Target)
    {
        if(auto* MID=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
            MID->SetScalarParameterValue(TEXT("FogOverallDensity"),FMath::FInterpTo(
                MID->K2_GetScalarParameterValue(TEXT("FogOverallDensity")),Target,.5f,.8f));
    };
    // Shared spawn: scale the fog BP's mesh to a footprint and give it a fresh
    // dynamic material at zero density; the owning pool fades it in.
    auto SpawnFog=[&](const FVector& Position,const FRotator& Rotation,const FVector& Footprint)->AActor*
    {
        FActorSpawnParameters Params;Params.Owner=this;
        auto* Fog=GetWorld()->SpawnActor<AActor>(Assets->ValleyFogClass.Get(),Position,Rotation,Params);
        if(!Fog)return nullptr;
        Fog->SetActorEnableCollision(false);Fog->SetActorHiddenInGame(false);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
        for(auto* M:Meshes)
        {
            if(!M->GetStaticMesh())continue;
            const auto MeshBounds=M->GetStaticMesh()->GetBounds();
            const FVector Scale=Footprint/MeshBounds.BoxExtent;
            // Mesh bounds exclude the Blueprint's editor-only box/billboard bounds.
            M->SetRelativeScale3D(Scale);M->SetRelativeLocation(-MeshBounds.Origin*Scale);
            M->SetCollisionEnabled(ECollisionEnabled::NoCollision);M->SetCanEverAffectNavigation(false);M->SetCastShadow(false);
            auto* MID=UMaterialInstanceDynamic::Create(Assets->ValleyFogMaterial.Get(),Fog);
            MID->SetScalarParameterValue(TEXT("FogOverallDensity"),0);
            M->SetMaterial(0,MID);M->SetVisibility(true);M->SetHiddenInGame(false);M->PrecachePSOs();
        }
        ValleyFog.Add(Fog);
        return Fog;
    };
    // Update a small fixed pool, fading before it leaves the retention radius.
    for(auto It=S.Fog.CreateIterator();It;++It)
    {
        auto* Fog=It.Value().Get();
        if(!Fog){It.RemoveCurrent();continue;}
        const double Distance=FVector::Dist2D(Fog->GetActorLocation(),Center);
        if(Distance>18000)
        {ValleyFog.Remove(Fog);Fog->Destroy();It.RemoveCurrent();return;}
        const float Fade=(1-FMath::SmoothStep(14000.0,18000.0,Distance))*FMath::Clamp(Fog->GetGameTimeSinceCreation()/3.f,0.f,1.f);
        const FVector P=Fog->GetActorLocation();
        const double Region=RainforestWeight(P.X,P.Y);
        const float Moisture=.65f+.35f*TemperateForestHabitat::Moisture(P.X,P.Y,Seed,Region, EcologyProfile());
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
        const float ForestMist=FMath::Lerp(Mist,FMath::Max(Mist,.46f)+.32f*float(Rain),float(Region));
        for(auto* M:Meshes)SetDensity(M,Assets->ValleyFogDensity*Fade*ForestMist*Moisture);
    }
    // River mist: thin bands hugging the waterline near the pawn, keyed by
    // centreline point so a stretch of river keeps exactly one volume.
    if(RiverPlan&&Assets->RiverMistDensity>0.01f)
    {
        for(auto It=S.RiverFog.CreateIterator();It;++It)
        {
            auto* Fog=It.Value().Get();
            if(!Fog){It.RemoveCurrent();continue;}
            const double Distance=FVector::Dist2D(Fog->GetActorLocation(),Center);
            if(Distance>16000)
            {ValleyFog.Remove(Fog);Fog->Destroy();It.RemoveCurrent();continue;}
            const float Fade=(1-FMath::SmoothStep(12000.0,16000.0,Distance))*FMath::Clamp(Fog->GetGameTimeSinceCreation()/3.f,0.f,1.f);
            TInlineComponentArray<UStaticMeshComponent*> Meshes(Fog);
            for(auto* M:Meshes)SetDensity(M,Assets->RiverMistDensity*Fade*FMath::Min(1.f,Mist+.12f));
        }
        if(S.RiverFog.Num()<2)
        {
            int32 Best=-1;double BestScore=DBL_MAX;
            const auto& Points=RiverPlan->Points;
            for(int32 I=0;I<Points.Num();++I)
            {
                if(S.RiverFog.Contains(I))continue;
                const auto& Pt=Points[I];
                const double D2=FVector2D::DistSquared(Pt.XY,FVector2D(Center));
                if(D2>FMath::Square(14000.0))continue;
                // Keep bands spaced apart along the channel.
                bool Crowded=false;
                for(const auto& Held:S.RiverFog)
                    if(auto* Other=Held.Value.Get();Other&&FVector::Dist2D(Other->GetActorLocation(),FVector(Pt.XY.X,Pt.XY.Y,0))<3800){Crowded=true;break;}
                if(Crowded)continue;
                if(D2<BestScore){Best=I;BestScore=D2;}
            }
            if(Best>=0)
            {
                const auto& Pt=Points[Best];
                // Side is the cross-channel normal; the flow axis is its perpendicular.
                const FVector2D Flow(-Pt.Side.Y,Pt.Side.X);
                const FRotator Rotation(0,FMath::RadiansToDegrees(FMath::Atan2(Flow.Y,Flow.X)),0);
                if(auto* Fog=SpawnFog(FVector(Pt.XY.X,Pt.XY.Y,Pt.WaterZ+45),Rotation,FVector(2600,700,85)))
                    S.RiverFog.Add(Best,Fog);
            }
        }
    }
    if(S.Fog.Num()>=4)return;
    const double Side=IsForestVillage()?double(ForestVillageMap::SideMeters):double(SizeMeters);
    const double Half=Side*50.;const int32 Count=FMath::RoundToInt(Side/64.);
    const FVector2D Origin=IsForestVillage()?ForestVillageMap::Bounds().Min:FVector2D(-Half,-Half);
    const int32 CX=FMath::FloorToInt((Center.X-Origin.X)/6400),CY=FMath::FloorToInt((Center.Y-Origin.Y)/6400);
    int32 Best=-1;double BestScore=DBL_MAX;FVector Position=FVector::ZeroVector;
    for(int32 Y=FMath::Max(0,CY-3);Y<=FMath::Min(Count-1,CY+3);++Y)
    for(int32 X=FMath::Max(0,CX-3);X<=FMath::Min(Count-1,CX+3);++X)
    {
        const int32 ID=Y*Count+X;if(S.Fog.Contains(ID))continue;
        const uint32 Key=TemperateHillsSurface::Key(X,Y,Seed,1731);
        const double WX=Origin.X+(X+.5)*6400+(TemperateHillsSurface::Unit(Key)-.5)*3000;
        const double WY=Origin.Y+(Y+.5)*6400+(TemperateHillsSurface::Unit(Key+1)-.5)*3000;
        const FVector P(WX,WY,Height(WX,WY)+65);const double Distance=FVector::DistSquared2D(P,Center);
        if(Distance>FMath::Square(14000.0))continue;
        const FVector N=SurfaceNormal(WX,WY);if(N.Z<.9)continue;
        const double Nearby=(Height(WX-2000,WY)+Height(WX+2000,WY)+Height(WX,WY-2000)+Height(WX,WY+2000))*.25;
        const auto Bank=RiverPlan?RiverPlan->Sample(WX,WY):TemperateRiver::FSample();
        const bool Low=Bank.Bank>.02||Bank.Wet>.02||P.Z-65<Nearby-15;
        const double LocalRegion=RainforestWeight(WX,WY);
        if(!Low&&LocalRegion<.75)continue;
        const double Moisture=TemperateForestHabitat::Moisture(WX,WY,Seed,LocalRegion, EcologyProfile());
        const double Score=Distance+(Bank.Bank>.02||Bank.Wet>.02?0:16000000)+(1.-Moisture)*8000000;
        if(Score<BestScore){Best=ID;BestScore=Score;Position=P;}
    }
    if(Best<0)return;
    const float Yaw=TemperateHillsSurface::Unit(uint32(Seed)+Best*133)*2*PI;
    const FRotator Rotation(0,FMath::RadiansToDegrees(Yaw),0);
    // This also runs under the loading overlay, warming the volume shader before play.
    const double Region=RainforestWeight(Position.X,Position.Y);
    const FVector Footprint=FMath::Lerp(FVector(1600,1100,110),FVector(2350,1650,230),Region);
    if(auto* Fog=SpawnFog(Position,Rotation,Footprint))S.Fog.Add(Best,Fog);
}

