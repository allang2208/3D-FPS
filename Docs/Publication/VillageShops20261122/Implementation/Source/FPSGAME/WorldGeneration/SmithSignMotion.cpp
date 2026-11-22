#include "SmithSignMotion.h"
#include "FluidPresentationSubsystem.h"
#include "VillagePresentationView.h"
#include "../FPSWeatherManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "TimerManager.h"

USmithSignMotion::USmithSignMotion()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.bStartWithTickEnabled=false;
}

void USmithSignMotion::BindToAssembly(AActor& Assembly)
{
    if (Assembly.FindComponentByClass<USmithSignMotion>()) return;
    UStaticMeshComponent* Chain = nullptr;
    UStaticMeshComponent* Panel = nullptr;
    TInlineComponentArray<UStaticMeshComponent*> Parts(&Assembly);
    for (auto* Part : Parts)
    {
        if (Part->ComponentHasTag(TEXT("VillageShop.SignLinks"))) Chain = Part;
        if (Part->ComponentHasTag(TEXT("VillageShop.SignBoard"))) Panel = Part;
    }
    if (!Chain || !Panel) return;
    auto* Motion = NewObject<USmithSignMotion>(&Assembly, NAME_None, RF_Transient);
    Assembly.AddInstanceComponent(Motion);
    Motion->RegisterComponent();
    Motion->Mount(*Chain, *Panel);
}

void USmithSignMotion::Mount(UStaticMeshComponent& ChainPair,UStaticMeshComponent& Sign)
{
    Links=&ChainPair; Board=&Sign;
    ChainRest=ChainPair.GetRelativeTransform();
    BoardRest=Sign.GetRelativeTransform();
    const FVector Center = Sign.Bounds.Origin;
    GustPhase = FMath::Fmod(float(Center.X * .0017 + Center.Y * .0031), 2.f*PI);
    GetWorld()->GetTimerManager().SetTimer(RangeTimer,this,&USmithSignMotion::UpdateRange,.7f,true);
    UpdateRange();
}

void USmithSignMotion::UpdateRange()
{
    if (!Board.IsValid() || !Links.IsValid()) { SetComponentTickEnabled(false); return; }
    bool bHasView = false;
    const float Distance = VillagePresentationView::Distance(*GetWorld(), Board->Bounds.Origin, 0., &bHasView);
    DistanceWeight=1.f-FMath::SmoothStep(2600.f,3600.f,Distance);
    if (!bHasView || DistanceWeight<=0.f || !Board->IsVisible() || Board->bHiddenInGame ||
        Board->GetOwner()->IsHidden() || !Board->WasRecentlyRendered(1.f))
    {
        if (IsComponentTickEnabled()) Pose(0.f,0.f);
        Angle=Speed=LinkAngle=LinkSpeed=WindClock=Target=0.f;
        SetComponentTickEnabled(false);
        return;
    }
    bDetailed=Distance<1600.f;
    SetComponentTickInterval(bDetailed ? 1.f/30.f : 1.f/12.f);
    SetComponentTickEnabled(true);
}

void USmithSignMotion::Pose(float Chain,float Panel)
{
    const FQuat hinge=ChainRest.GetRotation();
    const FQuat swing=hinge*FQuat(FVector::YAxisVector,Chain)*hinge.Inverse();
    Links->SetRelativeRotation(swing*hinge);
    const FVector lower=ChainRest.GetLocation()+swing.RotateVector(BoardRest.GetLocation()-ChainRest.GetLocation());
    Board->SetRelativeLocationAndRotation(lower,BoardRest.GetRotation()*FQuat(FVector::YAxisVector,Panel));
}

void USmithSignMotion::TickComponent(float Delta,ELevelTick TickType,FActorComponentTickFunction* ThisTick)
{
    Super::TickComponent(Delta,TickType,ThisTick);
    if (!Board.IsValid() || !Links.IsValid()) { SetComponentTickEnabled(false); return; }
    WindClock-=Delta;
    if (WindClock<=0.f)
    {
        WindClock=bDetailed ? .16f : .32f;
        auto* Air=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
        const auto* Weather=Air ? Air->WeatherSource() : nullptr;
        const float Rain=Weather?FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f):0.f;
        const bool bStorm=Weather && Weather->CurrentState==EFPSWeatherState::Storm;
        const FVector Flow=Air?Air->WindWithGustAt(Board->Bounds.Origin):FVector::ZeroVector;
        const FTransform Parent=Links->GetAttachParent()?Links->GetAttachParent()->GetComponentTransform():FTransform::Identity;
        const FVector Local=(ChainRest*Parent).InverseTransformVectorNoScale(Flow);
        const float t = GetWorld()->GetTimeSeconds();
        const float gust=FMath::Sin(t*1.83f+GustPhase)+.45f*FMath::Sin(t*3.21f-GustPhase);
        const float load=FMath::Clamp(float(-Local.X)/190.f, -1.f,1.f);
        const float breeze = load*(4.f + 2.5f*gust);
        const float tilt=breeze + Rain*(load*(bStorm?10.f:5.f)+gust*(bStorm?4.6f:2.4f));
        Target=FMath::DegreesToRadians(tilt)*DistanceWeight;
        if (Rain < .01f && Flow.SizeSquared2D() < 1.f &&
            FMath::Abs(Angle)+FMath::Abs(Speed)+FMath::Abs(LinkAngle)+FMath::Abs(LinkSpeed) < .001f)
        {
            Pose(0.f,0.f);
            Angle=Speed=LinkAngle=LinkSpeed=WindClock=Target=0.f;
            SetComponentTickEnabled(false);
            return; // The range timer also wakes a sheltered or calm sign when the wind changes.
        }
    }
    // Gravity about a load centre approximately half a metre below the suspension.
    // Bounded substeps keep the lower-rate distant simulation equally damped.
    float remaining=FMath::Min(Delta,.15f);
    while (remaining>SMALL_NUMBER)
    {
        const float h=FMath::Min(remaining,1.f/90.f);
        Speed+=(19.f*(FMath::Sin(Target)-FMath::Sin(Angle))-2.1f*Speed)*h;
        Angle=FMath::Clamp(Angle+Speed*h,-.38f,.38f);
        if (bDetailed)
        {
            LinkSpeed+=(62.f*(Angle+.17f*Speed-LinkAngle)-6.8f*LinkSpeed)*h;
            LinkAngle=FMath::Clamp(LinkAngle+LinkSpeed*h,-.44f,.44f);
        }
        else { LinkAngle=Angle; LinkSpeed=Speed; }
        remaining-=h;
    }
    Pose(LinkAngle,Angle);
}

void USmithSignMotion::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorld()->GetTimerManager().ClearTimer(RangeTimer);
    Super::EndPlay(Reason);
}
