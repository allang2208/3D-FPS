#include "PlazaInstanceTools.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "StaticMeshComponentLODInfo.h"
#include "Engine/World.h"
#include "PhysicsEngine/BodyInstance.h"
#include "UObject/UnrealType.h"

namespace
{
bool IsConfig(const FProperty* Property)
{
    // Copy only editable settings. Ownership, attachment links, live render/physics state and
    // relative transforms belong to the new actor; each source transform becomes an instance.
    const FName Name=Property->GetFName();
    return Property->HasAnyPropertyFlags(CPF_Edit) && !Property->HasAnyPropertyFlags(CPF_Transient|CPF_InstancedReference)
        && Name!=TEXT("RelativeLocation") && Name!=TEXT("RelativeRotation") && Name!=TEXT("RelativeScale3D")
        && Name!=TEXT("BodyInstance") && Name!=TEXT("ComponentTags") && Name!=TEXT("PrimaryComponentTick")
        && Name!=TEXT("StaticMesh");
}
}

bool UPlazaInstanceTools::BuildNaniteData(UStaticMesh* Mesh)
{
#if WITH_EDITOR
    if(!IsValid(Mesh)||!Mesh->GetNaniteSettings().bEnabled)return false;
    TArray<FText> Errors;
    Mesh->Build(true,&Errors); // Supplying errors makes this production build synchronous.
    for(const FText& Error:Errors)UE_LOG(LogTemp,Error,TEXT("Plaza Nanite build: %s"),*Error.ToString());
    return Errors.IsEmpty()&&Mesh->HasValidNaniteData();
#else
    return false;
#endif
}

FString UPlazaInstanceTools::ClusterPolicy(AStaticMeshActor* Source)
{
#if WITH_EDITOR
    if(!IsValid(Source)||Source->GetClass()!=AStaticMeshActor::StaticClass()||!Source->GetWorld()
        ||Source->GetWorld()->WorldType!=EWorldType::Editor||!Source->ActorHasTag(TEXT("ColdSteel.MainPlaza.Generated"))
        ||Source->GetAttachParentActor()||Source->IsHidden()||!Source->GetInstanceComponents().IsEmpty())return {};
    TArray<AActor*> Attached;Source->GetAttachedActors(Attached);if(!Attached.IsEmpty())return {};
    auto* Mesh=Source->GetStaticMeshComponent();
    if(!Mesh||!Mesh->GetStaticMesh()||!Mesh->GetStaticMesh()->HasValidNaniteData()||Mesh->GetMobility()!=EComponentMobility::Static
        ||Mesh->IsSimulatingPhysics()||!Mesh->IsVisible()||Mesh->bHiddenInGame||Mesh->GetGenerateOverlapEvents()||(Mesh->PrimaryComponentTick.bCanEverTick&&Mesh->IsComponentTickEnabled()))return {};
    for(const auto& LOD:Mesh->LODData)if(LOD.OverrideVertexColors)return {};
    FString Key=Mesh->GetStaticMesh()->GetPathName();
    for(TFieldIterator<FProperty> It(UStaticMeshComponent::StaticClass());It;++It)
        if(IsConfig(*It))
        {
            FString Value;It->ExportText_InContainer(0,Value,Mesh,nullptr,Mesh,PPF_None);
            Key+=TEXT("|")+It->GetName()+TEXT("=")+Value;
        }
    // Compare serialized physics configuration, excluding its live handles.
    if(const auto* Body=FindFProperty<FProperty>(UPrimitiveComponent::StaticClass(),TEXT("BodyInstance")))
    {
        FString Value;Body->ExportText_InContainer(0,Value,Mesh,nullptr,Mesh,PPF_None);Key+=TEXT("|body=")+Value;
    }
    Key+=FString::Printf(TEXT("|nav=%d"),Mesh->CanEverAffectNavigation());
    for(FName Tag:Source->Tags)Key+=TEXT("|actorTag=")+Tag.ToString();
    for(FName Tag:Mesh->ComponentTags)Key+=TEXT("|componentTag=")+Tag.ToString();
    return Key;
#else
    return {};
#endif
}

AActor* UPlazaInstanceTools::CreatePlazaCluster(const TArray<AStaticMeshActor*>& Sources,const FString& Label)
{
#if WITH_EDITOR
    if(Sources.Num()<2)return nullptr;
    const FString Policy=ClusterPolicy(Sources[0]);if(Policy.IsEmpty())return nullptr;
    auto* World=Sources[0]->GetWorld();
    TArray<FTransform> Instances;
    for(auto* Source:Sources)
    {
        if(!IsValid(Source)||Source->GetWorld()!=World||ClusterPolicy(Source)!=Policy)return nullptr;
        Instances.Add(Source->GetStaticMeshComponent()->GetComponentTransform());
    }
    auto* Template=Sources[0]->GetStaticMeshComponent();
    FActorSpawnParameters Spawn;Spawn.ObjectFlags=RF_Transactional;Spawn.OverrideLevel=Sources[0]->GetLevel();
    auto* Result=World->SpawnActor<AActor>(AActor::StaticClass(),Sources[0]->GetActorLocation(),FRotator::ZeroRotator,Spawn);
    if(!Result)return nullptr;
    Result->SetActorLabel(Label);Result->Tags=Sources[0]->Tags;
    Result->Tags.AddUnique(TEXT("ColdSteel.MainPlaza.Instanced20260923"));
    auto* Mesh=NewObject<UInstancedStaticMeshComponent>(Result,TEXT("PlazaInstances"),RF_Transactional);
    Result->SetRootComponent(Mesh);Result->AddInstanceComponent(Mesh);
    for(TFieldIterator<FProperty> It(UStaticMeshComponent::StaticClass());It;++It)
        if(IsConfig(*It))It->CopyCompleteValue_InContainer(Mesh,Template);
    Mesh->SetStaticMesh(Template->GetStaticMesh());
    // CopyBodyInstancePropertiesFrom only accepts uninitialized BodySetup defaults.
    // Level components already own physics state: copy their editable configuration only,
    // leaving owners, actor handles and scene state on the new body untouched.
    for(TFieldIterator<FProperty> It(FBodyInstance::StaticStruct());It;++It)
        if(IsConfig(*It))It->CopyCompleteValue_InContainer(&Mesh->BodyInstance,&Template->BodyInstance);
    Mesh->BodyInstance.SetMaskFilter(Template->BodyInstance.GetMaskFilter());
    Mesh->ComponentTags=Template->ComponentTags;
    Mesh->SetCanEverAffectNavigation(Template->CanEverAffectNavigation());
    Mesh->SetWorldLocation(Sources[0]->GetActorLocation());
    Mesh->RegisterComponent();
    Mesh->AddInstances(Instances,false,true,true);
    Result->MarkPackageDirty();
    return Result;
#else
    return nullptr;
#endif
}
