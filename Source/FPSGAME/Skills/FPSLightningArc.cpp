#include "FPSLightningArc.h"
#include "Components/SplineComponent.h"
#include "Components/PointLightComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"

AFPSLightningArc::AFPSLightningArc()
{
    PrimaryActorTick.bCanEverTick=true;
    Path=CreateDefaultSubobject<USplineComponent>(TEXT("LightningPath"));SetRootComponent(Path);
    Path->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FX=CreateDefaultSubobject<UNiagaraComponent>(TEXT("ElectricArc"));FX->SetupAttachment(Path);FX->SetAutoActivate(false);
    ImpactLight=CreateDefaultSubobject<UPointLightComponent>(TEXT("ContactLight"));ImpactLight->SetupAttachment(Path);
    ImpactLight->SetCastShadows(false);ImpactLight->SetIntensity(0);ImpactLight->SetAttenuationRadius(140);
    ImpactLight->SetLightColor(FLinearColor(.40f,.20f,1));ImpactLight->SetVolumetricScatteringIntensity(0);
}
void AFPSLightningArc::InitializeArc(UNiagaraSystem* System,const FVector& Start,const FVector& End,const FLightningCast& Spell,float Width)
{
    SetActorLocation(Start);Hold=Spell.Duration;Fade=FMath::Max(.01f,Spell.Fade);
    const FVector Delta=End-Start;const float Length=Delta.Size();
    FVector Side,Up;Delta.GetSafeNormal().FindBestAxisVectors(Side,Up);
    const int32 Count=FMath::Max(2,Spell.Segments);Path->ClearSplinePoints(false);
    // Randomize once, matching the original fixed bolt silhouette. Endpoints remain exact.
    for(int32 I=0;I<=Count;++I)
    {
        const float T=float(I)/Count;
        const float Amplitude=(I==0||I==Count)?0.f:FMath::Min(Length*.12f,Length*Spell.Jitter)*FMath::Sin(PI*T);
        const FVector P=Delta*T+(Side*FMath::FRandRange(-1.f,1.f)+Up*FMath::FRandRange(-1.f,1.f))*Amplitude;
        Path->AddSplinePoint(P,ESplineCoordinateSpace::Local,false);
        Path->SetSplinePointType(I,ESplinePointType::Linear,false);
    }
    Path->UpdateSpline();FX->SetAsset(System);
    const FBox Bounds=Path->CalcBounds(FTransform::Identity).GetBox().ExpandBy(160);
    FX->SetSystemFixedBounds(Bounds);FX->SetEmitterFixedBounds(TEXT("Detail"),Bounds);
    FX->SetVariableFloat(TEXT("User.Progress"),1);FX->SetVariableFloat(TEXT("User._Width"),8*Width);
    FX->SetVariableFloat(TEXT("User._Brightness"),50);FX->SetVariableFloat(TEXT("User._ColorHue"),0);
    // Freeze only spatial jitter. These speeds animate the ribbon material and
    // travelling sparks; zeroing them also freezes the material at its first sample.
    FX->SetVariableFloat(TEXT("User.Jitter"),0);FX->SetVariableFloat(TEXT("User._DetailSpeed"),.0013f);
    FX->SetVariableFloat(TEXT("User.MainPowerSpeed"),8);FX->SetVariableFloat(TEXT("User._DetailSpeedOffset"),6);FX->SetVariableBool(TEXT("User.AddDetail"),true);
    FX->SetVariableBool(TEXT("User.AddMainPower"),true);FX->Activate(true);
    ImpactLight->SetRelativeLocation(Delta);BaseLight=1800*Width;ImpactLight->SetIntensity(BaseLight);
    SetLifeSpan(Hold+Fade+.05f);
}
void AFPSLightningArc::Tick(float Delta)
{
    Super::Tick(Delta);Age+=Delta;
    const float Alpha=Age<Hold?1.f:FMath::Clamp(1-(Age-Hold)/Fade,0.f,1.f);
    FX->SetVariableFloat(TEXT("User._Brightness"),50*Alpha);
    ImpactLight->SetIntensity(BaseLight*Alpha*FMath::Max(0.f,1-Age/.3f));
    if(Age>=Hold+Fade){FX->DeactivateImmediate();Destroy();}
}
