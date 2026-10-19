#include "BeiweiSwordTrailComponent.h"
#include "Components/DynamicMeshComponent.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Actor.h"

namespace {constexpr double BeiweiTrailLifetime=.24;constexpr int32 BeiweiTrailSamples=48;}
UBeiweiSwordTrailComponent::UBeiweiSwordTrailComponent()
{
    PrimaryComponentTick.bCanEverTick=true;PrimaryComponentTick.bStartWithTickEnabled=false;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UBeiweiSwordTrailComponent::BeginPlay()
{
    Super::BeginPlay();Samples.Reserve(BeiweiTrailSamples);
    const FSoftObjectPath Path(TEXT("/Game/Weapons/Zhanmadao20261018/BeiweiRuneV1/Materials/M_BeiweiSwordTrail.M_BeiweiSwordTrail"));
    const FSoftObjectPath CrimsonPath(TEXT("/Game/Weapons/Zhanmadao20261018/ChixiaoLegendaryV1/Materials/M_ChixiaoSwordTrail.M_ChixiaoSwordTrail"));
    const FSoftObjectPath CyanPath(TEXT("/Game/Weapons/Zhanmadao20261018/ZhufengCyanTrailV1/Materials/M_ZhufengSwordTrail.M_ZhufengSwordTrail"));
    TWeakObjectPtr<UBeiweiSwordTrailComponent> Weak(this);
    MaterialLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(TArray<FSoftObjectPath>{Path,CrimsonPath,CyanPath},FStreamableDelegate::CreateLambda([Weak,Path,CrimsonPath,CyanPath]()
    {
        if(auto* Self=Weak.Get())
        {
            Self->Material=Cast<UMaterialInterface>(Path.ResolveObject());
            Self->CrimsonMaterial=Cast<UMaterialInterface>(CrimsonPath.ResolveObject());
            Self->CyanMaterial=Cast<UMaterialInterface>(CyanPath.ResolveObject());
        }
    }));
}
void UBeiweiSwordTrailComponent::SetView(bool OwnerOnly,bool HideFromOwner)
{
    bOwnerOnly=OwnerOnly;bHideOwner=HideFromOwner;
    if(Ribbon){Ribbon->SetOnlyOwnerSee(OwnerOnly);Ribbon->SetOwnerNoSee(HideFromOwner);}
}
UMaterialInterface* UBeiweiSwordTrailComponent::TrailMaterial() const
{
    if(ActivePalette==ESwordTrailPalette::Cyan)return CyanMaterial.Get();
    return ActivePalette==ESwordTrailPalette::Crimson?CrimsonMaterial.Get():Material.Get();
}
void UBeiweiSwordTrailComponent::Feed(const FVector& Base,const FVector& Tip,bool Emitting,ESwordTrailPalette Palette)
{
    if(!Emitting){bContinuous=false;return;}
    if(GetNetMode()==NM_DedicatedServer||Base.Equals(Tip,1.f))return;
    // Change palette only when a new strike emits; let inactive tails fade normally.
    if(ActivePalette!=Palette)
    {
        Clear();ActivePalette=Palette;
        if(Ribbon)Ribbon->SetMaterial(0,TrailMaterial());
    }
    const double Now=GetWorld()->GetTimeSeconds();
    if(!Samples.IsEmpty()&&(Now-Samples.Last().Time>BeiweiTrailLifetime||FVector::DistSquared(Base,Samples.Last().Base)>250000.))Clear();
    if(Samples.IsEmpty())Origin=Base;
    if(bContinuous&&!Samples.IsEmpty()&&Now-Samples.Last().Time<.001)return;
    if(Samples.Num()>=BeiweiTrailSamples)Samples.RemoveAt(0,1,EAllowShrinking::No);
    // Keep the root clear of hands; the blade tip remains at its real position.
    Samples.Add({FMath::Lerp(Base,Tip,.12f),Tip,Now,!bContinuous});
    bContinuous=true;SetComponentTickEnabled(true);
}
void UBeiweiSwordTrailComponent::Clear()
{
    Samples.Reset();bContinuous=false;SetComponentTickEnabled(false);
    if(Ribbon)Ribbon->SetVisibility(false);
}
void UBeiweiSwordTrailComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    const double Now=GetWorld()->GetTimeSeconds();
    while(!Samples.IsEmpty()&&Now-Samples[0].Time>=BeiweiTrailLifetime)Samples.RemoveAt(0,1,EAllowShrinking::No);
    if(Samples.IsEmpty()){Clear();return;}
    auto* CurrentMaterial=TrailMaterial();
    if(!CurrentMaterial||Samples.Num()<2){if(Ribbon)Ribbon->SetVisibility(false);return;}
    if(!Ribbon)
    {
        Ribbon=NewObject<UDynamicMeshComponent>(GetOwner());GetOwner()->AddInstanceComponent(Ribbon);
        Ribbon->SetMobility(EComponentMobility::Movable);
        Ribbon->SetCollisionEnabled(ECollisionEnabled::NoCollision);Ribbon->SetGenerateOverlapEvents(false);
        Ribbon->SetCanEverAffectNavigation(false);Ribbon->SetCastShadow(false);Ribbon->SetReceivesDecals(false);
        Ribbon->bVisibleInRayTracing=false;Ribbon->bAffectDistanceFieldLighting=false;
        Ribbon->SetOnlyOwnerSee(bOwnerOnly);Ribbon->SetOwnerNoSee(bHideOwner);
        Ribbon->SetTangentsType(EDynamicMeshComponentTangentsMode::NoTangents);
        Ribbon->RegisterComponent();
    }
    // A palette may finish streaming after an existing ribbon changes style.
    if(Ribbon->GetMaterial(0)!=CurrentMaterial)Ribbon->SetMaterial(0,CurrentMaterial);
    using namespace UE::Geometry;
    FDynamicMesh3 Mesh;Mesh.EnableAttributes();
    auto* UV=Mesh.Attributes()->PrimaryUV();auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for(const auto& S:Samples)
    {
        const float Age=FMath::Clamp(float((Now-S.Time)/BeiweiTrailLifetime),0.f,1.f);
        for(int32 Edge=0;Edge<2;++Edge)
        {
            Mesh.AppendVertex((Edge?S.Tip:S.Base)-Origin);
            UV->AppendElement(FVector2f(Age,float(Edge)));Normals->AppendElement(FVector3f(0,0,1));
        }
    }
    for(int32 I=1;I<Samples.Num();++I)
    {
        if(Samples[I].Start)continue;
        const int32 A=(I-1)*2,B=I*2;
        for(const FIndex3i& T:{FIndex3i(A,B,A+1),FIndex3i(A+1,B,B+1)})
        {const int32 Id=Mesh.AppendTriangle(T);UV->SetTriangle(Id,T);Normals->SetTriangle(Id,T);}
    }
    Ribbon->SetWorldLocation(Origin);Ribbon->SetVisibility(Mesh.TriangleCount()>0);Ribbon->SetMesh(MoveTemp(Mesh));
}
void UBeiweiSwordTrailComponent::EndPlay(EEndPlayReason::Type Reason)
{
    if(MaterialLoad)MaterialLoad->CancelHandle();MaterialLoad.Reset();Clear();
    if(Ribbon){GetOwner()->RemoveInstanceComponent(Ribbon);Ribbon->DestroyComponent();Ribbon=nullptr;}
    Super::EndPlay(Reason);
}
