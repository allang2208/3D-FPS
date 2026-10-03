#include "FPSPlayerBodyComponent.h"
#include "FPSPlayerHeadAnimInstance.h"
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/LODSyncComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StreamableManager.h"
#include "GroomComponent.h"
#include "GroomAsset.h"
#include "GroomBindingAsset.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"

namespace FPSBodyAppearance
{
TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonObject>& Parent,const FString& Key)
{const TSharedPtr<FJsonObject>* Value=nullptr;return Parent&&Parent->TryGetObjectField(Key,Value)?*Value:nullptr;}
FString Text(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{FString Value;if(Parent)Parent->TryGetStringField(Key,Value);return Value;}
void Grooms(const TSharedPtr<FJsonObject>& Settings,TArray<TSharedPtr<FJsonObject>>& Out)
{
    const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if(Settings&&Settings->TryGetArrayField(TEXT("grooms"),Values))
        for(const auto& Value:*Values)if(Value->Type==EJson::Object)Out.Add(Value->AsObject());
}
}

FFPSBodyAppearance UFPSPlayerBodyComponent::ResolveAppearance(FFPSBodyAppearance Value) const
{
    using namespace FPSBodyAppearance;
    const auto Heads=Object(Configuration,TEXT("heads"));
    if(!Object(Heads,Value.HeadId.ToString()))Value.HeadId=FName(*Text(Configuration,TEXT("default_head")));
    const auto Head=Object(Heads,Value.HeadId.ToString());
    const auto Hairs=Object(Head,TEXT("hair_styles"));
    if(!Object(Hairs,Value.HairId.ToString()))Value.HairId=FName(*Text(Head,TEXT("default_hair")));
    return Value;
}
bool UFPSPlayerBodyComponent::SetHeadAndHair(FName HeadId,FName HairId)
{
    if(!Character.IsValid()||!Character->IsLocallyControlled()||!Character->GetGameInstance())return false;
    FFPSBodyAppearance Requested;Requested.HeadId=HeadId;Requested.HairId=HairId;
    if(!(ResolveAppearance(Requested)==Requested))return false;
    auto* Profile=Character->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||!Profile->SetPlayerAppearance(HeadId,HairId))return false;
    RefreshAppearance(Profile);return true;
}
void UFPSPlayerBodyComponent::RefreshAppearance(UColdSteelStatusModel* Profile)
{
    FFPSBodyAppearance Next;
    if(Profile){Next.HeadId=Profile->PlayerHeadId();Next.HairId=Profile->PlayerHairId();}
    Next=ResolveAppearance(Next);
    if(GetOwner()->HasAuthority()&&!(Next==ReplicatedAppearance))
    {ReplicatedAppearance=Next;GetOwner()->ForceNetUpdate();}
    if(GetNetMode()!=NM_DedicatedServer)ApplyAppearance(Next);
}
void UFPSPlayerBodyComponent::OnRep_Appearance()
{
    // The owning player's accepted local profile already drives its immediate preview.
    if(Character.IsValid()&&!Character->IsLocallyControlled())ApplyAppearance(ReplicatedAppearance);
}
void UFPSPlayerBodyComponent::ApplyAppearance(FFPSBodyAppearance Value)
{
    using namespace FPSBodyAppearance;
    auto* Body=GetBodyMesh();if(!Body||FPSPlayerBodyWorldBodySuppressed())return;
    Value=ResolveAppearance(Value);
    if(Value==AppliedAppearance&&(HeadMesh||AppearanceLoad.IsValid()))return;
    AppliedAppearance=Value;
    const auto Head=Object(Object(Configuration,TEXT("heads")),Value.HeadId.ToString());
    if(!Head)return;
    const FString MeshPath=Text(Head,TEXT("mesh"));
    const auto MaterialOverrides=Object(Head,TEXT("materials"));
    TArray<TSharedPtr<FJsonObject>> GroomRecipes;Grooms(Head,GroomRecipes);
    Grooms(Object(Object(Head,TEXT("hair_styles")),Value.HairId.ToString()),GroomRecipes);
    TArray<FSoftObjectPath> Paths;Paths.Add(FSoftObjectPath(MeshPath));
    TMap<FName,FSoftObjectPath> Materials;
    if(MaterialOverrides)for(const auto& Pair:MaterialOverrides->Values)
    {FSoftObjectPath Path(Pair.Value->AsString());Paths.AddUnique(Path);Materials.Add(FName(*Pair.Key),Path);}
    for(const auto& Recipe:GroomRecipes)
    {Paths.AddUnique(FSoftObjectPath(Text(Recipe,TEXT("asset"))));Paths.AddUnique(FSoftObjectPath(Text(Recipe,TEXT("binding"))));}
    const uint32 Request=++AppearanceRequest;
    if(AppearanceLoad)AppearanceLoad->CancelHandle();
    AppearanceLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this,Value,Request,MeshPath,GroomRecipes,Materials]()
    {
        if(Request!=AppearanceRequest||!Character.IsValid())return;
        auto* Parent=GetBodyMesh();
        auto* Mesh=Cast<USkeletalMesh>(FSoftObjectPath(MeshPath).ResolveObject());
        if(!Parent||!Mesh){UE_LOG(LogTemp,Error,TEXT("Player head unavailable: %s"),*MeshPath);return;}
        // All requested assets stay held until the replacement components own them.
        if(AppearanceLODSync)AppearanceLODSync->DestroyComponent();
        for(auto Groom:HeadGrooms)if(Groom)Groom->DestroyComponent();HeadGrooms.Reset();
        if(HeadMesh)HeadMesh->DestroyComponent();
        HeadMesh=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        GetOwner()->AddInstanceComponent(HeadMesh);HeadMesh->SetupAttachment(Parent);
        HeadMesh->SetSkeletalMeshAsset(Mesh);HeadMesh->SetRelativeTransform(FTransform::Identity);
        for(const auto& Pair:Materials)
            if(auto* Material=Cast<UMaterialInterface>(Pair.Value.ResolveObject()))
                HeadMesh->SetMaterialByName(Pair.Key,Material);
        HeadMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);HeadMesh->SetGenerateOverlapEvents(false);
        HeadMesh->SetAnimationMode(EAnimationMode::AnimationBlueprint);
        HeadMesh->SetAnimInstanceClass(UFPSPlayerHeadAnimInstance::StaticClass());
        HeadMesh->RegisterComponent();HeadMesh->AddTickPrerequisiteComponent(Parent);
        HeadMesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        for(const auto& Recipe:GroomRecipes)
        {
            auto* Asset=Cast<UGroomAsset>(FSoftObjectPath(Text(Recipe,TEXT("asset"))).ResolveObject());
            auto* Binding=Cast<UGroomBindingAsset>(FSoftObjectPath(Text(Recipe,TEXT("binding"))).ResolveObject());
            if(!Asset||!Binding){UE_LOG(LogTemp,Error,TEXT("Player groom unavailable for %s"),*Value.HeadId.ToString());continue;}
            auto* Groom=NewObject<UGroomComponent>(GetOwner(),NAME_None,RF_Transient);
            GetOwner()->AddInstanceComponent(Groom);Groom->SetupAttachment(HeadMesh);
            Groom->SetGroomAsset(Asset,Binding,false);Groom->SetEnableSimulation(false);
            Groom->SetCollisionEnabled(ECollisionEnabled::NoCollision);Groom->SetGenerateOverlapEvents(false);
            Groom->RegisterComponent();Groom->AddTickPrerequisiteComponent(HeadMesh);HeadGrooms.Add(Groom);
        }
        AppearanceLODSync=NewObject<ULODSyncComponent>(GetOwner(),NAME_None,RF_Transient);
        GetOwner()->AddInstanceComponent(AppearanceLODSync);
        const int32 FaceLODs=FMath::Max(1,Mesh->GetLODNum());
        const int32 BodyLODs=FMath::Max(1,Parent->GetSkeletalMeshAsset()->GetLODNum());
        const int32 SyncLODs=FMath::Max(FaceLODs,BodyLODs);
        AppearanceLODSync->NumLODs=SyncLODs;
        AppearanceLODSync->ComponentsToSync.Add(FComponentSync(Parent->GetFName(),ESyncOption::Drive));
        AppearanceLODSync->ComponentsToSync.Add(FComponentSync(HeadMesh->GetFName(),FaceLODs>1?ESyncOption::Drive:ESyncOption::Passive));
        // Different heads may supply different LOD counts. Match ranges without
        // forcing a nonexistent body or groom LOD when catalog entries change.
        const auto Mapping=[SyncLODs](int32 Count)
        {
            FLODMappingData Result;Count=FMath::Max(1,Count);
            for(int32 I=0;I<SyncLODs;++I)Result.Mapping.Add(FMath::RoundToInt(float(I*(Count-1))/FMath::Max(1,SyncLODs-1)));
            return Result;
        };
        FLODMappingData BodyMapping=Mapping(BodyLODs);
        AppearanceLODSync->CustomLODMapping.Add(Parent->GetFName(),BodyMapping);
        AppearanceLODSync->CustomLODMapping.Add(HeadMesh->GetFName(),Mapping(FaceLODs));
        for(auto Groom:HeadGrooms)
        {
            AppearanceLODSync->ComponentsToSync.Add(FComponentSync(Groom->GetFName(),ESyncOption::Passive));
            AppearanceLODSync->CustomLODMapping.Add(Groom->GetFName(),Mapping(Groom->GetNumSyncLODs()));
        }
        AppearanceLODSync->RegisterComponent();UpdateAppearanceVisibility();
        AppearanceLoad.Reset();
    }));
}
void UFPSPlayerBodyComponent::UpdateAppearanceVisibility()
{
    const auto* Body=GetBodyMesh();if(!Body)return;
    const bool Visible=Body->IsVisible()&&!Body->bHiddenInGame;
    TArray<UPrimitiveComponent*> Parts;if(HeadMesh)Parts.Add(HeadMesh);
    for(auto Groom:HeadGrooms)if(Groom)Parts.Add(Groom);
    for(auto* Part:Parts)
    {
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(Part,false,Body->bOwnerNoSee);
        FPSBodyEquipment::ApplyShadowFlags(Part,ShouldWorldBodyCastShadow());
        if(Part->IsVisible()!=Visible)Part->SetVisibility(Visible);
        if(Part->bHiddenInGame==Visible)Part->SetHiddenInGame(!Visible);
    }
    if(HeadMesh)HeadMesh->VisibilityBasedAnimTickOption=Body->VisibilityBasedAnimTickOption;
}
