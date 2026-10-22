#include "FPSMeteorStrike.h"
#include "FireMagicArea.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../Weapons/ThermalTargetSubsystem.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"

namespace
{
constexpr int32 MaxSources=37;
constexpr float GridHeight=360.f;
constexpr float BelowSurface=96.f;

FName SourceName(int32 Index)
{
    static const TArray<FName> Names=[]()
    {
        TArray<FName> Result;
        for(int32 I=0;I<MaxSources;++I)Result.Emplace(*FString::Printf(TEXT("User.FuelCell%d"),I));
        return Result;
    }();
    return Names[Index];
}
}

void AFPSMeteorStrike::PrepareGroundFire(UNiagaraSystem* System)
{
    const float Radius=CastSnapshot.AuraRadius;
    const float Width=2.f*Radius+160.f;
    const int32 Resolution=Shooter.IsValid()&&Shooter->IsLocallyControlled()?128:96;
    const FMatrix Frame=FRotationMatrix::MakeFromZ(Normal);
    GroundFlames->SetAsset(System);
    GroundFlames->SetWorldLocation(Destination+Normal*(GridHeight*.5f-BelowSurface));
    GroundFlames->SetWorldRotation(Frame.Rotator());
    GroundFlames->SetVariablePosition(TEXT("User.Origin"),Destination+Normal*6.f);
    GroundFlames->SetVariableVec3(TEXT("User.Side"),Frame.GetUnitAxis(EAxis::X));
    GroundFlames->SetVariableVec3(TEXT("User.Forward"),Frame.GetUnitAxis(EAxis::Y));
    GroundFlames->SetVariableVec3(TEXT("User.Up"),FVector::UpVector);
    GroundFlames->SetVariableVec3(TEXT("User.SurfaceNormal"),Normal);
    GroundFlames->SetVariableVec3(TEXT("User.WorldSpaceSize"),FVector(Width,Width,GridHeight));
    GroundFlames->SetVariableInt(TEXT("User.ResolutionMaxAxis"),Resolution);
    GroundFlames->SetVariableFloat(TEXT("User.CellSize"),Width/Resolution);
    GroundFlames->SetVariableFloat(TEXT("User.Radius"),Radius);
    GroundFlames->SetVariableFloat(TEXT("User.PatchWidth"),Radius*.125f);
    GroundFlames->SetVariableFloat(TEXT("User.FuelLevel"),0.f);
    GroundFlames->SetVariableFloat(TEXT("User.VisualFade"),1.f);
    GroundFlames->SetVariableFloat(TEXT("User.FieldAge"),0.f);
    // Replicated start time gives each cast a stable patch pattern. Low and
    // hotter patches keep different rhythms instead of one common fire ceiling.
    GroundFlames->SetVariableFloat(TEXT("User.FieldSeed"),float(FMath::Fmod(FMath::Max(0.,NetStartedAt)*.1237,1.)));
    GroundFlames->SetVariableVec3(TEXT("User.Wind"),FVector::ZeroVector);
    GroundFlames->SetCastShadow(false);
    GroundFlames->SetSystemFixedBounds(FBox(FVector(-Width*.5f,-Width*.5f,-GridHeight*.5f),
        FVector(Width*.5f,Width*.5f,GridHeight*.5f)));

    // The known impact surface guarantees an immediate central source. The
    // remaining stable patches are resolved during the fall/first burning frames.
    GroundFireSourceCount=1;NextGroundFireSample=0;GroundFireWindAge=1.f;
    GroundFlames->SetVariableLinearColor(SourceName(0),FLinearColor(0,0,0,0));
    GroundFlames->SetVariableInt(TEXT("User.SourceCount"),GroundFireSourceCount);
    GroundFireSamples.Reset();GroundFireSamples.Add(FVector2D::ZeroVector);
    for(int32 Y=-3;Y<=3;++Y)for(int32 X=-3;X<=3;++X)
        if((X||Y)&&X*X+Y*Y<=10)GroundFireSamples.Add(FVector2D(X,Y));
    GroundFireSamples.Sort([](const auto& A,const auto& B){return A.SizeSquared()<B.SizeSquared();});
    UThermalTargetSubsystem::RegisterFire(GroundFlames,FVector(Radius,Radius,90),
        FVector(0,0,BelowSurface-GridHeight*.5f+65.f));
}

void AFPSMeteorStrike::UpdateGroundFire(float FieldAge,float Delta)
{
    if(!bVisualsReady||!GroundFlames||GetNetMode()==NM_DedicatedServer)return;
    auto* Budget=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    const FMatrix Frame=FRotationMatrix::MakeFromZ(Normal);
    const FVector Side=Frame.GetUnitAxis(EAxis::X),Forward=Frame.GetUnitAxis(EAxis::Y);
    const float Radius=CastSnapshot.AuraRadius;
    // Six logical geometry queries per patch, at most two patches per frame,
    // sharing the existing hazard budget. No world-wide actor scans or new Tick.
    for(int32 Work=0;Work<2&&NextGroundFireSample<GroundFireSamples.Num();++Work)
    {
        if(Budget&&!Budget->ReserveGeometryQueries(6,true))break;
        const FVector2D Cell=GroundFireSamples[NextGroundFireSample++];
        const bool Center=Cell.IsNearlyZero();
        const float Phase=Cell.X*12.9898f+Cell.Y*78.233f;
        const float JitterX=Center?0.f:FMath::Sin(Phase)*.15f,JitterY=Center?0.f:FMath::Sin(Phase+37.5f)*.15f;
        const FVector Offset=(Side*(Cell.X+JitterX)+Forward*(Cell.Y+JitterY))*(Radius*.285f);
        const FVector Candidate=Destination+Offset;
        FHitResult Floor;
        if(!FireMagic::TraceSurface(Shooter.Get(),Candidate+FVector(0,0,110),Candidate-FVector(0,0,150),Floor)
            ||Floor.bStartPenetrating||Floor.ImpactNormal.Z<.45f)continue;
        const FVector GroundOffset=Floor.ImpactPoint-Destination;
        const float Height=FVector::DotProduct(GroundOffset,Normal);
        if(FMath::Abs(Height)>FireMagic::GroundBand||FVector::VectorPlaneProject(GroundOffset,Normal).SizeSquared()>FMath::Square(Radius*.95f))continue;
        FHitResult Cover;
        if(FireMagic::TraceSurface(Shooter.Get(),Destination+Normal*40.f,Floor.ImpactPoint+Floor.ImpactNormal*32.f,Cover,true))continue;
        // Clamp this patch's spread before it can inject fuel across a wall.
        const float PatchWidth=Radius*.125f;
        float Clearance=PatchWidth;
        const FVector Probe=Floor.ImpactPoint+Floor.ImpactNormal*18.f;
        for(const FVector Axis:{Side,-Side,Forward,-Forward})
        {
            FHitResult Edge;
            if(FireMagic::TraceSurface(Shooter.Get(),Probe,Probe+Axis*PatchWidth,Edge,true))
                Clearance=FMath::Min(Clearance,FMath::Max(0.f,float(Edge.Distance)-12.f));
        }
        const int32 Index=Center?0:GroundFireSourceCount++;
        GroundFlames->SetVariableLinearColor(SourceName(Index),
            FLinearColor(GroundOffset.X,GroundOffset.Y,GroundOffset.Z,Clearance/FMath::Max(1.f,PatchWidth)));
        GroundFlames->SetVariableInt(TEXT("User.SourceCount"),GroundFireSourceCount);
    }
    GroundFireWindAge+=Delta;
    if(GroundFireWindAge>=.2f)
    {
        GroundFireWindAge=0.f;
        const FVector Wind=Budget?Budget->WindAt(Destination).GetClampedToMaxSize(80.f):FVector::ZeroVector;
        GroundFlames->SetVariableVec3(TEXT("User.Wind"),Wind);
    }
    const float Remaining=FMath::Max(0.f,CastSnapshot.Duration-FieldAge);
    // Source strength is independent of material extinction. Reduce new fuel
    // first; keep existing hot gas rising instead of shrinking the entire disk.
    const float Fuel=FMath::SmoothStep(0.f,.65f,Remaining);
    GroundFlames->SetVariableFloat(TEXT("User.FieldAge"),FieldAge);
    GroundFlames->SetVariableFloat(TEXT("User.FuelLevel"),bImpacted?Fuel:0.f);
    GroundFlames->SetVariableFloat(TEXT("User.VisualFade"),FMath::Clamp(Remaining/.22f,0.f,1.f));
}
