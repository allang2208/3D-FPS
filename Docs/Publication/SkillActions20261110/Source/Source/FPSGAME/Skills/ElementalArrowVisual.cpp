#include "ElementalArrowVisual.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "Components/SceneComponent.h"
#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "GameFramework/PlayerController.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"

namespace
{
// First-person arrows retain full detail; teammate and flying arrows share a world budget.
TArray<TWeakObjectPtr<UElementalArrowVisual>> FlyingVisuals;
constexpr int32 MaxFlyingVisuals=12,ArcPoints=17;
}

void UElementalArrowVisual::Clear()
{
    if(Load)Load->CancelHandle();Load.Reset();
    for(const auto& FX:Effects)if(FX)FX->DestroyComponent();Effects.Reset();
    for(const auto& Path:Paths)if(Path)Path->DestroyComponent();Paths.Reset();Assets.Reset();
    FlyingVisuals.RemoveAll([this](const auto& V){return !V.IsValid()||V.Get()==this;});
    Current=EArrowElement::None;bReady=bBuilt=false;Age=EnvironmentAge=0;FluidDetail=1;Wind=FVector::ZeroVector;
    bFireHistory=false;FireGeometry.Reset();FireBaseFlow=FireTipFlow=FVector::ZeroVector;
}
void UElementalArrowVisual::EndPlay(const EEndPlayReason::Type Reason){Clear();Super::EndPlay(Reason);}
void UElementalArrowVisual::OnComponentDestroyed(bool bDestroyingHierarchy){Clear();Super::OnComponentDestroyed(bDestroyingHierarchy);}
void UElementalArrowVisual::Build(const FVector& Tail,const FVector& Tip)
{
    auto AddFX=[&](const TCHAR* Asset)->UNiagaraComponent*
    {
        auto* System=Cast<UNiagaraSystem>(FSoftObjectPath(Asset).ResolveObject());if(!System)return nullptr;
        auto* FX=NewObject<UNiagaraComponent>(GetOwner(),NAME_None,RF_Transient);GetOwner()->AddInstanceComponent(FX);
        FX->SetAutoActivate(false);FX->SetAsset(System);FX->SetCastShadow(false);FX->SetVisibleInRayTracing(false);
        FX->RegisterComponent();FX->SetWorldLocation(Tip);FX->AddTickPrerequisiteActor(GetOwner());
        FX->SetTickBehavior(ENiagaraTickBehavior::UsePrereqs);Effects.Add(FX);return FX;
    };
    if(Current==EArrowElement::Fire)
    {
        // One fitted copy of the restored weapon flame, with its native random tongues.
        if(auto* FX=AddFX(ElementalArrow::Flame))
        {
            FX->SetAbsolute(false,false,true);FX->SetAutoDestroy(false);
            FX->PrimaryComponentTick.TickGroup=TG_LastDemotable;
            FX->SetTickBehavior(ENiagaraTickBehavior::UseComponentTickGroup);
        }
    }
    else if(Current==EArrowElement::Ice)
    {
        if(auto* FX=AddFX(ElementalArrow::Mist))
        {
            FX->SetAbsolute(false,false,true);FX->SetAutoDestroy(false);
            FX->PrimaryComponentTick.TickGroup=TG_LastDemotable;
            FX->SetTickBehavior(ENiagaraTickBehavior::UseComponentTickGroup);
        }
    }
    else if(Current==EArrowElement::Lightning)
    {
        for(int32 I=0;I<3;++I)
        {
            auto* Path=NewObject<USplineComponent>(GetOwner(),NAME_None,RF_Transient);GetOwner()->AddInstanceComponent(Path);
            Path->SetCollisionEnabled(ECollisionEnabled::NoCollision);Path->RegisterComponent();
            Path->ClearSplinePoints(false);
            for(int32 J=0;J<ArcPoints;++J)
            {
                Path->AddSplinePoint(FVector::ZeroVector,ESplineCoordinateSpace::Local,false);
                Path->SetSplinePointType(J,ESplinePointType::Linear,false);
            }
            Path->UpdateSpline();Paths.Add(Path);
            if(auto* FX=AddFX(ElementalArrow::Blade))
            {
                FX->SetVariableObject(TEXT("User.BladeSpline"),Path);
                FX->SetVariableFloat(TEXT("User.Progress"),1);FX->SetVariableFloat(TEXT("User.Jitter"),0);
                FX->SetVariableFloat(TEXT("User._DetailSpeed"),.0013f);FX->SetVariableFloat(TEXT("User.MainPowerSpeed"),8);
                FX->SetVariableFloat(TEXT("User._DetailSpeedOffset"),6);
                FX->SetVariableBool(TEXT("User.AddDetail"),false);FX->SetVariableBool(TEXT("User.AddMainPower"),true);
            }
        }
    }
    Previous=Tip;bBuilt=true;
}
void UElementalArrowVisual::UpdateWarmFire(const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation,float Detail,USceneComponent* ArrowSource)
{
    if(Effects.IsEmpty()||!Effects[0])return;
    auto* FX=Effects[0].Get();
    if(!ArrowSource)ArrowSource=GetOwner()->GetRootComponent();
    if(!IsValid(ArrowSource))return;
    FVector ActualTail=Tail,ActualTip=Tip;
    const auto* Rod=Cast<UStaticMeshComponent>(ArrowSource);
    UStaticMesh* Geometry=Rod?Rod->GetStaticMesh():nullptr;
    if(Geometry)
    {
        // Use the rendered shaft, excluding the asymmetric fletching's lateral offset.
        const auto Bounds=Geometry->GetBounds();
        const FVector Axis=Bounds.BoxExtent.X>Bounds.BoxExtent.Z?FVector::XAxisVector:FVector::ZAxisVector;
        const FVector Centre=Axis*FVector::DotProduct(Bounds.Origin,Axis);
        const FVector Extent=Axis*FVector::DotProduct(Bounds.BoxExtent,Axis);
        ActualTail=ArrowSource->GetComponentTransform().TransformPosition(Centre-Extent);
        ActualTip=ArrowSource->GetComponentTransform().TransformPosition(Centre+Extent);
    }
    const float Length=float(FVector::Distance(ActualTail,ActualTip));
    const float FlameLength=FMath::Min(Length,FMath::Clamp(Length*.45f,12.f,36.f));
    const FVector Direction=(ActualTip-ActualTail).GetSafeNormal(UE_SMALL_NUMBER,FVector::ForwardVector);
    const FVector Base=ActualTip-Direction*FlameLength;
    const FQuat Frame=ArrowSource->GetComponentQuat();
    const FVector Scale=ArrowSource->GetComponentScale();
    const bool AttachmentChanged=FX->GetAttachParent()!=ArrowSource;
    const bool Reset=!bFireHistory||AttachmentChanged||FireGeometry.Get()!=Geometry||!FireSourceScale.Equals(Scale,.0001)
        ||FVector::DistSquared(Base,FireBase)>FMath::Square(1200.f);
    if(AttachmentChanged)
    {
        if(auto* Old=FX->GetAttachParent())FX->RemoveTickPrerequisiteComponent(Old);
        FX->AttachToComponent(ArrowSource,FAttachmentTransformRules::KeepWorldTransform);
        FX->AddTickPrerequisiteComponent(ArrowSource);
    }
    const bool FirstPerson=!bFlying&&!bWorldPresentation;
    const auto* Primitive=Cast<UPrimitiveComponent>(ArrowSource);
    const auto PrimitiveType=FirstPerson&&Primitive?Primitive->FirstPersonPrimitiveType:EFirstPersonPrimitiveType::None;
    if(FX->FirstPersonPrimitiveType!=PrimitiveType)FX->SetFirstPersonPrimitiveType(PrimitiveType);
    if(FX->bOnlyOwnerSee!=FirstPerson)FX->SetOnlyOwnerSee(FirstPerson);
    FX->SetForceSolo(FirstPerson);
    // Roots are never smoothed: attachment also follows late camera/arrow transforms.
    FX->SetWorldLocationAndRotation(Base,Frame);FX->SetWorldScale3D(FVector::OneVector);
    if(Reset)FireBaseFlow=FireTipFlow=FVector::ZeroVector;
    else if(Delta>SMALL_NUMBER)
    {
        const double Blend=1.-FMath::Exp(-Delta/.060);
        const FVector Travel=bFlying?FVector::ZeroVector:GetOwner()->GetVelocity();
        FireBaseFlow=FMath::Lerp(FireBaseFlow,((Base-FireBase)/Delta-Travel).GetClampedToMaxSize(1500.),Blend);
        FireTipFlow=FMath::Lerp(FireTipFlow,((ActualTip-FireTip)/Delta-Travel).GetClampedToMaxSize(1500.),Blend);
    }
    // Keep the cross section in the arrow's frame, without camera-dependent axis flips.
    FVector Side=FVector::VectorPlaneProject(Frame.GetAxisY(),Direction).GetSafeNormal();
    if(Side.IsNearlyZero())Side=FVector::VectorPlaneProject(Frame.GetAxisZ(),Direction).GetSafeNormal();
    const FVector Normal=FVector::CrossProduct(Direction,Side).GetSafeNormal();
    FX->SetVariableVec3(TEXT("User.WeaponEnd"),Frame.UnrotateVector(ActualTip-Base));
    FX->SetVariableVec3(TEXT("User.BladeSide"),Frame.UnrotateVector(Side));
    FX->SetVariableVec3(TEXT("User.WeaponSide"),Frame.UnrotateVector(Side));
    FX->SetVariableVec3(TEXT("User.WeaponNormal"),Frame.UnrotateVector(Normal));
    FX->SetVariableVec3(TEXT("User.FlameUp"),Frame.UnrotateVector(FVector::UpVector));
    FX->SetVariableVec3(TEXT("User.BaseFlow"),Frame.UnrotateVector(FireBaseFlow));
    FX->SetVariableVec3(TEXT("User.TipFlow"),Frame.UnrotateVector(FireTipFlow));
    FX->SetVariableFloat(TEXT("User.SurfaceMode"),0.f);
    static const FName SurfaceNames[]={TEXT("User.Surface0"),TEXT("User.Surface1"),TEXT("User.Surface2"),TEXT("User.Surface3"),
        TEXT("User.Surface4"),TEXT("User.Surface5"),TEXT("User.Surface6"),TEXT("User.Surface7")};
    const float Radius=FMath::Clamp(Length*.01f,.45f,.9f);
    for(int32 Station=0;Station<8;++Station)
    {
        const float R=Radius*FMath::Lerp(1.f,.22f,float(Station)/7.f);
        FX->SetVariableVec4(SurfaceNames[Station],FVector4(0,0,R,R));
    }
    FX->SetVariableFloat(TEXT("User.WeaponSize"),.36f);
    FX->SetVariableFloat(TEXT("User.Coverage"),FMath::Clamp(FlameLength/60.f,.15f,1.f));
    FX->SetVariableFloat(TEXT("User.MotionEnergy"),FMath::Clamp(float(FMath::Max(FireBaseFlow.Size(),FireTipFlow.Size())/900.),0.f,1.f));
    FX->SetVariableFloat(TEXT("User.FlameClock"),GetWorld()->GetTimeSeconds());
    FX->SetVariableFloat(TEXT("User.Detail"),Detail);
    FX->SetVariableFloat(TEXT("User.VariationSeed"),float(GetUniqueID()&0xffff)*.015625f);
    FX->SetVariableFloat(TEXT("User.Fade"),1.f);
    if(Reset)FX->ReinitializeSystem();else if(!FX->IsActive())FX->Activate(true);
    FireBase=Base;FireTip=ActualTip;FireSourceScale=Scale;FireGeometry=Geometry;bFireHistory=true;
}
void UElementalArrowVisual::UpdateColdMist(const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation,float Detail,USceneComponent* ArrowSource)
{
    if(Effects.IsEmpty()||!Effects[0])return;
    auto* FX=Effects[0].Get();
    if(!ArrowSource)ArrowSource=GetOwner()->GetRootComponent();
    if(!IsValid(ArrowSource))return;
    FVector ActualTail=Tail,ActualTip=Tip;
    if(const auto* Rod=Cast<UStaticMeshComponent>(ArrowSource);Rod&&Rod->GetStaticMesh())
    {
        const auto Bounds=Rod->GetStaticMesh()->GetBounds();
        const FVector Axis=Bounds.BoxExtent.X>Bounds.BoxExtent.Z?FVector::XAxisVector:FVector::ZAxisVector;
        const FVector Centre=Axis*FVector::DotProduct(Bounds.Origin,Axis);
        const FVector Extent=Axis*FVector::DotProduct(Bounds.BoxExtent,Axis);
        ActualTail=ArrowSource->GetComponentTransform().TransformPosition(Centre-Extent);
        ActualTip=ArrowSource->GetComponentTransform().TransformPosition(Centre+Extent);
    }
    const FVector Base=FMath::Lerp(ActualTail,ActualTip,.28f);
    const FVector Direction=(ActualTip-Base).GetSafeNormal(UE_SMALL_NUMBER,FVector::ForwardVector);
    const FQuat Frame=ArrowSource->GetComponentQuat();
    const bool Reattach=FX->GetAttachParent()!=ArrowSource;
    if(Reattach)
    {
        if(auto* Old=FX->GetAttachParent())FX->RemoveTickPrerequisiteComponent(Old);
        FX->AttachToComponent(ArrowSource,FAttachmentTransformRules::KeepWorldTransform);
        FX->AddTickPrerequisiteComponent(ArrowSource);
    }
    const bool FirstPerson=!bFlying&&!bWorldPresentation;
    const auto* Primitive=Cast<UPrimitiveComponent>(ArrowSource);
    const auto PrimitiveType=FirstPerson&&Primitive?Primitive->FirstPersonPrimitiveType:EFirstPersonPrimitiveType::None;
    if(FX->FirstPersonPrimitiveType!=PrimitiveType)FX->SetFirstPersonPrimitiveType(PrimitiveType);
    if(FX->bOnlyOwnerSee!=FirstPerson)FX->SetOnlyOwnerSee(FirstPerson);
    FX->SetForceSolo(FirstPerson);
    FX->SetWorldLocationAndRotation(Base,Frame);FX->SetWorldScale3D(FVector::OneVector);
    EnvironmentAge-=FMath::Max(0.f,Delta);
    if(EnvironmentAge<=0.f)
    {
        EnvironmentAge=.12f;FluidDetail=1;Wind=FVector::ZeroVector;
        if(auto* Fluid=GetWorld()->GetSubsystem<UFluidPresentationSubsystem>())
        {
            constexpr int32 Wanted=12;
            FluidDetail=FMath::Max(.35f,float(Fluid->AllocateDetail(ActualTip,Wanted,FirstPerson))/Wanted);
            Wind=(Fluid->WindAt(ActualTip)*.10f).GetClampedToMaxSize(10.f);
        }
    }
    FVector Side=FVector::VectorPlaneProject(Frame.GetAxisY(),Direction).GetSafeNormal();
    if(Side.IsNearlyZero())Side=FVector::VectorPlaneProject(Frame.GetAxisZ(),Direction).GetSafeNormal();
    FX->SetVariableVec3(TEXT("User.ArrowEnd"),Frame.UnrotateVector(ActualTip-Base));
    FX->SetVariableVec3(TEXT("User.Side"),Frame.UnrotateVector(Side));
    FX->SetVariableVec3(TEXT("User.Up"),Frame.UnrotateVector(FVector::CrossProduct(Direction,Side).GetSafeNormal()));
    FX->SetVariableVec3(TEXT("User.Lift"),Frame.UnrotateVector(FVector::UpVector));
    FX->SetVariableVec3(TEXT("User.Wind"),Frame.UnrotateVector(Wind));
    FX->SetVariableFloat(TEXT("User.Flight"),bFlying?1.f:0.f);
    FX->SetVariableFloat(TEXT("User.Detail"),Detail*FluidDetail);
    FX->SetVariableFloat(TEXT("User.VariationSeed"),float(GetUniqueID()&0xffff)*.015625f);
    if(Reattach)FX->ReinitializeSystem();else if(!FX->IsActive())FX->Activate(true);
}
void UElementalArrowVisual::Update(EArrowElement Element,const FVector& Tail,const FVector& Tip,float Delta,bool bFlying,bool bWorldPresentation,USceneComponent* ArrowSource)
{
    if(GetNetMode()==NM_DedicatedServer)return;
    const bool WorldPresentation=bFlying||bWorldPresentation;
    float DistanceDetail=1.f;
    if(WorldPresentation)if(const auto* PC=GetWorld()->GetFirstPlayerController();PC&&PC->PlayerCameraManager)
    {
        const double Distance=FVector::DistSquared(PC->PlayerCameraManager->GetCameraLocation(),Tip);
        if(Distance>FMath::Square(6000.f)){if(Current!=EArrowElement::None)Clear();return;}
        if(Distance>FMath::Square(2200.f))DistanceDetail=.55f;
    }
    if(Element!=Current)
    {
        Clear();if(!ElementalArrow::IsElement(Element))return;
        if(WorldPresentation)
        {
            int32 Count=0;for(const auto& V:FlyingVisuals)if(V.IsValid()&&V->GetWorld()==GetWorld())++Count;
            if(Count>=MaxFlyingVisuals)return;
            FlyingVisuals.Add(this);
        }
        Current=Element;
        TArray<FSoftObjectPath> AssetPaths;
        if(Element==EArrowElement::Fire)AssetPaths.Emplace(ElementalArrow::Flame);
        else if(Element==EArrowElement::Ice)AssetPaths.Emplace(ElementalArrow::Mist);
        else AssetPaths.Emplace(ElementalArrow::Blade);
        bool Ready=true;for(const auto& P:AssetPaths)Ready&=P.ResolveObject()!=nullptr;
        auto Retain=[this,AssetPaths]{for(const auto& P:AssetPaths)if(auto* A=P.ResolveObject())Assets.Add(A);bReady=true;};
        if(Ready)Retain();else Load=UAssetManager::GetStreamableManager().RequestAsyncLoad(AssetPaths,FStreamableDelegate::CreateWeakLambda(this,Retain));
    }
    if(!bReady||Element==EArrowElement::None)return;
    if(!bBuilt)Build(Tail,Tip);
    if(Current==EArrowElement::Fire)
    {
        UpdateWarmFire(Tail,Tip,Delta,bFlying,bWorldPresentation,DistanceDetail,ArrowSource);
        return;
    }
    if(Current==EArrowElement::Ice)
    {
        UpdateColdMist(Tail,Tip,Delta,bFlying,bWorldPresentation,DistanceDetail,ArrowSource);
        return;
    }
    const float Step=FMath::Max(0.f,Delta),PreviousAge=Age;Age+=Step;
    const FVector Direction=(Tip-Tail).GetSafeNormal(UE_SMALL_NUMBER,FVector::ForwardVector);
    FVector Side,Up;Direction.FindBestAxisVectors(Side,Up);
    for(int32 I=0;I<Effects.Num();++I)
    {
        auto* FX=Effects[I].Get();if(!FX)continue;
        if(Current==EArrowElement::Lightning)
        {
            if(!Paths.IsValidIndex(I))continue;
            auto* Path=Paths[I].Get();
            const float Period=.16f+I*.017f,Offset=I/3.f;
            const int32 Pulse=FMath::FloorToInt(Age/Period+Offset);
            const bool Restart=Pulse!=FMath::FloorToInt(PreviousAge/Period+Offset);
            const FVector Start=bFlying?Tail-Direction*(I==0?48.f:22.f):FMath::Lerp(Tail,Tip,I==0?.24f:.34f);
            const FVector End=FMath::Lerp(Tail,Tip,I==0?1.f:.95f);
            Path->SetWorldLocation(Start);
            for(int32 J=0;J<ArcPoints;++J)
            {
                const float T=float(J)/(ArcPoints-1),Envelope=FMath::Sin(T*PI);
                const float Phase=T*(I==0?16.f:25.f)+I*2.1f+Pulse*1.73f;
                const float Radius=Envelope*(I==0?3.8f:6.5f)*(bFlying?1.25f:1.f);
                const FVector Point=(End-Start)*T+(Side*FMath::Sin(Phase)+Up*FMath::Cos(Phase*1.37f))*Radius;
                Path->SetLocationAtSplinePoint(J,Point,ESplineCoordinateSpace::Local,false);
            }
            Path->UpdateSpline();
            FX->SetWorldLocation(Start);FX->SetSystemFixedBounds(Path->CalcBounds(FTransform::Identity).GetBox().ExpandBy(18));
            const float Width=I==0?.72f:I==1?.44f:.34f;
            FX->SetVariableFloat(TEXT("User._Width"),Width*(bFlying?1.3f:1.f));
            FX->SetVariableFloat(TEXT("User._Brightness"),(I==0?65.f:46.f)*(1.f+.08f*FMath::Sin(Age*18.f+I)));
            if(Restart||!FX->IsActive())FX->Activate(true);
            continue;
        }
    }
    Previous=Tip;
}
