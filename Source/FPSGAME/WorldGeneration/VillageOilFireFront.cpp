#include "VillageHotOil.h"
#include "VillageOilSurveySubsystem.h"
#include "FluidPresentationSubsystem.h"
#include "VillagePresentationView.h"
#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraComponent.h"
#include "NiagaraDataInterfaceArrayFunctionLibrary.h"
#include "Scalability.h"
#include "Sound/SoundAttenuation.h"
#include "Sound/SoundBase.h"

namespace
{
constexpr int BandSide=(FVillageOilSpread::Side+1)/2;

int32 CoverageStride(int32 Bands)
{
    // Visit spatially separated bands, exactly once each before repeating.
    int32 Stride=FMath::Max(1,FMath::RoundToInt(Bands*.618f));
    while(FMath::GreatestCommonDivisor(Stride,Bands)>1)--Stride;
    return Stride;
}
}

void AVillageOilField::BuildFireBands()
{
    const auto& Cells=Spread.Cells;
    const int Center=Spread.Half*Spread.Side+Spread.Half;
    const float Life=FieldLife();
    const float HighEnd=Life-1.25f;
    FireBands.SetNum(BandSide*BandSide);
    FireEvents.Reset();
    FireEventCursor=0;
    double FilmSum=0.;
    int32 WetCells=0;
    for(int Y=0;Y<Spread.Side;Y+=2)for(int X=0;X<Spread.Side;X+=2)
    {
        FFireBand& Band=FireBands[(Y/2)*BandSide+X/2];
        int Anchor=INDEX_NONE;
        float BestScore=-1.f;
        Band.Richest=INDEX_NONE;
        for(int DY=0;DY<2 && Y+DY<Spread.Side;++DY)for(int DX=0;DX<2 && X+DX<Spread.Side;++DX)
        {
            const int I=(Y+DY)*Spread.Side+X+DX;
            const auto& C=Cells[I];
            if(!C.bGround || C.Edge<=0.f || C.Arrival>=Life || !Spread.WetAt(C.P,Life))continue;
            ++WetCells;FilmSum+=C.FilmMM;
            if(Band.Richest==INDEX_NONE || C.FilmMM>Cells[Band.Richest].FilmMM)Band.Richest=I;
            FRandomStream R(HashCombineFast(FlowSeed,I));
            const float Score=(I==Center?2.f:0.f)+R.FRand();
            if(Score>BestScore){Anchor=I;BestScore=Score;}
        }
        if(Anchor==INDEX_NONE){Band.Path=FIntVector(-1,-1,-1);continue;}

        const int Mid=Spread.UpstreamOnWetFace(Anchor);
        const int First=Spread.UpstreamOnWetFace(Mid);
        const FIntVector Path(First,Mid,Anchor);
        const bool GeometryChanged=Band.Path!=Path;
        Band.Path=Path;
        const int Idx[3]={First,Mid,Anchor};
        for(int K=0;K<3;++K)
        {
            const auto& C=Cells[Idx[K]];
            if(GeometryChanged)Band.Points[K]=C.P+FVector(0,0,2.);
            const float Shore=FMath::Clamp(C.Edge/34.f,.52f,1.05f);
            Band.Scale[K]=Shore*(.86f+.24f*FMath::Clamp(C.FilmMM/.085f,0.f,1.f));
            Band.Arrival[K]=C.Arrival+(Anchor==Center?0.f:.035f);
            FireEvents.Add(Band.Arrival[K]);
        }
    }

    const float Mean=FMath::Max(.001f,float(FilmSum/FMath::Max(1,WetCells)));
    FFireBand* LastPocket=nullptr;
    float Deepest=-1.f;
    for(FFireBand& Band:FireBands)if(Band.Path.X!=INDEX_NONE)
    {
        const float Depth=(Cells[Band.Path.X].FilmMM+Cells[Band.Path.Y].FilmMM+Cells[Band.Path.Z].FilmMM)/3.f;
        Band.LastBirth=FMath::Lerp(Life-2.0f,Life-.85f,FMath::SmoothStep(.45f,1.65f,Depth/Mean));
        if(Depth>Deepest){LastPocket=&Band;Deepest=Depth;}
        FireEvents.Add(Band.LastBirth);
    }
    if(LastPocket){LastPocket->LastBirth=Life-.85f;FireEvents.Add(LastPocket->LastBirth);}

    // Guarantee tall flame tongues at center and across the thickest sectors, including flat battlements.
    HotCells.Reset();
    struct FHotCandidate { int32 Cell; float Film; };
    TArray<FHotCandidate> Candidates;
    for(const FFireBand& Band:FireBands)
    {
        if(Band.Richest!=INDEX_NONE && Cells[Band.Richest].FilmMM>=Mean*.85f)
            Candidates.Add({Band.Richest,Cells[Band.Richest].FilmMM});
    }
    Candidates.Sort([](const FHotCandidate& A,const FHotCandidate& B){return A.Film>B.Film;});
    if(Center>=0 && Center<Cells.Num() && Cells[Center].bGround && Cells[Center].Edge>0.f && Cells[Center].Arrival<Life)
    {
        HotCells.Add(Center);
        FireEvents.Add(Cells[Center].Arrival+.15f);
    }
    for(const FHotCandidate& Cand:Candidates)
    {
        if(HotCells.Num()>=16)break;
        if(Cand.Cell==Center)continue;
        HotCells.Add(Cand.Cell);
        FireEvents.Add(Cells[Cand.Cell].Arrival+.16f);
    }
    FireEvents.Add(HighEnd);
    FireEvents.Sort();
    FireSurveyExtent=Spread.Built;
}

void AVillageOilField::UpdateFireRoots(float WetAge)
{
    while(FireEventCursor<FireEvents.Num() && FireEvents[FireEventCursor]<=WetAge)++FireEventCursor;
    ScratchFireRoots.Reset();
    ScratchFireRoots.Reserve(FireBands.Num()*3+HotCells.Num());
    int32 Bands=0,Pockets=0;
    ScratchSeenBits.Init(false,Spread.Cells.Num());
    for(const FFireBand& Band:FireBands)
    {
        if(Band.Path.X==INDEX_NONE || WetAge<Band.Arrival[0] || WetAge>=Band.LastBirth)continue;
        int Ready=1;
        while(Ready<3 && Band.Arrival[Ready]<=WetAge)++Ready;
        if(Band.Points[0]==Band.Points[Ready-1])
        {
            if(ScratchSeenBits[Band.Path.X])continue;
            ScratchSeenBits[Band.Path.X]=true;
        }
        for(int Slot=0;Slot<3;++Slot)
        {
            const int K=Slot%Ready;
            ScratchFireRoots.Emplace(Band.Points[K],Band.Scale[K]);
        }
        ++Bands;
    }
    if(Bands>0 && WetAge<FieldLife()-1.25f)for(int I:HotCells)
    {
        const auto& C=Spread.Cells[I];
        if(C.Arrival+.16f>WetAge)continue;
        ScratchFireRoots.Emplace(C.P+FVector(0,0,2.),.92f+.25f*FMath::Clamp(C.FilmMM/.1f,0.f,1.f));
        ++Pockets;
    }
    if(ScratchFireRoots!=UploadedFireRoots)
    {
        UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(FireFront,TEXT("User.OilRoots"),ScratchFireRoots);
        UploadedFireRoots=ScratchFireRoots;
    }
    if(Bands!=ActiveBands)
    {
        ActiveBands=Bands;
        FireFront->SetVariableFloat(TEXT("User.WetRootCount"),float(Bands));
        FireFront->SetVariableFloat(TEXT("User.BandStride"),float(CoverageStride(Bands)));
    }
    if(Pockets!=ActivePockets)
    {
        ActivePockets=Pockets;
        FireFront->SetVariableFloat(TEXT("User.HotRootCount"),float(Pockets));
    }
}

void UFluidPresentationSubsystem::SetOilFireDemand(UNiagaraComponent* Fire,float LowRate,float HighRate,float DetailRate,
    UPointLightComponent* Light,UAudioComponent* Audio,const FVector& Origin,float IntensityWeight)
{
    if(!Fire)return;
    if(LowRate<=0.f && HighRate<=0.f && DetailRate<=0.f)
    {
        if(OilFires.Remove(Fire))
        {
            Fire->SetVariableFloat(TEXT("User.PrimaryRate"),0.f);
            Fire->SetVariableFloat(TEXT("User.SecondaryRate"),0.f);
            Fire->SetVariableFloat(TEXT("User.DetailRate"),0.f);
            bOilBudgetDirty=true;
        }
        if(Light){Light->SetIntensity(0.f);Light->SetVisibility(false);}
        if(Audio && Audio->IsPlaying())Audio->Stop();
        return;
    }
    auto& Slot=OilFires.FindOrAdd(Fire);
    const FVector3f Demand(LowRate,HighRate,DetailRate);
    const bool bChanged=!Slot.Demand.Equals(Demand,.001f) ||
        FMath::Abs(Slot.IntensityWeight-IntensityWeight)>.02f ||
        Slot.Light.Get()!=Light || Slot.Audio.Get()!=Audio;
    Slot.Demand=Demand;
    Slot.Light=Light;
    Slot.Audio=Audio;
    Slot.Origin=Origin;
    Slot.IntensityWeight=IntensityWeight;
    if(bChanged)bOilBudgetDirty=true;
}

void UFluidPresentationSubsystem::FlushOilFireBudget()
{
    bOilBudgetDirty=false;
    FVector3f Total=FVector3f::ZeroVector;
    struct FSortedFire { UNiagaraComponent* Fire; float DistSq; };
    TArray<FSortedFire> Order;
    Order.Reserve(OilFires.Num());

    for(auto It=OilFires.CreateIterator();It;++It)
    {
        UNiagaraComponent* Key=It.Key().Get();
        if(!Key){It.RemoveCurrent();continue;}
        Total+=It.Value().Demand;
        const float DistSq=bHasView?FVector::DistSquared(It.Value().Origin,Eye):0.f;
        Order.Add({Key,DistSq});
    }
    Order.Sort([](const FSortedFire& A,const FSortedFire& B){return A.DistSq<B.DistSq;});

    const int32 Quality=Scalability::GetQualityLevels().EffectsQuality;
    const float Budget=Quality<=0?135.f:(Quality==1?195.f:260.f);
    const int32 MaxLights=Quality<=0?0:(Quality==1?1:2);
    const int32 MaxAudio=Quality<=0?1:2;
    const float DetailScale=Quality<=0?0.f:(Quality==1?.6f:1.f);

    const float LowShare=FMath::Min(1.f,Budget/FMath::Max(Total.X,1.f));
    const float HighBudget=FMath::Max(0.f,Budget-Total.X*LowShare);
    const float HighShare=FMath::Min(1.f,HighBudget/FMath::Max(Total.Y,1.f));
    const float DetailBudget=FMath::Max(0.f,HighBudget-Total.Y*HighShare);
    const float DetailShare=FMath::Min(DetailScale,DetailBudget/FMath::Max(Total.Z,1.f));

    const double Now=GetWorld()?GetWorld()->GetTimeSeconds():0.;
    int32 ActiveLights=0,ActiveAudio=0;
    for(const FSortedFire& Item:Order)
    {
        auto* Slot=OilFires.Find(Item.Fire);
        if(!Slot)continue;
        const FVector3f Rates(Slot->Demand.X*LowShare,Slot->Demand.Y*HighShare,Slot->Demand.Z*DetailShare);
        if(Slot->Applied.X!=Rates.X)Item.Fire->SetVariableFloat(TEXT("User.PrimaryRate"),Rates.X);
        if(Slot->Applied.Y!=Rates.Y)Item.Fire->SetVariableFloat(TEXT("User.SecondaryRate"),Rates.Y);
        if(Slot->Applied.Z!=Rates.Z)Item.Fire->SetVariableFloat(TEXT("User.DetailRate"),Rates.Z);
        Slot->Applied=Rates;

        if(UPointLightComponent* L=Slot->Light.Get())
        {
            if(ActiveLights<MaxLights && Slot->IntensityWeight>.02f && Item.DistSq<=FMath::Square(3200.f))
            {
                const float Flicker=.90f+.10f*FMath::Sin(float(Now)*11.3f+Item.DistSq*.001f);
                L->SetIntensity(2200.f*Slot->IntensityWeight*Flicker);
                if(!L->IsVisible())L->SetVisibility(true);
                ++ActiveLights;
            }
            else
            {
                L->SetIntensity(0.f);
                if(L->IsVisible())L->SetVisibility(false);
            }
        }
        if(UAudioComponent* A=Slot->Audio.Get())
        {
            if(ActiveAudio<MaxAudio && Slot->IntensityWeight>.02f && Item.DistSq<=FMath::Square(2600.f) && OilFireLoop.Get())
            {
                if(A->GetSound()!=OilFireLoop.Get())
                {
                    A->SetSound(OilFireLoop.Get());
                    A->AttenuationSettings=OilFireAtt.Get();
                }
                if(!A->IsPlaying())A->Play();
                A->SetVolumeMultiplier(FMath::Clamp(Slot->IntensityWeight,.05f,1.f));
                ++ActiveAudio;
            }
            else if(A->IsPlaying())
            {
                A->Stop();
            }
        }
    }
}

void AVillageOilField::UpdateFireFront(float WetAge)
{
    if(WetAge<NextFireUpdate)return;
    NextFireUpdate=WetAge+.15f;
    UWorld* World=GetWorld();
    auto* Fluid=World->GetSubsystem<UFluidPresentationSubsystem>();
    if(!Fluid)return;
    const float Radius=FieldRadius();
    const float Life=FieldLife();
    const auto Detail=Fluid->FireViews.Classify(*World,GetActorLocation(),Radius+120.f,30.f,
        3200.f,9600.f,FireFront,bDetailedFire);
    bDetailedFire=Detail==EFireParticleDetail::Full;
    if(Detail==EFireParticleDetail::Off)
    {
        Fluid->SetOilFireDemand(FireFront,0.f,0.f,0.f,FireLight,FireAudio);
        if(FireFront->IsActive())FireFront->DeactivateImmediate();
        return;
    }

    if(WetAge>=0.f && !bIgniteSoundPlayed)
    {
        bIgniteSoundPlayed=true;
        if(USoundBase* Cue=Fluid->OilIgniteSound())
            UGameplayStatics::PlaySoundAtLocation(World,Cue,GetActorLocation(),1.f,1.f,0.f,Fluid->OilIgniteAttenuation());
    }

    const bool SurveyChanged=FireSurveyExtent!=Spread.Built;
    if(SurveyChanged)BuildFireBands();
    if(SurveyChanged || (FireEvents.IsValidIndex(FireEventCursor) && FireEvents[FireEventCursor]<=WetAge))
        UpdateFireRoots(WetAge);

    if(WetAge>=NextWindUpdate)
    {
        NextWindUpdate=WetAge+.5f;
        const FVector LocalWind=GetActorTransform().InverseTransformVector(Fluid->WindWithGustAt(GetActorLocation()));
        FireFront->SetVariableVec3(TEXT("User.Wind"),LocalWind);
    }

    if(!ActiveBands && !ActivePockets){Fluid->SetOilFireDemand(FireFront,0.f,0.f,0.f,FireLight,FireAudio);return;}
    FVector Eye;double FovScale;
    if(VillagePresentationView::ClosestEye(*World,GetActorLocation(),Radius,Eye,FovScale))
    {
        const FVector4 View(GetActorTransform().InverseTransformPosition(Eye),.23*FovScale);
        if(!FVector(View).Equals(FVector(FireView),2.) || FMath::Abs(View.W-FireView.W)>.001)
        {
            FireFront->SetVariableVec4(TEXT("User.OilView"),View);
            FireView=View;
        }
    }
    const float IntensityWeight=FMath::SmoothStep(0.f,.35f,WetAge)*(1.f-FMath::SmoothStep(Life-1.4f,Life+.35f,WetAge));
    const bool Far=!bDetailedFire && VillagePresentationView::Distance(*World,GetActorLocation(),Radius)>6000.;
    const float Low=ActiveBands==0?0.f:bDetailedFire?FMath::Clamp(2.3f*ActiveBands,14.f,105.f):
        Far?FMath::Min(24.f,.65f*ActiveBands):FMath::Min(52.f,1.25f*ActiveBands);
    const float High=bDetailedFire?FMath::Min(42.f,2.6f*ActivePockets):(!Far?FMath::Min(14.f,.9f*ActivePockets):0.f);
    const float DetailRate=(bDetailedFire && ActiveBands>0)?FMath::Min(24.f,.9f*ActiveBands):0.f;
    Fluid->SetOilFireDemand(FireFront,Low*IntensityWeight,High*IntensityWeight,DetailRate*IntensityWeight,
        FireLight,FireAudio,GetActorLocation(),IntensityWeight);
    if(!FireFront->IsActive() && (Low>0.f || High>0.f || DetailRate>0.f))FireFront->Activate();
}

void AVillageOilField::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority() && GetWorld())
        if(auto* Scheduler=GetWorld()->GetSubsystem<UVillageOilSurveySubsystem>())Scheduler->Remove(this);
    if(UWorld* World=GetWorld())if(auto* Fluid=World->GetSubsystem<UFluidPresentationSubsystem>())
        Fluid->SetOilFireDemand(FireFront,0.f,0.f,0.f,FireLight,FireAudio);
    Super::EndPlay(Reason);
}
