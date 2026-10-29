#include "FPSBodyKukriRifts.h"
#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyKukriMotion.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/Kukri/KukriRhythm.h"
#include "Components/StaticMeshComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

namespace BodyKukriRift
{
constexpr int32 Stations=32;
UE::Geometry::FDynamicMesh3 Ribbon()
{
    using namespace UE::Geometry;
    FDynamicMesh3 M;M.EnableAttributes();
    auto* UV=M.Attributes()->PrimaryUV();auto* N=M.Attributes()->PrimaryNormals();
    for(int32 I=0;I<Stations;++I)for(int32 E=0;E<2;++E)
    {
        M.AppendVertex(FVector3d(0,0,0));
        const float U=float(I)/(Stations-1);
        UV->AppendElement(FVector2f(U<.6f?.045f*U/.6f:.045f+.955f*(U-.6f)/.4f,float(E)));
        N->AppendElement(FVector3f(0,0,1));
    }
    for(int32 I=0;I<Stations-1;++I)for(auto T:{FIndex3i(I*2,I*2+2,I*2+1),FIndex3i(I*2+1,I*2+2,I*2+3)})
    {const int32 Id=M.AppendTriangle(T);UV->SetTriangle(Id,T);N->SetTriangle(Id,T);}
    return M;
}
}

void FFPSBodyKukriRifts::Sample(AActor* Owner,int32 Hand,const FString& Weapon,FName Action,float Progress,
    bool Whirlwind,const FTransform& Knife,double Now)
{
    if(!Owner||Owner->GetNetMode()==NM_DedicatedServer||Hand<0||Hand>1)return;
    auto& T=Trails[Hand];
    if(T.Weapon!=Weapon||T.Action!=Action||Progress+.08f<T.Progress)
    {T.Points.Reset();T.Weapon=Weapon;T.Action=Action;T.Progress=-1.f;if(T.Mesh.IsValid())T.Mesh->SetVisibility(false);}
    if(Progress<=T.Progress+UE_SMALL_NUMBER)return; // A replicated hit-stop adds no phantom motion.
    T.Progress=Progress;T.LastSample=Now;T.Whirlwind=Whirlwind;
    FPoint P;P.Inner=Knife.TransformPosition(KukriRhythm::BladeTip*.40f);
    P.Outer=Knife.TransformPosition(KukriRhythm::BladeTip*1.35f);P.At=Now;
    if(!T.Points.IsEmpty())
    {
        const auto& Last=T.Points.Last();
        if(FVector::DistSquared(Last.Outer,P.Outer)>FMath::Square(180.f))T.Points.Reset();
        else
        {
            const FVector A=(Last.Outer-Owner->GetActorLocation()).GetSafeNormal2D();
            const FVector B=(P.Outer-Owner->GetActorLocation()).GetSafeNormal2D();
            P.Travel=Last.Travel+FMath::RadiansToDegrees(FMath::Acos(FMath::Clamp(FVector::DotProduct(A,B),-1.,1.)));
        }
    }
    T.Points.Add(P);
    while(T.Points.Num()>BodyKukriRift::Stations||
        (T.Points.Num()>1&&(Now-T.Points[0].At>(Whirlwind?.12:.20)||(Whirlwind&&P.Travel-T.Points[0].Travel>120.f))))
        T.Points.RemoveAt(0,1,EAllowShrinking::No);
    if(!T.Mesh.IsValid())
    {
        auto* Base=Cast<UMaterialInterface>(FSoftObjectPath(KukriRhythm::RiftMaterial).ResolveObject());
        if(!Base)return;
        auto* Mesh=NewObject<UDynamicMeshComponent>(Owner);Owner->AddInstanceComponent(Mesh);
        Mesh->ComponentTags.Add(Hand?TEXT("KukriObserverRiftLeft"):TEXT("KukriObserverRiftRight"));
        Mesh->SetMobility(EComponentMobility::Movable);Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetGenerateOverlapEvents(false);Mesh->SetCanEverAffectNavigation(false);Mesh->SetCastShadow(false);
        Mesh->SetVisibility(false);
        Mesh->SetReceivesDecals(false);Mesh->bVisibleInRayTracing=false;Mesh->bAffectDistanceFieldLighting=false;
        Mesh->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);Mesh->RegisterComponent();
        Mesh->SetMesh(BodyKukriRift::Ribbon());T.Mesh=Mesh;
        auto* MID=UMaterialInstanceDynamic::Create(Base,Mesh);Mesh->SetMaterial(0,MID);T.Material=MID;
        MID->SetScalarParameterValue(TEXT("SweepProgress"),1.06f);
    }
    if(T.Points.Num()<2){T.Mesh->SetVisibility(false);return;}
    const FVector Origin=Owner->GetActorLocation();T.Mesh->SetWorldTransform(FTransform(Origin));
    T.Mesh->GetDynamicMesh()->EditMesh([&](UE::Geometry::FDynamicMesh3& M)
    {
        for(int32 I=0;I<BodyKukriRift::Stations;++I)
        {
            const float X=float(I)*(T.Points.Num()-1)/(BodyKukriRift::Stations-1);
            const int32 A=FMath::FloorToInt(X),B=FMath::Min(A+1,T.Points.Num()-1);
            M.SetVertex(I*2,FVector3d(FMath::Lerp(T.Points[A].Inner,T.Points[B].Inner,X-A)-Origin));
            M.SetVertex(I*2+1,FVector3d(FMath::Lerp(T.Points[A].Outer,T.Points[B].Outer,X-A)-Origin));
        }
    },EDynamicMeshChangeType::DeformationEdit,EDynamicMeshAttributeChangeFlags::VertexPositions);
    T.Material->SetScalarParameterValue(TEXT("RiftStrength"),Whirlwind?.10f:.095f);
    T.Material->SetScalarParameterValue(TEXT("RiftFade"),1.f);T.Mesh->SetVisibility(true);
}
void FFPSBodyKukriRifts::Advance(double Now)
{
    for(auto& T:Trails)
    {
        const float Fade=FMath::Clamp(float(Now-T.LastSample)/(T.Whirlwind?.12f:.20f),0.f,1.f);
        if(T.Material.IsValid())T.Material->SetScalarParameterValue(TEXT("RiftFade"),1.f-FMath::SmoothStep(0.f,1.f,Fade));
        if(Fade>=1.f){T.Points.Reset();if(T.Mesh.IsValid())T.Mesh->SetVisibility(false);}
    }
}
void FFPSBodyKukriRifts::SampleWindow(AActor* Owner,int32 Hand,const FString& Weapon,FName Action,float Progress,
    float Start,float End,bool Whirlwind,const FTransform& Knife,double Now)
{
    if(Hand<0||Hand>1)return;
    auto& T=Trails[Hand];
    if(T.Weapon!=Weapon||T.Action!=Action||Progress+.08f<T.ProbeProgress)
    {
        T.Points.Reset();T.Weapon=Weapon;T.Action=Action;T.Progress=T.ProbeProgress=-1.f;
        if(T.Mesh.IsValid())T.Mesh->SetVisibility(false);
        // Heavy release can already be beyond contact in its first packet.
        // Its last finalized charge pose supplies the real start of the cut.
        // Do not bridge an equipment change or a stale/teleported pose.
        if(T.PreviousWeapon==Weapon&&T.PreviousAt>=0.&&Now>=T.PreviousAt&&Now-T.PreviousAt<=.25&&
            FVector::DistSquared(T.PreviousKnife.GetLocation(),Knife.GetLocation())<FMath::Square(180.f))
        {T.ProbeKnife=T.PreviousKnife;T.ProbeProgress=0.f;}
    }
    // A fast cut may cross its entire reveal window between two finalized
    // observer poses. Clip that real blade segment to the window instead of
    // requiring two packets to happen to land inside it.
    if(T.ProbeProgress>=0.f&&Progress>T.ProbeProgress+UE_SMALL_NUMBER&&Progress>=Start&&T.ProbeProgress<=End)
    {
        const float A=FMath::Max(Start,T.ProbeProgress),B=FMath::Min(End,Progress);
        if(B>A+UE_SMALL_NUMBER)
        {
            for(const float P:{A,B})
            {
                FTransform Pose;Pose.Blend(T.ProbeKnife,Knife,(P-T.ProbeProgress)/(Progress-T.ProbeProgress));
                Sample(Owner,Hand,Weapon,Action,P,Whirlwind,Pose,Now);
            }
        }
    }
    if(Progress>T.ProbeProgress){T.ProbeProgress=Progress;T.ProbeKnife=Knife;}
    static const bool Trace=FParse::Param(FCommandLine::Get(),TEXT("KukriRiftTrace"));
    if(Trace&&Hand==0&&Progress<.55f)
        UE_LOG(LogTemp,Display,TEXT("KUKRI_RIFT_TRACE %s p=%.3f start=%.3f end=%.3f probe=%.3f points=%d visible=%d material=%d"),
            *Action.ToString(),Progress,Start,End,T.ProbeProgress,T.Points.Num(),T.Mesh.IsValid()&&T.Mesh->IsVisible(),T.Material.IsValid());
}
void FFPSBodyKukriRifts::RememberPose(int32 Hand,const FString& Weapon,const FTransform& Knife,double Now)
{
    if(Hand<0||Hand>1)return;
    auto& T=Trails[Hand];T.PreviousKnife=Knife;T.PreviousWeapon=Weapon;T.PreviousAt=Now;
}
void FFPSBodyKukriRifts::Clear(AActor* Owner)
{
    for(auto& T:Trails){if(T.Mesh.IsValid()){if(Owner)Owner->RemoveInstanceComponent(T.Mesh.Get());T.Mesh->DestroyComponent();}T=FTrail();}
    if(MaterialLoad){MaterialLoad->CancelHandle();MaterialLoad.Reset();}
}
void UFPSPlayerBodyComponent::UpdateObserverKukriRifts()
{
    if(!Character.IsValid()||Character->IsLocallyControlled()||GetNetMode()==NM_DedicatedServer||!BodyAnimation)return;
    const auto& S=BodyAnimation->BodyState;
    bool CarriesKnife=S.Family==TEXT("Kukri");
    for(const auto& B:MotionBindings)CarriesKnife|=B.Definition.PoseFamily==TEXT("OffhandKukri")&&B.Definition.ItemInstance==S.OffhandInstance;
    if(!CarriesKnife)
    {if(ObserverKukriRifts){ObserverKukriRifts->Clear(GetOwner());ObserverKukriRifts.Reset();}return;}
    if(!ObserverKukriRifts)ObserverKukriRifts=MakeShared<FFPSBodyKukriRifts>();
    auto& R=*ObserverKukriRifts;
    if(!R.MaterialLoad)R.MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(FSoftObjectPath(KukriRhythm::RiftMaterial));
    for(int32 Hand=0;Hand<2;++Hand)
    {
        auto& T=R.Trails[Hand];
        if(!T.Weapon.IsEmpty()&&T.Weapon!=(Hand?S.OffhandInstance:S.WeaponInstance))
        {T.Points.Reset();T.Weapon.Reset();T.Progress=T.ProbeProgress=-1.f;T.LastSample=-1.;if(T.Mesh.IsValid())T.Mesh->SetVisibility(false);}
    }
    if(S.Action==EFPSBodyAction::Dead||FPSBodyPoses::Traversing(S.Motion))
    {R.Clear(GetOwner());ObserverKukriRifts.Reset();return;}
    const float P=FPSBodyPoses::Progress(S,BodyAnimation->Clock);
    const bool Spin=S.Action==EFPSBodyAction::Whirlwind;
    const bool Attack=S.Action==EFPSBodyAction::Strike||S.Action==EFPSBodyAction::Thrust||S.Action==EFPSBodyAction::HeavyStrike||Spin;
    for(const auto& B:MotionBindings)
    {
        const auto& W=B.Definition;const int32 Hand=W.AttachHand;
        if(Hand<0||Hand>1||(W.PoseFamily!=TEXT("Kukri")&&W.PoseFamily!=TEXT("KukriDual")&&W.PoseFamily!=TEXT("OffhandKukri")))continue;
        if(W.ItemInstance!=(Hand?S.OffhandInstance:S.WeaponInstance))continue;
        if(Hand==1&&S.Family==TEXT("Kukri")&&S.ActionVariant==TEXT("Uppercut"))continue;
        float Start=FMath::Max(0.f,S.ContactFraction-(Spin?0.f:.08f)),End=S.ReleaseFraction;
        if(S.Action==EFPSBodyAction::Strike&&(S.ActionVariant==TEXT("DualAttack")||S.ActionVariant==TEXT("DualAttack2")))
        {
            // The second blade swings later. Derive the author length from the
            // replicated strike marker; don't render the left wind-up as a cut.
            const int32 Stage=S.ActionVariant==TEXT("DualAttack2")?1:0;
            const float Length=KukriRhythm::Strikes[Stage].At/FMath::Max(.001f,S.ContactFraction);
            const float Offset=Hand?KukriRhythm::DualSweepOffset(Stage):0.f;
            Start=(KukriRhythm::Rifts[Stage].Start+Offset)/Length;End=(KukriRhythm::Rifts[Stage].End+Offset)/Length;
        }
        auto* Blade=B.Static.Get();if(!Blade||!Blade->IsVisible()||Blade->bHiddenInGame||IsWorldWeaponStowed(Blade))continue;
        auto* Parent=Blade->GetAttachParent();if(!Parent)continue;
        const FTransform Knife=Blade->GetRelativeTransform()*Parent->GetSocketTransform(Blade->GetAttachSocketName(),RTS_World);
        const double Now=GetWorld()->GetTimeSeconds();
        if(Attack)R.SampleWindow(GetOwner(),Hand,W.ItemInstance,S.ActionVariant,P,Start,End,Spin,Knife,Now);
        R.RememberPose(Hand,W.ItemInstance,Knife,Now);
    }
}
