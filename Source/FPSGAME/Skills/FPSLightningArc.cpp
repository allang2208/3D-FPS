#include "FPSLightningArc.h"
#include "Components/SplineComponent.h"
#include "Components/PointLightComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitterHandle.h"

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
void AFPSLightningArc::InitializeArc(UNiagaraSystem* System,const FVector& Start,const FVector& End,const FLightningCast& Spell,float Width,bool bContactLight,float Brightness)
{
    SetActorLocation(Start);Hold=Spell.Duration;Fade=FMath::Max(.01f,Spell.Fade);
    BaseBrightness=Brightness;
    const FVector Delta=End-Start;const float Length=Delta.Size();
    FVector Side,Up;Delta.GetSafeNormal().FindBestAxisVectors(Side,Up);
    const int32 Count=FMath::Max(2,Spell.Segments);Path->ClearSplinePoints(false);
    FRandomStream Cosmetic{int32(FPlatformTime::Cycles())};
    // Randomize once, matching the original fixed bolt silhouette. Endpoints remain exact.
    for(int32 I=0;I<=Count;++I)
    {
        const float T=float(I)/Count;
        const float Amplitude=(I==0||I==Count)?0.f:FMath::Min(Length*.12f,Length*Spell.Jitter)*FMath::Sin(PI*T);
        const FVector P=Delta*T+(Side*Cosmetic.FRandRange(-1.f,1.f)+Up*Cosmetic.FRandRange(-1.f,1.f))*Amplitude;
        Path->AddSplinePoint(P,ESplineCoordinateSpace::Local,false);
        Path->SetSplinePointType(I,ESplinePointType::Linear,false);
    }
    Path->UpdateSpline();FX->SetAsset(System);
    const FBox Bounds=Path->CalcBounds(FTransform::Identity).GetBox().ExpandBy(160);
    FX->SetSystemFixedBounds(Bounds);
    if(System)
        for(const auto& Emitter:System->GetEmitterHandles())
            if(Emitter.GetName()==TEXT("Detail")){FX->SetEmitterFixedBounds(TEXT("Detail"),Bounds);break;}
    // The weapon attachment root is the pawn, not this arc. Bind the blade
    // asset's spline interface explicitly so it cannot lose its own path.
    if(bBladeAttached)FX->SetVariableObject(TEXT("User.BladeSpline"),Path);
    FX->SetVariableFloat(TEXT("User.Progress"),1);FX->SetVariableFloat(TEXT("User._Width"),8*Width);
    FX->SetVariableFloat(TEXT("User._Brightness"),BaseBrightness);FX->SetVariableFloat(TEXT("User._ColorHue"),0);
    // Freeze only spatial jitter. These speeds animate the ribbon material and
    // travelling sparks; zeroing them also freezes the material at its first sample.
    FX->SetVariableFloat(TEXT("User.Jitter"),0);FX->SetVariableFloat(TEXT("User._DetailSpeed"),.0013f);
    FX->SetVariableFloat(TEXT("User.MainPowerSpeed"),8);FX->SetVariableFloat(TEXT("User._DetailSpeedOffset"),6);FX->SetVariableBool(TEXT("User.AddDetail"),true);
    FX->SetVariableBool(TEXT("User.AddMainPower"),true);FX->Activate(true);
    ImpactLight->SetRelativeLocation(Delta);BaseLight=bContactLight?1800*Width:0.f;ImpactLight->SetIntensity(BaseLight);
    SetLifeSpan(Hold+Fade+.05f);
}
void AFPSLightningArc::InitializeBladeArc(UNiagaraSystem* System,USceneComponent* BladeAnchor,float Length,int32 Seed)
{
    if(!IsValid(BladeAnchor)){Destroy();return;}
    BoundBlade=BladeAnchor;bBladeAttached=true;
    FLightningCast Visual;Visual.Duration=.065f;Visual.Fade=.115f;
    BladeLength=FMath::Max(1.f,Length);
    InitializeArc(System,FVector::ZeroVector,FVector(BladeLength,0,0),Visual,.032f,false,56.f);
    FRandomStream Random(Seed);const float Phase=Random.FRandRange(0.f,2*PI);
    // A short-lived, angular discharge along the blade. It does not trace a
    // regular multi-turn coil; each strike picks a new silhouette.
    const float Radius=FMath::Clamp(BladeLength*.06f,3.2f,6.5f);
    const float Turns=Random.FRandRange(.35f,.72f)*(Random.RandRange(0,1)?1.f:-1.f);
    Path->ClearSplinePoints(false);
    for(int32 I=0;I<=24;++I)
    {
        const float T=I/24.f,Angle=Phase+T*Turns*2*PI+Random.FRandRange(-.24f,.24f);
        const float R=Radius*Random.FRandRange(.74f,1.08f);
        Path->AddSplinePoint(FVector(BladeLength*(.09f+.82f*T),FMath::Cos(Angle)*R+Random.FRandRange(-.9f,.9f),
            FMath::Sin(Angle)*R+Random.FRandRange(-.9f,.9f)),ESplineCoordinateSpace::Local,false);
        Path->SetSplinePointType(I,ESplinePointType::Linear,false);
    }
    Path->UpdateSpline();FX->SetSystemFixedBounds(Path->CalcBounds(FTransform::Identity).GetBox().ExpandBy(16));
    FX->SetVariableBool(TEXT("User.AddDetail"),false);FX->SetOnlyOwnerSee(true);
    AttachToComponent(BladeAnchor,FAttachmentTransformRules::SnapToTargetNotIncludingScale);
    Path->SetRelativeTransform(FTransform::Identity);
    // Bone publication -> enchant anchor -> local rotation -> Niagara. The
    // attachment also carries later camera/weapon updates without a world copy.
    PrimaryActorTick.TickGroup=TG_PostUpdateWork;
    FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);
    FX->AddTickPrerequisiteActor(this);
    // Reuse the arc's light, with only the newest blade arc allowed to light
    // the scene. The light remains attached through inspect and swing motion.
    ImpactLight->SetIntensityUnits(ELightUnits::Lumens);
    ImpactLight->SetLightColor(FLinearColor(.42f,.28f,1.f));
    ImpactLight->SetUseInverseSquaredFalloff(true);
    ImpactLight->SetAttenuationRadius(145.f);ImpactLight->SetSourceRadius(4.f);
    ImpactLight->SetSourceLength(FMath::Min(60.f,BladeLength*.55f));
    ImpactLight->SetRelativeLocation(FVector(BladeLength*.48f,0.f,3.f));
    ImpactLight->SetRelativeRotation(FRotator(90.f,0.f,0.f));
    ImpactLight->SetIndirectLightingIntensity(0.f);ImpactLight->SetVolumetricScatteringIntensity(0.f);
    BaseLight=60.f;ImpactLight->SetIntensity(BaseLight*1.35f);ImpactLight->SetVisibility(true);
}
float AFPSLightningArc::BladeFlash() const
{
    if(!bBladeAttached)return 0.f;
    // An initial spark followed by a smaller restrike, with a soft decay.
    return FMath::Clamp(FMath::Exp(-Age*28.f)+.45f*FMath::Exp(-FMath::Square((Age-.082f)/.017f)),0.f,1.f);
}
void AFPSLightningArc::SetBladeLightVisible(bool bVisible)
{
    if(bBladeAttached)ImpactLight->SetVisibility(bVisible);
}
void AFPSLightningArc::Tick(float Delta)
{
    if(bBladeAttached&&!BoundBlade.IsValid()){Destroy();return;}
    Super::Tick(Delta);Age+=Delta;
    if(bBladeAttached)SetActorRelativeRotation(FQuat(FVector::ForwardVector,Age*.7f));
    const float Alpha=Age<Hold?1.f:FMath::Clamp(1-(Age-Hold)/Fade,0.f,1.f);
    const float Flash=BladeFlash();
    FX->SetVariableFloat(TEXT("User._Brightness"),BaseBrightness*Alpha*(1.f+.55f*Flash));
    ImpactLight->SetIntensity(BaseLight*Alpha*(bBladeAttached?.45f+.90f*Flash:FMath::Max(0.f,1-Age/.3f)));
    if(Age>=Hold+Fade){FX->DeactivateImmediate();Destroy();}
}
