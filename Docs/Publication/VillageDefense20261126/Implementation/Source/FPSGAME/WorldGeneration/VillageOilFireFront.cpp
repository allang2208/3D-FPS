#include "VillageHotOil.h"
#include "VillageOilSurveySubsystem.h"
#include "FluidPresentationSubsystem.h"
#include "VillagePresentationView.h"
#include "NiagaraComponent.h"
#include "NiagaraDataInterfaceArrayFunctionLibrary.h"

namespace
{
constexpr int BandSide=(FVillageOilSpread::Side+1)/2;
constexpr float HighFlameLastBirth=8.95f;

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
            if(!C.bGround || C.Edge<=0.f || C.Arrival>=VillageHotOil::Life || !Spread.WetAt(C.P,VillageHotOil::Life))continue;
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
        // Two edges on supported wet triangles. Samples on the same edge interpolate
        // the same ground height and arrival clock as the oil film, even across a slope.
        for(int K=0;K<5;++K)
        {
            const auto& A=Cells[K<2?First:Mid];
            const auto& B=Cells[K<2?Mid:Anchor];
            const float T=K<2?K*.5f:(K-2)*.5f;
            if(GeometryChanged)Band.Points[K]=FMath::Lerp(A.P,B.P,double(T))+FVector(0,0,2.);
            const float Depth=FMath::Lerp(A.FilmMM,B.FilmMM,T);
            const float Shore=FMath::Clamp(FMath::Lerp(A.Edge,B.Edge,T)/36.f,.48f,1.f);
            Band.Scale[K]=Shore*(.84f+.22f*FMath::Clamp(Depth/.085f,0.f,1.f));
            Band.Arrival[K]=FMath::Lerp(A.Arrival,B.Arrival,T)+(Anchor==Center?0.f:.035f);
            FireEvents.Add(Band.Arrival[K]);
        }
    }

    const float Mean=FMath::Max(.001f,float(FilmSum/FMath::Max(1,WetCells)));
    FFireBand* LastPocket=nullptr;
    float Deepest=-1.f;
    for(FFireBand& Band:FireBands)if(Band.Path.X!=INDEX_NONE)
    {
        const float Depth=(Cells[Band.Path.X].FilmMM+Cells[Band.Path.Y].FilmMM+Cells[Band.Path.Z].FilmMM)/3.f;
        Band.LastBirth=FMath::Lerp(7.85f,9.46f,FMath::SmoothStep(.45f,1.65f,Depth/Mean));
        if(Depth>Deepest){LastPocket=&Band;Deepest=Depth;}
        FireEvents.Add(Band.LastBirth);
    }
    // A small ledge may wet only one nearly uniform band. Keep that last low
    // flame until the torch's native tail can carry it to the end of the field.
    if(LastPocket){LastPocket->LastBirth=9.46f;FireEvents.Add(LastPocket->LastBirth);}

    // One tall tongue per four-by-four sector, at its thickest real oil sample.
    HotCells.Reset();
    for(int Y=0;Y<BandSide;Y+=2)for(int X=0;X<BandSide;X+=2)
    {
        int Pocket=INDEX_NONE;
        float Best=Mean*1.12f;
        for(int DY=0;DY<2 && Y+DY<BandSide;++DY)for(int DX=0;DX<2 && X+DX<BandSide;++DX)
        {
            const int I=FireBands[(Y+DY)*BandSide+X+DX].Richest;
            if(I!=INDEX_NONE && Cells[I].FilmMM>Best){Pocket=I;Best=Cells[I].FilmMM;}
        }
        if(Pocket!=INDEX_NONE){HotCells.Add(Pocket);FireEvents.Add(Cells[Pocket].Arrival+.19f);}
    }
    FireEvents.Add(HighFlameLastBirth);
    FireEvents.Sort();
    FireSurveyExtent=Spread.Built;
}

void AVillageOilField::UpdateFireRoots(float WetAge)
{
    while(FireEventCursor<FireEvents.Num() && FireEvents[FireEventCursor]<=WetAge)++FireEventCursor;
    TArray<FVector4> Roots;
    Roots.Reserve(FireBands.Num()*5+HotCells.Num());
    int32 Bands=0,Pockets=0;
    TBitArray<> SingleSources(false,Spread.Cells.Num());
    for(const FFireBand& Band:FireBands)
    {
        if(Band.Path.X==INDEX_NONE || WetAge<Band.Arrival[0] || WetAge>=Band.LastBirth)continue;
        int Ready=1;
        while(Ready<5 && Band.Arrival[Ready]<=WetAge)++Ready;
        if(Band.Points[0]==Band.Points[Ready-1])
        {
            if(SingleSources[Band.Path.X])continue;
            SingleSources[Band.Path.X]=true;
        }
        // Newly lit bands initially use just their upstream end. Keep the same
        // five-slot addressing as the front advances toward the last wet knot.
        for(int Slot=0;Slot<5;++Slot)
        {
            const int K=Slot%Ready;
            Roots.Emplace(Band.Points[K],Band.Scale[K]);
        }
        ++Bands;
    }
    if(Bands>0 && WetAge<HighFlameLastBirth)for(int I:HotCells)
    {
        const auto& C=Spread.Cells[I];
        if(C.Arrival+.19f>WetAge)continue;
        Roots.Emplace(C.P+FVector(0,0,2.),.85f+.22f*FMath::Clamp(C.FilmMM/.1f,0.f,1.f));
        ++Pockets;
    }
    if(Roots!=UploadedFireRoots)
    {
        UNiagaraDataInterfaceArrayFunctionLibrary::SetNiagaraArrayVector4(FireFront,TEXT("User.OilRoots"),Roots);
        UploadedFireRoots=MoveTemp(Roots);
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

void UFluidPresentationSubsystem::SetOilFireDemand(UNiagaraComponent* Fire,float LowRate,float HighRate)
{
    if(LowRate<=0.f && HighRate<=0.f)
    {
        if(OilFires.Remove(Fire))
        {
            Fire->SetVariableFloat(TEXT("User.PrimaryRate"),0.f);
            Fire->SetVariableFloat(TEXT("User.SecondaryRate"),0.f);
            bOilBudgetDirty=true;
        }
        return;
    }
    auto& Slot=OilFires.FindOrAdd(Fire);
    const FVector2f Demand(LowRate,HighRate);
    if(!Slot.Demand.Equals(Demand,.001f)){Slot.Demand=Demand;bOilBudgetDirty=true;}
}

void UFluidPresentationSubsystem::FlushOilFireBudget()
{
    bOilBudgetDirty=false;
    FVector2f Total(0.f,0.f);
    for(auto It=OilFires.CreateIterator();It;++It)
    {
        if(!It.Key().IsValid()){It.RemoveCurrent();continue;}
        Total+=It.Value().Demand;
    }
    constexpr float Budget=300.f;
    const float LowShare=FMath::Min(1.f,Budget/FMath::Max(Total.X,1.f));
    const float HighShare=FMath::Clamp((Budget-Total.X)/FMath::Max(Total.Y,1.f),0.f,1.f);
    for(auto& Entry:OilFires)
    {
        auto& Slot=Entry.Value;
        const FVector2f Rates(Slot.Demand.X*LowShare,Slot.Demand.Y*HighShare);
        if(Slot.Applied.X!=Rates.X)Entry.Key->SetVariableFloat(TEXT("User.PrimaryRate"),Rates.X);
        if(Slot.Applied.Y!=Rates.Y)Entry.Key->SetVariableFloat(TEXT("User.SecondaryRate"),Rates.Y);
        Slot.Applied=Rates;
    }
}

void AVillageOilField::UpdateFireFront(float WetAge)
{
    if(WetAge<NextFireUpdate)return;
    NextFireUpdate=WetAge+.15f;
    UWorld* World=GetWorld();
    auto* Fluid=World->GetSubsystem<UFluidPresentationSubsystem>();
    if(!Fluid)return;
    const auto Detail=Fluid->FireViews.Classify(*World,GetActorLocation(),VillageHotOil::Radius+120.f,30.f,
        3200.f,9600.f,FireFront,bDetailedFire);
    bDetailedFire=Detail==EFireParticleDetail::Full;
    if(Detail==EFireParticleDetail::Off)
    {
        Fluid->SetOilFireDemand(FireFront,0.f,0.f);
        if(FireFront->IsActive())FireFront->DeactivateImmediate();
        return;
    }

    const bool SurveyChanged=FireSurveyExtent!=Spread.Built;
    if(SurveyChanged)BuildFireBands();
    if(SurveyChanged || (FireEvents.IsValidIndex(FireEventCursor) && FireEvents[FireEventCursor]<=WetAge))
        UpdateFireRoots(WetAge);

    // Once fuel runs out let already spawned torch particles finish their own fade.
    if(!ActiveBands && !ActivePockets){Fluid->SetOilFireDemand(FireFront,0.f,0.f);return;}
    FVector Eye;double FovScale;
    if(VillagePresentationView::ClosestEye(*World,GetActorLocation(),VillageHotOil::Radius,Eye,FovScale))
    {
        const FVector4 View(GetActorTransform().InverseTransformPosition(Eye),.23*FovScale);
        if(!FVector(View).Equals(FVector(FireView),2.) || FMath::Abs(View.W-FireView.W)>.001)
        {
            FireFront->SetVariableVec4(TEXT("User.OilView"),View);
            FireView=View;
        }
    }
    const bool Far=!bDetailedFire && VillagePresentationView::Distance(*World,GetActorLocation(),VillageHotOil::Radius)>6000.;
    const float Fuel=1.f-.68f*FMath::SmoothStep(8.f,9.46f,WetAge);
    const float Low=ActiveBands==0?0.f:bDetailedFire?FMath::Clamp(3.1f*ActiveBands,12.f,145.f):
        Far?FMath::Min(26.f,.75f*ActiveBands):FMath::Min(60.f,1.45f*ActiveBands);
    const float High=bDetailedFire?FMath::Min(36.f,.9f*ActivePockets):0.f;
    Fluid->SetOilFireDemand(FireFront,Low*Fuel,High*Fuel);
    if(!FireFront->IsActive() && (Low>0.f || High>0.f))FireFront->Activate();
}

void AVillageOilField::EndPlay(const EEndPlayReason::Type Reason)
{
    if(HasAuthority() && GetWorld())
        if(auto* Scheduler=GetWorld()->GetSubsystem<UVillageOilSurveySubsystem>())Scheduler->Remove(this);
    if(UWorld* World=GetWorld())if(auto* Fluid=World->GetSubsystem<UFluidPresentationSubsystem>())
        Fluid->SetOilFireDemand(FireFront,0.f,0.f);
    Super::EndPlay(Reason);
}
