#include "GhostScytheMist.h"
#include "Components/StaticMeshComponent.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "GameFramework/Actor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"

namespace GhostScytheMist
{
const TCHAR* const MaterialPath=TEXT("/Game/Weapons/TacticalHatchet20261101/GhostScythe20261104/HeldMistR13/M_GhostScythe_HeldMist.M_GhostScythe_HeldMist");
const TCHAR* const PlanePath=TEXT("/Engine/BasicShapes/Plane.Plane");
const FName HolderTag(TEXT("GhostScytheMistHolder"));
static const FName EffectTag(TEXT("GhostScytheBloodMist"));
static const FName HeadName(TEXT("SM_TacticalHatchet_Head_GhostScythe_V6"));

UPrimitiveComponent* Find(const UPrimitiveComponent* Blade)
{
    if(!Blade||!Blade->ComponentHasTag(HolderTag))return nullptr;
    for(const auto& Child:Blade->GetAttachChildren())
        if(Child&&Child->ComponentHasTag(EffectTag))return Cast<UPrimitiveComponent>(Child.Get());
    return nullptr;
}
void MatchVisibility(const UPrimitiveComponent* Blade)
{
    if(auto* Fx=Find(Blade))
    {
        Fx->SetOnlyOwnerSee(Blade->bOnlyOwnerSee);
        Fx->SetOwnerNoSee(Blade->bOwnerNoSee);
        if(Fx->FirstPersonPrimitiveType!=Blade->FirstPersonPrimitiveType)
            Fx->SetFirstPersonPrimitiveType(Blade->FirstPersonPrimitiveType);
        Fx->SetVisibility(Blade->IsVisible());
        Fx->SetHiddenInGame(Blade->bHiddenInGame);
    }
}
void Clear(UStaticMeshComponent* Blade)
{
    if(!Blade||!Blade->ComponentHasTag(HolderTag))return;
    if(auto* Fx=Find(Blade))
    {
        if(auto* Owner=Fx->GetOwner())Owner->RemoveInstanceComponent(Fx);
        Fx->DestroyComponent();
    }
    Blade->ComponentTags.Remove(HolderTag);
}
void Refresh(UStaticMeshComponent* Blade)
{
    Refresh(Blade,Blade&&Blade->GetStaticMesh()&&Blade->GetStaticMesh()->GetFName()==HeadName);
}
void Refresh(UStaticMeshComponent* Blade,bool bEquipped)
{
    if(!Blade)return;
    if(!bEquipped){Clear(Blade);return;}
    auto* World=Blade->GetWorld();
    if(!World||!Blade->IsRegistered()||World->GetNetMode()==NM_DedicatedServer)return;
    if(Find(Blade)){MatchVisibility(Blade);return;}
    // The modular weapon preloads this with its mesh. The preview and replicated
    // world parts may enter here directly, even without a preceding preload.
    auto* Material=LoadObject<UMaterialInterface>(nullptr,MaterialPath);
    auto* Plane=LoadObject<UStaticMesh>(nullptr,PlanePath);
    if(!Material||!Plane)return;
    auto* Fx=NewObject<UInstancedStaticMeshComponent>(Blade,NAME_None,RF_Transient);
    if(auto* Owner=Blade->GetOwner())Owner->AddInstanceComponent(Fx);
    Fx->SetMobility(EComponentMobility::Movable);
    Fx->SetupAttachment(Blade);
    Fx->ComponentTags.Add(EffectTag);
    Fx->SetStaticMesh(Plane);Fx->SetMaterial(0,Material);Fx->NumCustomDataFloats=2;
    Fx->SetCastShadow(false);
    Fx->bReceivesDecals=false;Fx->bAffectDistanceFieldLighting=false;
    Fx->SetVisibleInRayTracing(false);
    Fx->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    Fx->SetGenerateOverlapEvents(false);
    Fx->SetCanEverAffectNavigation(false);
    Fx->SetCullDistances(0,2600);Fx->SetBoundsScale(4.f);
    // The fitted edge is in grip-local centimetres. The material expands these small planes into
    // camera-facing wisps and lifts them along world Z; the signed offhand transform affects only the anchor.
    const FVector Edge[]={FVector(5.6,0,21.7),FVector(10.3,0,21.4),FVector(14.25,0,19.55),FVector(18.15,0,14.8)};
    constexpr int32 WispCount=16;
    for(int32 I=0;I<WispCount;++I)
    {
        const float Seed=FMath::Frac(.17f+I*.61803399f);
        const float Station=(I+.5f)*3.f/WispCount;const int32 N=int32(Station);
        FVector Anchor=FMath::Lerp(Edge[N],Edge[N+1],Station-N);
        Anchor.Y=(I%2?1.f:-1.f)*(.5f+.45f*Seed);
        const int32 Index=Fx->AddInstance(FTransform(FQuat::Identity,Anchor,FVector(.001f)));
        Fx->SetCustomDataValue(Index,0,Seed,false);
        Fx->SetCustomDataValue(Index,1,FMath::Frac(.13f+I*.41421356f),false);
    }
    Fx->RegisterComponentWithWorld(World);
    Blade->ComponentTags.AddUnique(HolderTag);
    MatchVisibility(Blade);
}
}
