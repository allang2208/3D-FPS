#include "FPSLightningArc.h"
#include "Components/SplineComponent.h"
#include "Components/PointLightComponent.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "NiagaraEmitterHandle.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Net/UnrealNetwork.h"

void AFPSLightningArc::InitializeColumn(UStaticMesh* Tube,UMaterialInterface* BodyMaterial,UMaterialInterface* FilamentMaterial,const FVector& Start,const FVector& End,const FLightningCast& Spell,float ChargeRatio)
{
    if(!Tube||!BodyMaterial||!FilamentMaterial){Destroy();return;}
    Tags.Add(TEXT("ThunderLanceColumn"));Age=0;Hold=Spell.Duration;Fade=FMath::Max(.01f,Spell.Fade);
    if(HasAuthority()){NetKind=1;NetStart=Start;NetEnd=End;NetSpell=Spell;NetWidth=1.f;NetBrightness=50.f;NetChargeRatio=ChargeRatio;NetContactLight=true;}
    // Charge payoff: a minimum-charge shot reads as a thinner, dimmer bolt.
    const float Visual=FMath::Lerp(.55f,1.f,FMath::Clamp(ChargeRatio,0.f,1.f));
    const float Glow=FMath::Lerp(.65f,1.f,FMath::Clamp(ChargeRatio,0.f,1.f));
    const FVector Delta=End-Start;const float Length=FMath::Max(1.f,float(Delta.Size()));
    SetActorLocationAndRotation(Start,Delta.Rotation());
    Path->ClearSplinePoints(false);Path->AddSplinePoint(FVector::ZeroVector,ESplineCoordinateSpace::Local,false);
    Path->AddSplinePoint(FVector(Length,0,0),ESplineCoordinateSpace::Local,false);Path->UpdateSpline();
    FX->DeactivateImmediate();FX->SetAsset(nullptr);
    const auto Bounds=Tube->GetBounds();const float MeshDiameter=FMath::Max(1.f,2.f*Bounds.BoxExtent.X),MeshHeight=FMath::Max(1.f,2.f*Bounds.BoxExtent.Z);
    // An irregular rolling envelope surrounds a coherent white-blue core.
    // The fourth tube carries snapped, branched electric paths instead of coils.
    const float Widths[]={264.f,168.f,87.f,291.f},Opacities[]={.45f,.93f,1.f,1.f},Emissions[]={12.f,21.f,31.5f,42.f};
    const FLinearColor Colors[]={FLinearColor::FromSRGBColor(FColor(65,145,255)),FLinearColor::FromSRGBColor(FColor(125,225,255)),
        FLinearColor::FromSRGBColor(FColor(225,246,255)),FLinearColor::FromSRGBColor(FColor(170,225,255))};
    FRandomStream Cosmetic{int32(FPlatformTime::Cycles())};const float Seed=Cosmetic.FRandRange(0.f,100.f);
    const FVector Axis=Delta.GetSafeNormal();
    auto MakeTube=[&](const FString& Name,UMaterialInterface* Material,float Diameter)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(this,*Name);AddInstanceComponent(Mesh);Mesh->SetupAttachment(Path);
        Mesh->SetStaticMesh(Tube);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);Mesh->SetCanEverAffectNavigation(false);
        Mesh->SetCastShadow(false);Mesh->SetReceivesDecals(false);Mesh->SetRelativeRotation(FRotator(90,0,0));
        Mesh->SetRelativeScale3D(FVector(Diameter/MeshDiameter,Diameter/MeshDiameter,Length/MeshHeight));Mesh->SetBoundsScale(1.7f);
        auto* MaterialInstance=UMaterialInstanceDynamic::Create(Material,Mesh);Mesh->SetMaterial(0,MaterialInstance);Mesh->RegisterComponent();return Mesh;
    };
    for(int32 I=0;I<4;++I)
    {
        auto* Mesh=MakeTube(FString::Printf(TEXT("FluxLayer%d"),I),I==3?FilamentMaterial:BodyMaterial,Widths[I]*Visual);
        Mesh->SetRelativeLocation(FVector(Length*.5f,0,0));Mesh->SetTranslucentSortPriority(I+1);
        auto* Material=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0));
        Material->SetVectorParameterValue(TEXT("BeamColor"),Colors[I]);Material->SetScalarParameterValue(TEXT("Opacity"),Opacities[I]);
        Material->SetScalarParameterValue(TEXT("Emission"),Emissions[I]*Glow);Material->SetScalarParameterValue(TEXT("Role"),I<3?2.f-I:3.f);
        Material->SetScalarParameterValue(TEXT("Radius"),Widths[I]*Visual*.5f);Material->SetScalarParameterValue(TEXT("Length"),Length);
        Material->SetScalarParameterValue(TEXT("Seed"),Seed+I*.731f);
        Material->SetVectorParameterValue(TEXT("Origin"),FLinearColor(Start.X,Start.Y,Start.Z,0.f));
        Material->SetVectorParameterValue(TEXT("Axis"),FLinearColor(Axis.X,Axis.Y,Axis.Z,0.f));
    }
    ImpactLight->SetRelativeLocation(FVector(Length,0,0));ImpactLight->SetLightColor(FLinearColor(.4f,.7f,1.f));ImpactLight->SetAttenuationRadius(210.f);
    BaseLight=3600.f*Visual;ImpactLight->SetIntensity(BaseLight);SetLifeSpan(Hold+Fade*1.55f+.05f);
}

AFPSLightningArc::AFPSLightningArc()
{
    PrimaryActorTick.bCanEverTick=true;
    Path=CreateDefaultSubobject<USplineComponent>(TEXT("LightningPath"));SetRootComponent(Path);
    Path->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    FX=CreateDefaultSubobject<UNiagaraComponent>(TEXT("ElectricArc"));FX->SetupAttachment(Path);FX->SetAutoActivate(false);
    ImpactLight=CreateDefaultSubobject<UPointLightComponent>(TEXT("ContactLight"));ImpactLight->SetupAttachment(Path);
    ImpactLight->SetCastShadows(false);ImpactLight->SetIntensity(0);ImpactLight->SetAttenuationRadius(140);
    ImpactLight->SetLightColor(FLinearColor(.40f,.20f,1));ImpactLight->SetVolumetricScatteringIntensity(0);
    // 联机：链式电弧/雷枪柱由服务端生成，复制到各端自建表现。
    bReplicates=true;
}
void AFPSLightningArc::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSLightningArc,NetKind);
    DOREPLIFETIME(AFPSLightningArc,NetStart);
    DOREPLIFETIME(AFPSLightningArc,NetEnd);
    DOREPLIFETIME(AFPSLightningArc,NetSpell);
    DOREPLIFETIME(AFPSLightningArc,NetWidth);
    DOREPLIFETIME(AFPSLightningArc,NetBrightness);
    DOREPLIFETIME(AFPSLightningArc,NetChargeRatio);
    DOREPLIFETIME(AFPSLightningArc,NetContactLight);
}
void AFPSLightningArc::InitializeArc(UNiagaraSystem* System,const FVector& Start,const FVector& End,const FLightningCast& Spell,float Width,bool bContactLight,float Brightness)
{
    SetActorLocation(Start);Hold=Spell.Duration;Fade=FMath::Max(.01f,Spell.Fade);
    BaseBrightness=Brightness;
    if(HasAuthority()){NetKind=0;NetStart=Start;NetEnd=End;NetSpell=Spell;NetWidth=Width;NetBrightness=Brightness;NetContactLight=bContactLight;}
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
// 远端副本：复制字段就位后自载素材重演。kind0=链式电弧(闪电链资产)；kind1=雷枪柱(雷电魔法的管道+双层材质)。
void AFPSLightningArc::NetInit()
{
    if(bNetInit||NetSpell.Duration<=0)return;
    if(NetKind==1)
    {
        auto* Tube=LoadObject<UStaticMesh>(nullptr,TEXT("/Game/Skills/ElectricMagic/ThunderFluxV3/SM_ThunderFluxTube.SM_ThunderFluxTube"));
        auto* Body=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/ElectricMagic/ThunderFluxV3/M_ThunderFluxBody.M_ThunderFluxBody"));
        auto* Filament=LoadObject<UMaterialInterface>(nullptr,TEXT("/Game/Skills/ElectricMagic/ThunderFluxV3/M_ThunderFluxFilaments.M_ThunderFluxFilaments"));
        if(!Tube||!Body||!Filament)return;
        InitializeColumn(Tube,Body,Filament,NetStart,NetEnd,NetSpell,NetChargeRatio);
    }
    else
    {
        auto* System=LoadObject<UNiagaraSystem>(nullptr,TEXT("/Game/Skills/Lightning/NS_LightningChain.NS_LightningChain"));
        if(!System)return;
        InitializeArc(System,NetStart,NetEnd,NetSpell,NetWidth,NetContactLight,NetBrightness);
    }
    bNetInit=true;
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
    // 远端副本：首包到齐后 NetInit 自建表现；刃弧（blade）仍是本地特效不走复制。
    if(!HasAuthority()&&!bBladeAttached){NetInit();if(!bNetInit)return;}
    if(bBladeAttached&&!BoundBlade.IsValid()){Destroy();return;}
    Super::Tick(Delta);Age+=Delta;
    if(Tags.Contains(TEXT("ThunderLanceColumn")))
    {
        // Staggered collapse: the coherent core dies first, the envelope follows,
        // and the snapped filaments linger as the discharge's afterglow.
        static const float LayerDelay[]={.20f,.10f,0.f,.45f};
        TInlineComponentArray<UStaticMeshComponent*> Meshes(this);
        for(auto* Mesh:Meshes)
        {
            const int32 Layer=FMath::Clamp(Mesh->TranslucencySortPriority-1,0,3);
            const float Delay=LayerDelay[Layer]*Fade;
            const float Alpha=Age<Hold+Delay?1.f:FMath::Clamp(1.f-(Age-Hold-Delay)/Fade,0.f,1.f);
            if(auto* Material=Cast<UMaterialInstanceDynamic>(Mesh->GetMaterial(0)))
            {Material->SetScalarParameterValue(TEXT("BeamAlpha"),Alpha);Material->SetScalarParameterValue(TEXT("BeamAge"),Age);}
        }
        const float LightAlpha=Age<Hold?1.f:FMath::Clamp(1.f-(Age-Hold)/Fade,0.f,1.f);
        ImpactLight->SetIntensity(BaseLight*LightAlpha*(1.f+1.25f*FMath::Exp(-Age*32.f)));if(Age>=Hold+Fade*1.45f)Destroy();return;
    }
    if(bBladeAttached)SetActorRelativeRotation(FQuat(FVector::ForwardVector,Age*.7f));
    const float Alpha=Age<Hold?1.f:FMath::Clamp(1-(Age-Hold)/Fade,0.f,1.f);
    const float Flash=BladeFlash();
    FX->SetVariableFloat(TEXT("User._Brightness"),BaseBrightness*Alpha*(1.f+.55f*Flash));
    ImpactLight->SetIntensity(BaseLight*Alpha*(bBladeAttached?.45f+.90f*Flash:FMath::Max(0.f,1-Age/.3f)));
    if(Age>=Hold+Fade){FX->DeactivateImmediate();Destroy();}
}
