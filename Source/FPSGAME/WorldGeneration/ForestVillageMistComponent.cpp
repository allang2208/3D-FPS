#include "ForestVillageMistComponent.h"
#include "ForestVillageMap.h"
#include "ForestVillageRegion.h"
#include "ForestVillageRelief.h"
#include "../FPSWeatherManager.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/LocalFogVolumeComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "HAL/IConsoleManager.h"

namespace
{
TAutoConsoleVariable<float> ForestMistStrength(TEXT("fps.Hills.ForestMist"),1.f,
    TEXT("Forest village local ground mist strength (0-2). Zero leaves the UDS reference fog alone."));
TAutoConsoleVariable<float> ForestMistRangeCm(TEXT("fps.Hills.ForestMistRangeCm"),18000.f,
    TEXT("Max range in cm for forest village local fog pockets (<= 0 restores 24500 cm)."));

struct FMistSite
{
    FVector Center;
    float Radius;
    float Score;
};

TArray<FMistSite> SelectSites(const AForestVillageRegion& Region)
{
    const FBox2D Map=ForestVillageMap::Bounds();
    const FVector2D VillageMin=FVector2D(Region.GetSettlementMinM())*100.;
    const FBox2D Village(VillageMin,VillageMin+100.*FVector2D(ForestVillageRelief::Columns-1,ForestVillageRelief::Rows-1));
    const auto Water=Region.GetWoodlandWater();
    FRandomStream Jitter(237855);
    TArray<FMistSite> Candidates;
    for(double Y=Map.Min.Y+4600.;Y<Map.Max.Y-4600.;Y+=3200.)
    {
        for(double X=Map.Min.X+4600.;X<Map.Max.X-4600.;X+=3200.)
        {
            const double PX=X+Jitter.FRandRange(-550.f,550.f);
            const double PY=Y+Jitter.FRandRange(-550.f,550.f);
            const FVector2D XY(PX,PY);
            const float Radius=Jitter.FRandRange(2800.f,4000.f);
            if(Village.ComputeSquaredDistanceToPoint(XY)<FMath::Square(Radius+400.f) ||
                (!Region.QuarryLevel.IsNull() && FVector2D::DistSquared(XY,FVector2D(Region.QuarryOrigin))<FMath::Square(8300.+Radius)) ||
                Region.MapRoadWeight(PX,PY)>.55) continue;

            // The standing-tree sites are a stable subset of the baked canopy across both forest surfaces.
            const FIntPoint Cell(FMath::FloorToInt32(PX/1200.),FMath::FloorToInt32(PY/1200.));
            int32 Trees=0;
            for(int32 J=-2;J<=2;++J)
                for(int32 I=-2;I<=2;++I)
                    Trees+=Region.HarvestTreeSite(Cell+FIntPoint(I,J))!=nullptr;
            if(Trees<4) continue;

            const double Z=Region.GroundHeight(PX,PY);
            const double E=Region.GroundHeight(PX+1800.,PY),W=Region.GroundHeight(PX-1800.,PY);
            const double N=Region.GroundHeight(PX,PY+1800.),S=Region.GroundHeight(PX,PY-1800.);
            const double Slope=FMath::Sqrt(FMath::Square(E-W)+FMath::Square(N-S))/3600.;
            const double Hollow=(E+W+N+S)*.25-Z;
            if(Slope>.28 || Hollow<-65.) continue;
            double Shore=0.;
            for(const auto& Pool:Water->Pools)
                Shore=FMath::Max(Shore,1.-FMath::SmoothStep(1400.,4800.,FMath::Sqrt(Pool.Bounds.ComputeSquaredDistanceToPoint(XY))));
            const float Score=float(.38*FMath::Clamp(Trees/10.,0.,1.)+.38*FMath::SmoothStep(-30.,170.,Hollow)+.24*Shore);
            Candidates.Add({FVector(PX,PY,Z+45.),Radius,Score});
        }
    }
    Candidates.Sort([](const FMistSite& A,const FMistSite& B){return A.Score>B.Score;});
    TArray<FMistSite> Sites;
    for(const auto& Candidate:Candidates)
    {
        const bool Crowded=Sites.ContainsByPredicate([&](const FMistSite& Other)
        {
            return FVector::DistSquared2D(Candidate.Center,Other.Center)<FMath::Square(Other.Radius+Candidate.Radius+1200.f);
        });
        if(!Crowded) Sites.Add(Candidate);
        if(Sites.Num()==12) break;
    }
    return Sites;
}

float MistAmount(const AFPSWeatherManager& Weather)
{
    const float Hour=Weather.NormalizedDayTime*24.f;
    const float Dawn=FMath::SmoothStep(3.5f,5.5f,Hour)*(1.f-FMath::SmoothStep(6.5f,9.5f,Hour));
    const float Dusk=FMath::SmoothStep(16.5f,18.5f,Hour)*(1.f-FMath::SmoothStep(20.f,22.f,Hour));
    const float Wet=Weather.GetSurfaceWetness(),Rain=Weather.GetEffectiveRainIntensity();
    const float Calm=1.f-FMath::SmoothStep(180.f,600.f,float(Weather.GetWeatherWind().Size2D()));
    return FMath::Clamp((.055f+.91f*Dawn+.48f*Dusk+.64f*Wet)*FMath::Lerp(.42f,1.f,Calm)*(1.f-.78f*Rain),0.f,1.f);
}
}

UForestVillageMistComponent::UForestVillageMistComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickInterval=.5f;
}

void UForestVillageMistComponent::BeginPlay()
{
    Super::BeginPlay();
    const auto* Region=CastChecked<AForestVillageRegion>(GetOwner());
    for(const auto& Site:SelectSites(*Region))
    {
        auto* Fog=NewObject<ULocalFogVolumeComponent>(GetOwner(),NAME_None,RF_Transient);
        Fog->SetupAttachment(GetOwner()->GetRootComponent());
        Fog->SetAbsolute(true,true,true);
        Fog->SetWorldLocation(Site.Center);
        Fog->SetWorldScale3D(FVector(Site.Radius/ULocalFogVolumeComponent::GetBaseVolumeSize()));
        Fog->RadialFogExtinction=0.f;
        Fog->HeightFogExtinction=0.f;
        Fog->HeightFogFalloff=1550.f;
        Fog->FogPhaseG=.2f;
        Fog->FogAlbedo=FLinearColor(.91f,.945f,.955f);
        Fog->SetVisibility(false);
        Fog->RegisterComponent();
        Pockets.Add(Fog);
    }
    if(Pockets.IsEmpty()) SetComponentTickEnabled(false);
}

void UForestVillageMistComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime,TickType,TickFunction);
    auto* Manager=Weather.Get();
    if(!Manager)
    {
        TActorIterator<AFPSWeatherManager> It(GetWorld());
        if(It) { Manager=*It; Weather=Manager; }
    }
    const float Gain=FMath::Clamp(ForestMistStrength.GetValueOnGameThread(),0.f,2.f);
    const float Target=Manager && Manager->IsWeatherStateReady() && Manager->IsSkyClockConnected() ? MistAmount(*Manager)*Gain : 0.f;
    LocalStrength=LocalStrength<0.f ? Target : FMath::Lerp(LocalStrength,Target,1.f-FMath::Exp(-DeltaTime/5.f));
    TArray<FVector,TInlineAllocator<2>> Eyes;
    if(Gain>0.f && LocalStrength>.008f)
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=It->Get();PC && PC->IsLocalController() && PC->PlayerCameraManager)
                Eyes.Add(PC->PlayerCameraManager->GetCameraLocation());
    const float ConfiguredRangeCm = ForestMistRangeCm.GetValueOnGameThread();
    const double MaxRangeCm = ConfiguredRangeCm > 0.f ? double(ConfiguredRangeCm) : 24500.;
    const double MaxRangeSq = MaxRangeCm * MaxRangeCm;
    const double FadeStartCm = MaxRangeCm * 0.7;
    for(ULocalFogVolumeComponent* Fog:Pockets)
    {
        double DistanceSq=DBL_MAX;
        for(const auto& Eye:Eyes) DistanceSq=FMath::Min(DistanceSq,FVector::DistSquared(Eye,Fog->GetComponentLocation()));
        const float Amount=DistanceSq<MaxRangeSq ?
            LocalStrength*float(1.-FMath::SmoothStep(FadeStartCm,MaxRangeCm,FMath::Sqrt(DistanceSq))) : 0.f;
        const bool Visible=Amount>.008f;
        const float HeightExtinction=.40f*Amount;
        if(Visible && (!Fog->IsVisible() || FMath::Abs(Fog->HeightFogExtinction-HeightExtinction)>.002f))
        {
            Fog->SetHeightFogExtinction(HeightExtinction);
            Fog->SetRadialFogExtinction(.065f*Amount);
        }
        if(Fog->IsVisible()!=Visible) Fog->SetVisibility(Visible);
    }
}

void UForestVillageMistComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    for(ULocalFogVolumeComponent* Fog:Pockets) if(IsValid(Fog)) Fog->DestroyComponent();
    Pockets.Reset();
    Super::EndPlay(Reason);
}
