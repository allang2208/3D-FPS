#include "OathJudgmentVisualComponent.h"
#include "BeiweiSwordTrailComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Sound/SoundBase.h"
#include "Kismet/GameplayStatics.h"

namespace
{
void OathRibbon(UE::Geometry::FDynamicMesh3& M,int32 Steps,float Width,TFunctionRef<FVector(float)> Curve)
{
    auto* UV=M.Attributes()->PrimaryUV();auto* N=M.Attributes()->PrimaryNormals();
    int32 Previous[2]={};FVector Side=FVector::ZeroVector;
    for(int32 I=0;I<=Steps;++I)
    {
        const float U=float(I)/Steps;const FVector P=Curve(U);
        const FVector Tangent=(Curve(FMath::Min(1.f,U+.01f))-Curve(FMath::Max(0.f,U-.01f))).GetSafeNormal();
        Side=FVector::VectorPlaneProject(Side,Tangent).GetSafeNormal();
        if(Side.IsNearlyZero()){FVector Other;Tangent.FindBestAxisVectors(Side,Other);}
        const float Radius=Width*(.12f+.88f*FMath::Sin(PI*U));int32 V[2];
        for(int32 E=0;E<2;++E)
        {V[E]=M.AppendVertex(P+Side*(E?Radius:-Radius));UV->AppendElement(FVector2f(U,E));N->AppendElement(FVector3f(0,0,1));}
        if(I)for(const auto T:{UE::Geometry::FIndex3i(Previous[0],V[0],Previous[1]),UE::Geometry::FIndex3i(Previous[1],V[0],V[1])})
        {const int32 Id=M.AppendTriangle(T);UV->SetTriangle(Id,T);N->SetTriangle(Id,T);}
        Previous[0]=V[0];Previous[1]=V[1];
    }
}

void SetOathSurface(UMeshComponent* Mesh,float Charge,float Ready,float Release)
{
    if(!Mesh)return;
    for(int32 I=0;I<Mesh->GetNumMaterials();++I)
    {
        auto* MID=Cast<UMaterialInstanceDynamic>(Mesh->GetOverlayMaterial(true,I));
        if(!MID||!MID->GetBaseMaterial()->GetName().Contains(TEXT("HighlandOath")))continue;
        MID->SetScalarParameterValue(TEXT("OathCharge"),Charge);
        MID->SetScalarParameterValue(TEXT("OathReady"),Ready);
        MID->SetScalarParameterValue(TEXT("OathRelease"),Release);
    }
}
}

UOathJudgmentVisualComponent::UOathJudgmentVisualComponent()
{
    SetMobility(EComponentMobility::Movable);SetCollisionEnabled(ECollisionEnabled::NoCollision);
    SetGenerateOverlapEvents(false);SetCanEverAffectNavigation(false);SetCastShadow(false);SetReceivesDecals(false);
    bVisibleInRayTracing=false;bAffectDistanceFieldLighting=false;SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
    SetVisibility(false);PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
}
UOathJudgmentVisualComponent* UOathJudgmentVisualComponent::CreateFor(AActor* Owner,bool FirstPerson)
{
    auto* FX=NewObject<UOathJudgmentVisualComponent>(Owner);Owner->AddInstanceComponent(FX);
    FX->SetupAttachment(Owner->GetRootComponent());FX->SetAbsolute(true,true,true);FX->SetOnlyOwnerSee(FirstPerson);
    FX->RegisterComponent();return FX;
}
void UOathJudgmentVisualComponent::OnRegister()
{
    Super::OnRegister();
    if(!GetWorld()||!GetWorld()->IsGameWorld()||GetNetMode()==NM_DedicatedServer||LightMaterial||MaterialLoad)return;
    const FSoftObjectPath Path(FString(HighlandOathRune::Root)+TEXT("M_OathLight.M_OathLight"));
    const FSoftObjectPath SoundPath(FString(HighlandOathRune::Root)+TEXT("S_OathImpact.S_OathImpact"));
    const FSoftObjectPath WakePath(FString(HighlandOathRune::Root)+TEXT("M_OathJudgmentWake.M_OathJudgmentWake"));
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Path,SoundPath,WakePath},FStreamableDelegate::CreateWeakLambda(this,[this,Path,SoundPath]()
    {LightMaterial=Cast<UMaterialInterface>(Path.ResolveObject());ImpactSound=Cast<USoundBase>(SoundPath.ResolveObject());if(LightMaterial)SetMaterial(0,LightMaterial);}));
}
void UOathJudgmentVisualComponent::UpdateWake(UMeshComponent* Blade,const FVector& Base,const FVector& Tip,
    const FHighlandOathPresentation& State,double Now,EOathStroke Stroke)
{
    if(!Blade)return;
    const FVector Side=Blade->GetForwardVector();
    if(PreviousBlade.Get()!=Blade)
    {
        PendingStroke.Reset();LastStroke=EOathStroke::None;
        if(Wake)Wake->Clear();
    }
    const auto Slice=[Stroke](const FVector& Root,const FVector& Point,const FVector& Across,double Time)
    {
        // Sweep across the point itself on a thrust; its axis and velocity can be collinear.
        return Stroke==EOathStroke::Thrust?FWakeSlice{Point-Across*4.,Point+Across*4.,Time}:FWakeSlice{Root,Point,Time};
    };
    if(!PendingStroke.IsEmpty() && Now-PendingStroke.Last().At>=HighlandOathRune::TrailSeconds)
        PendingStroke.Reset();
    if(Stroke!=EOathStroke::None)
    {
        if(Stroke!=LastStroke)
        {
            PendingStroke.Reset();
            if(PreviousBlade.Get()==Blade && Now-PreviousPoseAt>=0. && Now-PreviousPoseAt<.22 &&
                FVector::DistSquared(PreviousBase,Base)<250.*250. &&
                (Stroke!=EOathStroke::Thrust || !PreviousTip.Equals(Tip,1.)))
                PendingStroke.Add(Slice(PreviousBase,PreviousTip,PreviousSide,PreviousPoseAt));
            else if(Stroke==EOathStroke::Thrust)
                PendingStroke.Add(Slice(Base,FMath::Lerp(Base,Tip,.68f),Side,Now));
        }
        // Keep the start pose when a high-refresh client samples a delayed receipt.
        if(PendingStroke.Num()==24)PendingStroke.RemoveAt(1,1,EAllowShrinking::No);
        PendingStroke.Add(Slice(Base,Tip,Side,Now));
    }

    // Body animation and the authoritative oath receipt replicate independently.
    // Replay only this strike's recorded slices, at their original fade ages.
    const bool Judgment=State.Phase==2 && !PendingStroke.IsEmpty() &&
        PendingStroke.Last().At>=State.ReleaseAt-.10 && PendingStroke[0].At<=State.ReleaseAt+.45;
    if(Judgment)
    {
        if(!Wake)
        {
            Wake=NewObject<UBeiweiSwordTrailComponent>(GetOwner());
            GetOwner()->AddInstanceComponent(Wake);
            Wake->SetView(bOnlyOwnerSee,false);
            Wake->ConfigureSingleMaterial(FSoftObjectPath(FString(HighlandOathRune::Root)+
                TEXT("M_OathJudgmentWake.M_OathJudgmentWake")),HighlandOathRune::TrailSeconds);
            Wake->RegisterComponent();
        }
        if(WakeReleaseAt!=State.ReleaseAt)Wake->Feed(Base,Tip,false);
        for(const FWakeSlice& Sample:PendingStroke)
            Wake->Feed(Sample.Root,Sample.Edge,true,ESwordTrailPalette::Gold,Now-Sample.At);
        WakeReleaseAt=State.ReleaseAt;
        PendingStroke.Reset();
    }
    if(Stroke==EOathStroke::None && Wake)Wake->Feed(Base,Tip,false);
    LastStroke=Stroke;
    PreviousBlade=Blade;PreviousBase=Base;PreviousTip=Tip;PreviousSide=Side;PreviousPoseAt=Now;
}

void UOathJudgmentVisualComponent::Present(UMeshComponent* Blade,const FVector& Base,const FVector& Tip,
    const FHighlandOathPresentation& State,double Now,double ImpactAt,const FVector& ImpactPoint,EOathStroke Stroke)
{
    UpdateWake(Blade,Base,Tip,State,Now,Stroke);
    const float Charge=State.Phase==1?float(FMath::Clamp(1.-(State.FullAt-Now)/FMath::Max(.01f,State.Duration),0.,1.)):0.f;
    const float Ready=State.Phase==1&&HighlandOathRune::InWindow(Now,State.FullAt)?1.f:0.f;
    const float Release=State.Phase==2?float(FMath::Clamp(1.-(Now-State.ReleaseAt)/.55,0.,1.)):0.f;
    SetOathSurface(Blade,Charge,Ready,Release);
    if(Blade)for(const auto& Child:Blade->GetAttachChildren())SetOathSurface(Cast<UMeshComponent>(Child.Get()),Charge,Ready,Release);
    const float HitAge=float(Now-ImpactAt);
    if(HitAge>=0.f&&HitAge<.42f&&ImpactAt>LastImpactSound&&ImpactSound)
    {LastImpactSound=ImpactAt;UGameplayStatics::PlaySoundAtLocation(this,ImpactSound,ImpactPoint,.65f);}
    if(!LightMaterial||(Release<=0.f&&(HitAge<0.f||HitAge>=.42f))){SetVisibility(false);SetComponentTickEnabled(false);return;}
    const FVector Axis=(Tip-Base).GetSafeNormal();FVector A,B;Axis.FindBestAxisVectors(A,B);
    SetWorldLocationAndRotation(Base,FQuat::Identity);
    const float Length=FVector::Distance(Base,Tip);
    UE::Geometry::FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    const float Age=float(Now-State.ReleaseAt);
    if(Release>0.f)for(int32 Ring=0;Ring<3;++Ring)
    {
        const float Travel=FMath::Clamp((Age-Ring*.045f)/.22f,0.f,1.f);
        const float Fade=1.f-FMath::SmoothStep(.24f,.55f,Age);
        const FVector Center=Axis*Length*FMath::Lerp(.18f+Ring*.18f,1.f,Travel);
        const float Radius=FMath::Lerp(5.8f,1.1f,Travel);
        OathRibbon(Mesh,28,.27f*Fade,[&](float U)
        {const float Angle=2.f*PI*U;return Center+(A*FMath::Cos(Angle)+B*FMath::Sin(Angle))*Radius;});
    }
    if(Release>0.f)
    {
        const float Pulse=FMath::SmoothStep(.12f,.20f,Age)*(1.f-FMath::SmoothStep(.30f,.55f,Age));
        if(Pulse>0.f)OathRibbon(Mesh,4,.38f*Pulse,[&](float U)
        {return Axis*(Length+(U-.5f)*12.f*Pulse);});
    }
    if(HitAge>=0.f&&HitAge<.42f)
    {
        const FVector Center=ImpactPoint-Base;const float Fade=1.f-HitAge/.42f;
        for(int32 I=0;I<12;++I)
        {
            const float Angle=2.f*PI*I/12.f;
            const FVector Ray=(A*FMath::Cos(Angle)+B*FMath::Sin(Angle)+Axis*(I%2?.3f:-.3f)).GetSafeNormal();
            const float Distance=2.f+HitAge*(20.f+I*2.f);
            OathRibbon(Mesh,3,.22f*Fade,[&](float U){return Center+Ray*(Distance+U*4.f*Fade);});
        }
        OathRibbon(Mesh,3,.5f*Fade,[&](float U){return Center+Axis*((U-.5f)*18.f*Fade);});
    }
    SetMesh(MoveTemp(Mesh));SetVisibility(true);LastPresented=GetWorld()->GetTimeSeconds();SetComponentTickEnabled(true);
}
void UOathJudgmentVisualComponent::Hide(bool DiscardWake)
{
    SetVisibility(false);SetComponentTickEnabled(false);PreviousBlade.Reset();
    PendingStroke.Reset();LastStroke=EOathStroke::None;
    if(Wake)
    {
        if(DiscardWake)Wake->Clear();
        else Wake->Feed(FVector::ZeroVector,FVector::ZeroVector,false);
    }
}
void UOathJudgmentVisualComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{Super::TickComponent(Delta,Type,Tick);if(GetWorld()->GetTimeSeconds()-LastPresented>.12)Hide();}
void UOathJudgmentVisualComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(MaterialLoad)MaterialLoad->CancelHandle();
    MaterialLoad.Reset();
    if(Wake){Wake->DestroyComponent();Wake=nullptr;}
    Super::EndPlay(Reason);
}
