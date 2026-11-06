#include "HighlandRidgeGatherComponent.h"
#include "HighlandRidgeThrust.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/RandomStream.h"

using UE::Geometry::FDynamicMesh3;

namespace
{
// Each strip has a broad face and a narrower crossing face. It stays readable
// head-on in first person as well as from beside or behind another player.
void AddStroke(FDynamicMesh3& Mesh,int32 Steps,double Width,TFunctionRef<FVector(double)> Curve)
{
    auto* UV=Mesh.Attributes()->PrimaryUV();
    auto* Normals=Mesh.Attributes()->PrimaryNormals();
    int32 Prev[4];
    FVector Side=FVector::ZeroVector;
    for(int32 I=0;I<=Steps;++I)
    {
        const double U=double(I)/Steps;
        const FVector P=Curve(U);
        const FVector Tangent=(Curve(FMath::Min(1.,U+.01))-Curve(FMath::Max(0.,U-.01))).GetSafeNormal();
        Side=FVector::VectorPlaneProject(Side,Tangent).GetSafeNormal();
        if(Side.IsNearlyZero()){FVector Other;Tangent.FindBestAxisVectors(Side,Other);}
        const double Radius=Width*(.025+.975*FMath::Sin(PI*U));
        const FVector Across[2]={Side*Radius,FVector::CrossProduct(Tangent,Side)*Radius*.52};
        int32 Curr[4];
        for(int32 Face=0;Face<2;++Face)
        {
            const int32 J=Face*2;
            for(int32 Edge=0;Edge<2;++Edge)
            {
                Curr[J+Edge]=Mesh.AppendVertex(P+(Edge?Across[Face]:-Across[Face]));
                UV->AppendElement(FVector2f(U,Edge));
                Normals->AppendElement(FVector3f(0,0,1));
            }
            if(I>0)
            {
                for(const UE::Geometry::FIndex3i& Tri:{UE::Geometry::FIndex3i(Prev[J],Curr[J],Prev[J+1]),
                    UE::Geometry::FIndex3i(Prev[J+1],Curr[J],Curr[J+1])})
                {
                    const int32 Id=Mesh.AppendTriangle(Tri);
                    UV->SetTriangle(Id,Tri);Normals->SetTriangle(Id,Tri);
                }
            }
        }
        for(int32 J=0;J<4;++J)Prev[J]=Curr[J];
    }
}
}

UHighlandRidgeGatherComponent::UHighlandRidgeGatherComponent()
{
    SetMobility(EComponentMobility::Movable);
    SetCollisionEnabled(ECollisionEnabled::NoCollision);SetGenerateOverlapEvents(false);
    SetCanEverAffectNavigation(false);SetCastShadow(false);SetReceivesDecals(false);
    bVisibleInRayTracing=false;bAffectDistanceFieldLighting=false;
    SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
    SetVisibility(false);
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
}

UHighlandRidgeGatherComponent* UHighlandRidgeGatherComponent::CreateFor(AActor* Owner,bool FirstPerson)
{
    auto* FX=NewObject<UHighlandRidgeGatherComponent>(Owner);
    Owner->AddInstanceComponent(FX);FX->SetupAttachment(Owner->GetRootComponent());
    FX->SetAbsolute(true,true,true);FX->SetOnlyOwnerSee(FirstPerson);FX->RegisterComponent();
    return FX;
}

void UHighlandRidgeGatherComponent::OnRegister()
{
    Super::OnRegister();
    if(!GetWorld()||!GetWorld()->IsGameWorld()||GetNetMode()==NM_DedicatedServer||GatherMaterial||MaterialLoad)return;
    const FSoftObjectPath Path(TEXT("/Game/Weapons/HighlandClaymore20260922/RidgeThrust20261105/M_RidgeGather.M_RidgeGather"));
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Path,
        FStreamableDelegate::CreateWeakLambda(this,[this,Path]()
        {
            GatherMaterial=Cast<UMaterialInterface>(Path.ResolveObject());
            if(GatherMaterial)SetMaterial(0,GatherMaterial);
        }));
}

void UHighlandRidgeGatherComponent::Present(const FTransform& Eye,const FVector& Tip,const FVector& BladeDirection,float SincePeak,float BeforePeak)
{
    constexpr float EndTime=HighlandRidgeThrust::AfterglowSeconds;
    if(!GatherMaterial||SincePeak<=-BeforePeak||SincePeak>=EndTime){Hide();return;}
    if(!IsVisible()&&SincePeak>HighlandRidgeThrust::HoldSeconds)return;
    // One per-emitter pattern, stored in its primitive data. Keep the seed
    // through the entire stroke; only a new visible burst chooses a new one.
    constexpr int32 PatternSeedSlot=0;
    if(!IsVisible()||!GetCustomPrimitiveData().Data.IsValidIndex(PatternSeedSlot))
        SetCustomPrimitiveDataFloat(PatternSeedSlot,float(FMath::RandRange(1,0xFFFFFF)));
    FRandomStream Pattern(int32(GetCustomPrimitiveData().Data[PatternSeedSlot]));
    const int32 StrandCount=Pattern.RandRange(25,30);
    const double Phase=Pattern.FRandRange(0.f,2.f*PI);
    // Follow the current rendered blade throughout gathering and afterglow.
    // Both callers supply the latest pose, so movement, turning and recovery
    // must move the convergence point as well as the camera-relative strands.
    SetWorldLocationAndRotation(Tip,FRotationMatrix::MakeFromX(BladeDirection).ToQuat());
    const FTransform TipFrame=GetComponentTransform();
    const FQuat ViewRotation=Eye.GetRotation();
    const FVector End=ViewRotation.UnrotateVector(Tip-Eye.GetLocation());
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    const float Age=SincePeak+BeforePeak;
    for(int32 I=0;I<StrandCount;++I)
    {
        // Stratified random angles fill the whole camera perimeter. Radius,
        // bend, start time and thickness vary, without changing between frames.
        const double Angle=Phase+2.*PI*(I+Pattern.FRandRange(.08f,.92f))/StrandCount;
        const double Radius=Pattern.FRandRange(72.f,125.f);
        const double Twist=Pattern.FRandRange(-.32f,.32f);
        const double Delay=BeforePeak*Pattern.FRandRange(0.f,.20f);
        const double Arrive=BeforePeak+Pattern.FRandRange(.018f,.105f);
        const double Trail=Pattern.FRandRange(.080f,.140f);
        const double Width=Pattern.FRandRange(.36f,.78f);
        const FVector Rear(-Pattern.FRandRange(65.f,145.f),Radius*FMath::Cos(Angle),Radius*.80*FMath::Sin(Angle));
        const FVector Shoulder(Pattern.FRandRange(24.f,58.f),Radius*FMath::Cos(Angle+Twist),Radius*.80*FMath::Sin(Angle+Twist));
        const FVector Guide=End*.72+FVector(0,Radius*.18*FMath::Cos(Angle-Twist),Radius*.18*FMath::Sin(Angle-Twist));
        const double Head=FMath::Clamp((Age-Delay)/FMath::Max(.012,Arrive-Delay),0.,1.);
        const double Tail=FMath::Clamp((Age-Delay-Trail)/FMath::Max(.012,Arrive-Delay+.035),0.,1.);
        if(Head-Tail<.003)continue;
        const auto Curve=[&](double U)
        {
            const double T=FMath::Lerp(Tail,Head,U),A=1.-T;
            const FVector P=Rear*(A*A*A)+Shoulder*(3*A*A*T)+Guide*(3*A*T*T)+End*(T*T*T);
            return TipFrame.InverseTransformPosition(Eye.GetLocation()+ViewRotation.RotateVector(P));
        };
        AddStroke(Mesh,14,Width*FMath::Min(1.,(Head-Tail)*10.),Curve);
    }
    const double Glow=FMath::SmoothStep(-.022f,.025f,SincePeak)*
        (1.f-FMath::SmoothStep(.07f,.24f,SincePeak));
    if(Glow>.005)
    {
        for(const FVector& Ray:{FVector(12,0,0),FVector(0,4.1,0),FVector(0,0,3.1)})
            AddStroke(Mesh,5,1.05*Glow,[&](double U){return Ray*((2.*U-1.)*Glow);});
    }
    const float Fade=1.f-FMath::SmoothStep(.18f,EndTime,SincePeak);
    if(SincePeak>0.f)
    {
        const double Drive=FMath::SmoothStep(0.f,.09f,SincePeak);
        const double Dissolve=1.-Fade;
        const double Front=8.+41.*Drive+10.*Dissolve;
        const double Back=-19.+43.*Dissolve;
        AddStroke(Mesh,10,1.65*Drive*(.45+.55*Fade),[&](double U)
            {return FVector(FMath::Lerp(Back,Front,U),0,0);});
        for(int32 I=0;I<3;++I)
        {
            // Three short filaments peel off the linear core. Their displaced tips
            // die first while the narrow center stays aligned to the live tip.
            AddStroke(Mesh,12,.87*Drive*(.32+.68*Fade),[&](double U)
            {
                const double Angle=I*(2.*PI/3.)+U*1.4;
                const double Spread=(2.8+2.4*Dissolve)*FMath::Sin(PI*U);
                return FVector(FMath::Lerp(Back-4.-I,Front-5.-2.*I,U),
                    Spread*FMath::Cos(Angle),Spread*FMath::Sin(Angle));
            });
        }
    }
    if(Mesh.TriangleCount()==0){Hide();return;}
    auto* MID=Cast<UMaterialInstanceDynamic>(GetMaterial(0));
    if(!MID)MID=CreateDynamicMaterialInstance(0,GatherMaterial);
    if(MID)MID->SetScalarParameterValue(TEXT("RidgeFade"),Fade);
    SetMesh(MoveTemp(Mesh));SetVisibility(true);
    LastPresented=GetWorld()->GetTimeSeconds();SetComponentTickEnabled(true);
}

void UHighlandRidgeGatherComponent::Hide()
{
    if(IsVisible())SetVisibility(false);
    SetComponentTickEnabled(false);
}

void UHighlandRidgeGatherComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    // A culled body can stop finalizing poses before sending an inactive one.
    if(GetWorld()->GetTimeSeconds()-LastPresented>.12)Hide();
}

void UHighlandRidgeGatherComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    if(MaterialLoad)MaterialLoad->CancelHandle();
    MaterialLoad.Reset();Super::EndPlay(Reason);
}
