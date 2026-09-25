#include "FPSModularOutfitComponent.h"
#include "FPSPlayerBodyComponent.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/AssetManager.h"
#include "Engine/GameInstance.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkinnedAssetCommon.h"
#include "Engine/StreamableManager.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/IConsoleManager.h"
#include "Materials/MaterialInterface.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"

namespace FPSModularOutfit
{
// Only explicitly authored first-person profiles participate in bare-arm rollout.
TAutoConsoleVariable<int32> CVarBareArmsCandidate(
    TEXT("fps.Outfit.BareArmsCandidate"),0,
    TEXT("1: registered realistic bare arms with modular shirt/gloves unequipped. 0: original source arms."),ECVF_Default);
FString PresentationKey(USkeletalMeshComponent* Source,FName Shirt,FName Gloves,bool bCandidate)
{
    return Source->GetSkeletalMeshAsset()->GetPathName()+TEXT("|")+Shirt.ToString()+TEXT("|")+Gloves.ToString()
        +(bCandidate?TEXT("|BareArms"):TEXT("|Default"));
}
TSharedPtr<FJsonObject> Object(const TSharedPtr<FJsonObject>& Parent,const FString& Key)
{
    const TSharedPtr<FJsonObject>* Value=nullptr;
    return Parent&&Parent->TryGetObjectField(Key,Value)?*Value:nullptr;
}
FString String(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{FString Value;if(Parent)Parent->TryGetStringField(Key,Value);return Value;}
bool Flag(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{bool Value=false;if(Parent)Parent->TryGetBoolField(Key,Value);return Value;}
TArray<int32> Numbers(const TSharedPtr<FJsonObject>& Parent,const TCHAR* Key)
{
    TArray<int32> Result;const TArray<TSharedPtr<FJsonValue>>* Values=nullptr;
    if(Parent&&Parent->TryGetArrayField(Key,Values))for(const auto& V:*Values)Result.Add(static_cast<int32>(V->AsNumber()));
    return Result;
}
void Section(USkeletalMeshComponent* Mesh,int32 Material,int32 LOD,bool bShow)
{
    const auto* Data=Mesh&&Mesh->GetSkeletalMeshAsset()?Mesh->GetSkeletalMeshAsset()->GetResourceForRendering():nullptr;
    if(!Data||!Data->LODRenderData.IsValidIndex(LOD))return;
    const auto& Sections=Data->LODRenderData[LOD].RenderSections;
    for(int32 S=0;S<Sections.Num();++S)if(Sections[S].MaterialIndex==Material)
        Mesh->ShowMaterialSection(Material,S,bShow,LOD);
}
}

UFPSModularOutfitComponent::UFPSModularOutfitComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
}
void UFPSModularOutfitComponent::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()==NM_DedicatedServer||!GetWorld()->IsGameWorld())
    {SetComponentTickEnabled(false);return;}
    FString Json;
    if(FFileHelper::LoadFileToString(Json,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/modular_outfits.json"))))
        FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json),Configuration);
    if(!Configuration){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(GetOwner());
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())AddTickPrerequisiteComponent(Body);
    RefreshInventory();
}
void UFPSModularOutfitComponent::RefreshInventory()
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(!Pawn||!Pawn->IsLocallyControlled()||!GetWorld()->GetGameInstance())return;
    auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!Model)return;
    if(!InventoryChanged.IsValid())
        InventoryChanged=Model->OnChanged.AddUObject(this,&UFPSModularOutfitComponent::RefreshInventory);
    TMap<int32,FName> Next;
    for(const auto& Item:Model->Items())if(Item.Place==1&&(Item.Cell==3||Item.Cell==7))Next.Add(Item.Cell,FName(*Item.Definition));
    if(Next.OrderIndependentCompareEqual(Equipped))return;
    Equipped=MoveTemp(Next);bDirty=true;DiscoverCountdown=0.f;
}
void UFPSModularOutfitComponent::SetWorldOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&Pawn->IsLocallyControlled()){RefreshInventory();return;}
    TMap<int32,FName> Next;
    for(const auto& Item:Outfit)if(Item.Slot==3||Item.Slot==7)Next.Add(Item.Slot,Item.Definition);
    if(!Next.OrderIndependentCompareEqual(Equipped)){Equipped=MoveTemp(Next);bDirty=true;DiscoverCountdown=0.f;}
}
void UFPSModularOutfitComponent::ReleasePresentation(FFPSOutfitPresentation& P)
{
    if(auto* Source=P.Source.Get();Source&&Source->GetSkeletalMeshAsset()==P.SourceAsset)
        for(int32 L=0;L<P.PreviouslyVisible.Num();++L)
            for(const int32 Material:P.PreviouslyVisible[L])FPSModularOutfit::Section(Source,Material,L,true);
    for(auto Part:P.Parts)if(IsValid(Part))Part->DestroyComponent();
    P.Parts.Reset();P.Key.Reset();P.SourceAsset=nullptr;
}
void UFPSModularOutfitComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    bEnding=true;
    if(GetWorld()&&GetWorld()->GetGameInstance())if(auto* Model=GetWorld()->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())
        Model->OnChanged.Remove(InventoryChanged);
    for(auto& Load:PendingLoads)if(Load.Value)Load.Value->CancelHandle();
    PendingLoads.Reset();
    for(auto& P:Presentations)ReleasePresentation(P);
    Presentations.Reset();Super::EndPlay(Reason);
}
void UFPSModularOutfitComponent::FollowVisibility(FFPSOutfitPresentation& P)
{
    auto* Source=P.Source.Get();if(!Source)return;
    const bool bVisible=Source->IsVisible()&&!Source->bHiddenInGame&&Source->GetSkeletalMeshAsset()==P.SourceAsset;
    for(auto Part:P.Parts)if(Part)
    {
        if(Part->IsVisible()!=bVisible)Part->SetVisibility(bVisible,false);
        if(Part->bHiddenInGame==bVisible)Part->SetHiddenInGame(!bVisible,false);
        if(Part->bOwnerNoSee!=Source->bOwnerNoSee)Part->SetOwnerNoSee(Source->bOwnerNoSee);
        if(Part->bOnlyOwnerSee!=Source->bOnlyOwnerSee)Part->SetOnlyOwnerSee(Source->bOnlyOwnerSee);
        if(Part->CastShadow!=Source->CastShadow)Part->SetCastShadow(Source->CastShadow);
        Part->bCastHiddenShadow=Source->bCastHiddenShadow;
        if(Part->FirstPersonPrimitiveType!=Source->FirstPersonPrimitiveType)Part->SetFirstPersonPrimitiveType(Source->FirstPersonPrimitiveType);
    }
}
void UFPSModularOutfitComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    DiscoverCountdown-=Delta;
    if(bDirty||DiscoverCountdown<=0.f){bDirty=false;DiscoverCountdown=.1f;DiscoverSources();}
    // Visibility changes (scope, casting, dual hand and third-person camera) are
    // followed every frame, without rebuilding meshes or parsing inventory JSON.
    for(auto& P:Presentations)FollowVisibility(P);
}
void UFPSModularOutfitComponent::DiscoverSources()
{
    using namespace FPSModularOutfit;
    if(!Configuration||bEnding)return;
    if(!InventoryChanged.IsValid())RefreshInventory();
    const auto Recipes=Object(Configuration,TEXT("items"));
    const auto GloveRecipe=Object(Recipes,Equipped.FindRef(3).ToString());
    const bool bRestoreSourceArms=String(GloveRecipe,TEXT("first_person_mode"))==TEXT("source_arms");
    const bool bWearingModularOutfit=Object(Recipes,Equipped.FindRef(7).ToString()).IsValid()
        ||(GloveRecipe.IsValid()&&!bRestoreSourceArms);
    bool bNativeBareHandsDefault=false;
    Configuration->TryGetBoolField(TEXT("native_bare_hands_default"),bNativeBareHandsDefault);
    const auto* Pawn=Cast<APawn>(GetOwner());
    const bool bTryCandidate=!bRestoreSourceArms&&!bWearingModularOutfit&&Pawn&&Pawn->IsLocallyControlled()
        &&CVarBareArmsCandidate.GetValueOnGameThread()==1;
    if(!bWearingModularOutfit&&!bNativeBareHandsDefault&&!bTryCandidate&&!bRestoreSourceArms)
    {
        // Returning the candidate switch to zero restores original sections.
        for(auto& Load:PendingLoads)if(Load.Value)Load.Value->CancelHandle();
        PendingLoads.Reset();
        for(auto& P:Presentations)ReleasePresentation(P);
        Presentations.Reset();
        return;
    }
    const auto Profiles=Object(Configuration,TEXT("profiles"));if(!Profiles)return;
    auto* BodyComponent=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* Body=BodyComponent?BodyComponent->GetBodyMesh():nullptr;
    TArray<USkeletalMeshComponent*> Sources;GetOwner()->GetComponents(Sources);
    const auto WantsCandidate=[&](USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile)
    {
        return bTryCandidate&&Source!=Body&&Source->bOnlyOwnerSee
            &&!Flag(Profile,TEXT("native_bare_arms"))
            &&!String(Profile,TEXT("bare_arms_candidate")).IsEmpty();
    };
    TSet<FString> CurrentKeys;
    for(auto* Source:Sources)if(Source&&Source->GetSkeletalMeshAsset()&&!Source->ComponentHasTag(TEXT("ModularOutfit"))
        &&(Source==Body||(Source->IsVisible()&&!Source->bHiddenInGame)))
    {
        const auto Profile=Object(Profiles,Source->GetSkeletalMeshAsset()->GetPathName());
        if(Source!=Body)
        {
            const bool bBaked=Flag(Profile,TEXT("native_bare_arms"));
            if((bRestoreSourceArms&&!bBaked)||(bBaked&&!bRestoreSourceArms&&!bWearingModularOutfit))continue;
        }
        CurrentKeys.Add(PresentationKey(Source,Equipped.FindRef(7),Equipped.FindRef(3),WantsCandidate(Source,Profile)));
    }
    for(auto It=PendingLoads.CreateIterator();It;++It)
        if(!CurrentKeys.Contains(It.Key())||FailedLoads.Contains(It.Key()))
        {if(It.Value()&&!It.Value()->HasLoadCompleted())It.Value()->CancelHandle();It.RemoveCurrent();}
    for(int32 I=Presentations.Num()-1;I>=0;--I)
    {
        auto& P=Presentations[I];auto* Source=P.Source.Get();
        if(!Source||Source->GetSkeletalMeshAsset()!=P.SourceAsset||!CurrentKeys.Contains(P.Key))
        {ReleasePresentation(P);Presentations.RemoveAt(I);}
    }
    for(auto* Source:Sources)
    {
        if(!IsValid(Source)||!Source->GetSkeletalMeshAsset()||Source->ComponentHasTag(TEXT("ModularOutfit")))continue;
        const bool bWorld=Source==Body;
        if(bWorld&&FPSPlayerBodyWorldBodySuppressed())continue;
        if(!bWorld&&(!Pawn||!Pawn->IsLocallyControlled()))continue;
        auto Profile=Object(Profiles,Source->GetSkeletalMeshAsset()->GetPathName());
        if(!Profile)continue;
        const bool bBakedBare=!bWorld&&Flag(Profile,TEXT("native_bare_arms"));
        if(!bWorld&&bRestoreSourceArms&&!bBakedBare)continue;
        // Baked viewmodels already contain the bare surface on their native rig.
        // No follower, async load or first-frame appearance swap is needed.
        if(bBakedBare&&!bWearingModularOutfit&&!bRestoreSourceArms)continue;
        const bool bOriginalGloves=bBakedBare&&bRestoreSourceArms;
        const bool bCandidate=WantsCandidate(Source,Profile);
        if(!bWearingModularOutfit&&!bNativeBareHandsDefault&&!bCandidate&&!bOriginalGloves)continue;
        // A future profile without a native default keeps its accepted source.
        // Never revive the old FBX-rebound base merely because the global default
        // is enabled for other weapons.
        if(!bWearingModularOutfit&&!bCandidate&&String(Profile,TEXT("native_bare_skin")).IsEmpty())continue;
        // World weapon copies have the same mesh paths as viewmodels, but have
        // no camera-space ownership. Never grow a second pair of arms on them.
        if(!bWorld&&!Source->bOnlyOwnerSee)continue;
        if(!bWorld&&(!Source->IsVisible()||Source->bHiddenInGame))continue;
        if(bOriginalGloves)
        {
            const FString Original=String(Profile,TEXT("original_gloved_arms"));
            if(Original.IsEmpty())continue;
            Profile=MakeShared<FJsonObject>(*Profile);
            Profile->SetStringField(TEXT("native_bare_skin"),Original);
            Profile->SetBoolField(TEXT("restore_original_gloves"),true);
        }
        else if(bCandidate)
        {
            Profile=MakeShared<FJsonObject>(*Profile);
            Profile->SetStringField(TEXT("native_bare_skin"),String(Profile,TEXT("bare_arms_candidate")));
            Profile->SetBoolField(TEXT("candidate_active"),true);
        }
        UpdatePresentation(Source,Profile,bWorld);
    }
}
void UFPSModularOutfitComponent::UpdatePresentation(USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile,bool bWorld)
{
    using namespace FPSModularOutfit;
    const auto Recipes=Object(Configuration,TEXT("items"));
    const auto Shirt=Flag(Profile,TEXT("restore_original_gloves"))?nullptr:Object(Recipes,Equipped.FindRef(7).ToString());
    const auto GloveRecipe=Object(Recipes,Equipped.FindRef(3).ToString());
    const TSharedPtr<FJsonObject> Gloves=String(GloveRecipe,TEXT("first_person_mode"))==TEXT("source_arms")
        ?nullptr:GloveRecipe;
    bool bCandidate=false;Profile->TryGetBoolField(TEXT("candidate_active"),bCandidate);
    FString Key=PresentationKey(Source,Equipped.FindRef(7),Equipped.FindRef(3),bCandidate);
    auto* Existing=Presentations.FindByPredicate([Source](const auto& P){return P.Source==Source;});
    if(Existing&&Existing->Key==Key)
    {
        // Other equipment refreshes can restore source sections; conceal only
        // the arm/body sections owned by this presentation, never weapon parts.
        for(int32 L=0;L<Existing->PreviouslyVisible.Num();++L)for(int32 M:Existing->HiddenMaterials)
            if(Source->IsMaterialSectionShown(M,L))Section(Source,M,L,false);
        return;
    }
    const FString NativeBase=String(Profile,TEXT("native_bare_skin"));
    TArray<FString> MeshPaths{NativeBase.IsEmpty()?String(Profile,TEXT("base")):NativeBase};
    TArray<FString> MaterialPaths{TEXT("")};
    const auto PartMesh=[&Profile](const TSharedPtr<FJsonObject>& Recipe,const TCHAR* Part)
    {
        // New shapes register their own bound mesh for every supported rig.
        const auto RigMeshes=Object(Recipe,TEXT("rig_meshes"));
        const FString Override=String(RigMeshes,*String(Profile,TEXT("rig_profile")));
        return RigMeshes?Override:String(Profile,Part);
    };
    if(Shirt){MeshPaths.Add(PartMesh(Shirt,TEXT("shirt")));MaterialPaths.Add(String(Shirt,TEXT("material")));}
    if(Gloves){MeshPaths.Add(PartMesh(Gloves,TEXT("gloves")));MaterialPaths.Add(String(Gloves,TEXT("material")));}
    TArray<FSoftObjectPath> Paths;
    bool bLoaded=true;
    for(const FString& Path:MeshPaths)
    {if(Path.IsEmpty())return;Paths.AddUnique(FSoftObjectPath(Path));bLoaded&=Cast<USkeletalMesh>(FSoftObjectPath(Path).ResolveObject())!=nullptr;}
    for(const FString& Path:MaterialPaths)if(!Path.IsEmpty())
    {Paths.AddUnique(FSoftObjectPath(Path));bLoaded&=Cast<UMaterialInterface>(FSoftObjectPath(Path).ResolveObject())!=nullptr;}
    if(!bLoaded)
    {
        if(PendingLoads.Contains(Key)||FailedLoads.Contains(Key))return;
        // Only outstanding loads retain handles; committed components hold assets.
        // Rapid outfit switching has a bounded number of in-flight requests.
        if(PendingLoads.Num()>=8)return;
        TWeakObjectPtr<UFPSModularOutfitComponent> WeakThis(this);
        auto Handle=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
            FStreamableDelegate::CreateLambda([WeakThis,Key,Paths]()
            {
                if(auto* Self=WeakThis.Get();Self&&!Self->bEnding)
                {
                    bool bOK=true;for(const auto& Path:Paths)bOK&=Path.ResolveObject()!=nullptr;
                    if(!bOK){Self->FailedLoads.Add(Key);UE_LOG(LogTemp,Warning,TEXT("Modular outfit asset unavailable: %s"),*Key);}
                    Self->bDirty=true;
                    // Keep the completed handle until DiscoverSources has bound
                    // the current request. Stale requests are released below.
                }
            }));
        PendingLoads.Add(Key,MoveTemp(Handle));return;
    }
    TArray<TObjectPtr<USkeletalMeshComponent>> NewParts;
    for(int32 I=0;I<MeshPaths.Num();++I)
    {
        auto* Part=NewObject<USkeletalMeshComponent>(GetOwner(),NAME_None,RF_Transient);
        GetOwner()->AddInstanceComponent(Part);Part->ComponentTags.Add(TEXT("ModularOutfit"));
        Part->SetSkeletalMeshAsset(Cast<USkeletalMesh>(FSoftObjectPath(MeshPaths[I]).ResolveObject()));
        Part->SetupAttachment(Source);Part->SetRelativeTransform(FTransform::Identity);
        Part->SetCollisionEnabled(ECollisionEnabled::NoCollision);Part->SetGenerateOverlapEvents(false);
        Part->SetOnlyOwnerSee(Source->bOnlyOwnerSee);Part->SetOwnerNoSee(Source->bOwnerNoSee);
        Part->SetCastShadow(Source->CastShadow);Part->bCastHiddenShadow=Source->bCastHiddenShadow;
        Part->SetFirstPersonPrimitiveType(Source->FirstPersonPrimitiveType);
        Part->SetVisibility(false);Part->SetLeaderPoseComponent(Source);
        Part->bUseAttachParentBound=true;Part->RegisterComponent();
        Part->SetComponentTickEnabled(false);
        if(!MaterialPaths[I].IsEmpty())
            for(int32 M=0;M<Part->GetNumMaterials();++M)Part->SetMaterial(M,Cast<UMaterialInterface>(FSoftObjectPath(MaterialPaths[I]).ResolveObject()));
        NewParts.Add(Part);
    }
    // Cover the body only once the entire mesh/material recipe is resident.
    auto* Base=NewParts[0].Get();const auto* BaseData=Base->GetSkeletalMeshAsset()->GetResourceForRendering();
    TArray<int32> Covered;
    if(Shirt)Covered.Append(Numbers(Profile,TEXT("shirt_covers")));
    if(Gloves)Covered.Append(Numbers(Profile,TEXT("glove_covers")));
    if(BaseData)for(int32 L=0;L<BaseData->LODRenderData.Num();++L)for(const int32 M:Covered)Section(Base,M,L,false);
    if(Existing)ReleasePresentation(*Existing);
    else Existing=&Presentations.AddDefaulted_GetRef();
    Existing->Source=Source;Existing->SourceAsset=Source->GetSkeletalMeshAsset();Existing->Key=Key;Existing->bWorld=bWorld;
    Existing->Parts=MoveTemp(NewParts);Existing->HiddenMaterials=Numbers(Profile,TEXT("hide_source_materials"));
    Existing->PreviouslyVisible.Reset();
    if(const auto* Data=Source->GetSkeletalMeshAsset()->GetResourceForRendering())
        for(int32 L=0;L<Data->LODRenderData.Num();++L)
        {
            auto& Visible=Existing->PreviouslyVisible.AddDefaulted_GetRef();
            for(int32 M:Existing->HiddenMaterials)
            {if(Source->IsMaterialSectionShown(M,L))Visible.Add(M);Section(Source,M,L,false);}
        }
    FollowVisibility(*Existing);
    // Completed stale loads cannot apply an old recipe: source identity and the
    // current equipment are re-read by DiscoverSources, never captured on commit.
    for(auto It=PendingLoads.CreateIterator();It;++It)
        if(!It.Value()||It.Value()->HasLoadCompleted())It.RemoveCurrent();
}

bool UFPSModularOutfitComponent::ConfigureDistanceLODs(USkeletalMesh* Mesh)
{
#if WITH_EDITOR
    if(!Mesh||!Mesh->GetPathName().StartsWith(TEXT("/Game/Characters/ModularOutfit20260924/")))return false;
    const FSkeletalMeshLODInfo* Base=Mesh->GetLODInfo(0);
    if(!Base||Base->bHasBeenSimplified)return false;
    const FSkeletalMeshBuildSettings Build=Base->BuildSettings;
    Mesh->Modify();
    while(Mesh->GetLODNum()<3)Mesh->AddLODInfo();
    for(int32 L=1;L<3;++L)
    {
        auto& Info=*Mesh->GetLODInfo(L);Info.BuildSettings=Build;
        Info.ScreenSize.Default=L==1?.18f:.075f;Info.LODHysteresis=.015f;
        auto& R=Info.ReductionSettings;R.BaseLOD=0;R.TerminationCriterion=SMTC_NumOfTriangles;
        R.NumOfTrianglesPercentage=L==1?.5f:.2f;R.MaxBonesPerVertex=8;
        R.bRecalcNormals=false;R.bEnforceBoneBoundaries=true;R.bLockEdges=true;R.bLockColorBounaries=true;
        Info.bHasBeenSimplified=true;
    }
    Mesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
