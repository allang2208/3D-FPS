#include "ThermalTargetSubsystem.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Camera/CameraComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "Engine/StaticMesh.h"
#include "GameFramework/Character.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "TimerManager.h"

namespace ThermalTargets
{
const FSoftObjectPath Sphere(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
const FSoftObjectPath Body(TEXT("/Game/Weapons/ThermalScope20261006/Runtime/M_ThermalBody.M_ThermalBody"));
const FSoftObjectPath Fire(TEXT("/Game/Weapons/ThermalScope20261006/Runtime/M_ThermalFire.M_ThermalFire"));
}
void UThermalTargetSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    if(GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    Resources=UAssetManager::GetStreamableManager().RequestAsyncLoad(
        TArray<FSoftObjectPath>{ThermalTargets::Sphere,ThermalTargets::Body,ThermalTargets::Fire},
        FStreamableDelegate::CreateWeakLambda(this,[this]()
        {
            HeatMesh=Cast<UStaticMesh>(ThermalTargets::Sphere.ResolveObject());
            BodyMaterial=Cast<UMaterialInterface>(ThermalTargets::Body.ResolveObject());
            FireMaterial=Cast<UMaterialInterface>(ThermalTargets::Fire.ResolveObject());
        }));
}
void UThermalTargetSubsystem::Deinitialize()
{
    GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);
    for(auto& Target:Targets)Release(Target);
    Targets.Reset();Viewers.Reset();Resources.Reset();
    Super::Deinitialize();
}
void UThermalTargetSubsystem::RegisterMonster(UMonsterCombatComponent* Combat)
{
    if(!Combat||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    const auto* Character=Cast<ACharacter>(Combat->GetOwner());
    auto* Source=Character?Character->GetMesh():nullptr;
    if(!Source)return;
    for(const auto& T:Targets)if(T.Source==Source)return;
    auto& T=Targets.AddDefaulted_GetRef();T.Source=Source;T.Combat=Combat;
}
void UThermalTargetSubsystem::RegisterFire(UPrimitiveComponent* Source,FVector Extent,FVector Offset,float Duration)
{
    if(!Source||!Source->GetWorld()||Source->GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    auto* System=Source->GetWorld()->GetSubsystem<UThermalTargetSubsystem>();if(!System)return;
    // Pooled Niagara components can be reused by the same producer.
    const double Expires=Duration>0?Source->GetWorld()->GetTimeSeconds()+Duration:-1.;
    for(auto& T:System->Targets)if(T.Source==Source){System->Release(T);T.Extent=Extent;T.Offset=Offset;T.Expires=Expires;return;}
    auto& T=System->Targets.AddDefaulted_GetRef();T.Source=Source;T.Extent=Extent;T.Offset=Offset;T.Fire=true;
    T.Expires=Expires;
}
void UThermalTargetSubsystem::SetViewer(UCameraComponent* Camera,bool Active)
{
    if(!Camera)return;
    const bool HadViewers=!Viewers.IsEmpty();
    if(Active)Viewers.Add(Camera);else Viewers.Remove(Camera);
    if(HadViewers==!Viewers.IsEmpty())return;
    if(Viewers.IsEmpty())
    {
        GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);
        for(auto& T:Targets)Release(T);
    }
    else
    {
        Refresh();
        GetWorld()->GetTimerManager().SetTimer(RefreshTimer,this,&UThermalTargetSubsystem::Refresh,.2f,true);
    }
}
void UThermalTargetSubsystem::Release(FTarget& T)
{if(auto* P=T.Proxy.Get())P->DestroyComponent();T.Proxy.Reset();}
void UThermalTargetSubsystem::CreateProxy(FTarget& T)
{
    auto* Source=T.Source.Get();if(!Source||!BodyMaterial||!FireMaterial||!HeatMesh)return;
    UPrimitiveComponent* Proxy=nullptr;
    if(T.Fire)
    {
        auto* Mesh=NewObject<UStaticMeshComponent>(Source->GetOwner());
        Mesh->SetStaticMesh(HeatMesh);Mesh->SetMaterial(0,FireMaterial);Proxy=Mesh;
    }
    else if(auto* Body=Cast<USkeletalMeshComponent>(Source))
    {
        if(!Body->GetSkeletalMeshAsset())return;
        auto* Mesh=NewObject<USkeletalMeshComponent>(Source->GetOwner());
        Mesh->SetSkeletalMeshAsset(Body->GetSkeletalMeshAsset());
        Mesh->SetLeaderPoseComponent(Body);Mesh->bUseBoundsFromLeaderPoseComponent=true;
        for(int32 I=0;I<Mesh->GetNumMaterials();++I)Mesh->SetMaterial(I,BodyMaterial);
        Proxy=Mesh;
    }
    if(!Proxy)return;
    Proxy->SetupAttachment(Source);Proxy->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Proxy->SetGenerateOverlapEvents(false);Proxy->SetCanEverAffectNavigation(false);
    Proxy->SetCastShadow(false);Proxy->bReceivesDecals=false;
    Proxy->SetRenderInMainPass(false);Proxy->SetRenderInDepthPass(false);
    Proxy->SetRenderCustomDepth(true);Proxy->SetCustomDepthStencilValue(T.Fire?241:240);
    Proxy->SetCustomDepthStencilWriteMask(ERendererStencilMask::ERSM_Default);
    if(T.Fire)
    {
        // Physical heat envelope, independently sized from Niagara's spawn scale.
        Proxy->SetAbsolute(false,false,true);Proxy->SetRelativeLocation(T.Offset/Source->GetComponentScale().GetAbs().ComponentMax(FVector(.001f)));
        Proxy->SetWorldScale3D(T.Extent/50.f);
    }
    Source->GetOwner()->AddInstanceComponent(Proxy);Proxy->RegisterComponent();T.Proxy=Proxy;
}
void UThermalTargetSubsystem::Refresh()
{
    for(auto It=Viewers.CreateIterator();It;++It)if(!It->IsValid())It.RemoveCurrent();
    if(Viewers.IsEmpty()){GetWorld()->GetTimerManager().ClearTimer(RefreshTimer);for(auto& T:Targets)Release(T);return;}
    struct FCandidate {int32 Index;double Distance;};TArray<FCandidate> Candidates;
    for(int32 I=Targets.Num()-1;I>=0;--I)
    {
        auto& T=Targets[I];auto* Source=T.Source.Get();
        if(!Source||(!T.Fire&&!T.Combat.IsValid())||(T.Expires>0&&GetWorld()->GetTimeSeconds()>=T.Expires)){Release(T);Targets.RemoveAtSwap(I);continue;}
    }
    for(int32 I=0;I<Targets.Num();++I)
    {
        auto& T=Targets[I];auto* Source=T.Source.Get();
        const bool Alive=T.Fire?Source->IsActive()&&Source->IsVisible():!T.Combat->IsDead();
        if(!Alive||Source->GetOwner()->IsHidden()){Release(T);continue;}
        double Distance=DBL_MAX;
        for(const auto& Camera:Viewers)if(Camera.IsValid())
            Distance=FMath::Min(Distance,FVector::DistSquared(Camera->GetComponentLocation(),Source->GetComponentLocation()));
        if(Distance>FMath::Square(25000.)){Release(T);continue;}
        Candidates.Add({I,Distance});
    }
    Candidates.Sort([](const FCandidate& A,const FCandidate& B){return A.Distance<B.Distance;});
    int32 Bodies=0,Fires=0;
    for(const auto& C:Candidates)
    {
        auto& T=Targets[C.Index];bool Selected=T.Fire?Fires++<32:Bodies++<96;
        if(Selected&&T.Fire)
        {
            // A broad heat envelope must not leak around a wall that separates
            // its source from the observer. Pixel depth still clips its contour.
            Selected=false;
            for(const auto& Camera:Viewers)if(Camera.IsValid())
            {
                FCollisionQueryParams Query(SCENE_QUERY_STAT(ThermalFireOcclusion),false,Camera->GetOwner());
                Query.AddIgnoredActor(T.Source->GetOwner());FHitResult Hit;
                const FVector Center=T.Source->GetComponentLocation()+T.Source->GetComponentQuat().RotateVector(T.Offset);
                if(!GetWorld()->LineTraceSingleByChannel(Hit,Camera->GetComponentLocation(),Center,ECC_Visibility,Query)){Selected=true;break;}
            }
        }
        if(!Selected)Release(T);else if(!T.Proxy.IsValid())CreateProxy(T);
    }
}
