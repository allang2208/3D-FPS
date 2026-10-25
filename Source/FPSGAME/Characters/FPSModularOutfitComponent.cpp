#include "FPSModularOutfitComponent.h"
#include "FPSPlayerBodyComponent.h"
#include "FPSOutfitSecondaryMotion.h"
#include "FPSQuiverMotion.h"
#include "Engine/StaticMesh.h"
#include "FPSOutfitRobeCloth.h"
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
FString PresentationKey(USkeletalMeshComponent* Source,FName Shirt,FName Gloves,bool bCandidate,FName Pants=NAME_None,FName Shoes=NAME_None,FName Belt=NAME_None)
{
    return Source->GetSkeletalMeshAsset()->GetPathName()+TEXT("|")+Shirt.ToString()+TEXT("|")+Gloves.ToString()
        +(bCandidate?TEXT("|BareArms"):TEXT("|Default"))+TEXT("|")+Pants.ToString()+TEXT("|")+Shoes.ToString()+TEXT("|")+Belt.ToString()
        +(Source->ComponentHasTag(TEXT("SharedOwnerBody"))?TEXT("|SharedOwnerBody"):TEXT(""));
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
    BaseConfiguration=Configuration;
    BodyConfigurations.Add(TEXT("jason"),BaseConfiguration);
    if(const auto Variants=FPSModularOutfit::Object(BaseConfiguration,TEXT("body_variants")))
        for(const auto& Entry:Variants->Values)
        {
            const TSharedPtr<FJsonObject>* Value=nullptr;
            if(Entry.Value->TryGetObject(Value))BodyConfigurations.Add(FName(*Entry.Key),*Value);
        }
    AddTickPrerequisiteActor(GetOwner());
    if(auto* Body=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>())
    {AddTickPrerequisiteComponent(Body);SetBodyType(Body->GetBodyType());}
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
    for(const auto& Item:Model->Items())if(Item.Place==1&&(Item.Cell==3||Item.Cell==7||Item.Cell==10||Item.Cell==13||Item.Cell==15))Next.Add(Item.Cell,FName(*Item.Definition));
    if(Next.OrderIndependentCompareEqual(Equipped))return;
    Equipped=MoveTemp(Next);bDirty=true;DiscoverCountdown=0.f;
}
bool UFPSModularOutfitComponent::IsSteelGauntletEquipped() const
{
    static const FName SteelGauntlets(TEXT("ue_steel_gauntlets"));
    return Equipped.FindRef(3)==SteelGauntlets;
}
bool UFPSModularOutfitComponent::IsChainmailEquipped() const
{
    static const FName Chainmail(TEXT("ue_chainmail_shirt"));
    return Equipped.FindRef(7)==Chainmail;
}
void UFPSModularOutfitComponent::SetWorldOutfit(const TArray<FFPSBodyOutfitSlot>& Outfit)
{
    const auto* Pawn=Cast<APawn>(GetOwner());
    if(Pawn&&Pawn->IsLocallyControlled()){RefreshInventory();return;}
    TMap<int32,FName> Next;
    for(const auto& Item:Outfit)if(Item.Slot==3||Item.Slot==7||Item.Slot==10||Item.Slot==13||Item.Slot==15)Next.Add(Item.Slot,Item.Definition);
    if(!Next.OrderIndependentCompareEqual(Equipped)){Equipped=MoveTemp(Next);bDirty=true;DiscoverCountdown=0.f;}
}
void UFPSModularOutfitComponent::ReleasePresentation(FFPSOutfitPresentation& P)
{
    if(P.RobeHem)if(auto* Robe=P.RobeHem->Garment.Get())
    {
        PrimaryComponentTick.RemovePrerequisite(Robe,Robe->PrimaryComponentTick);
        PrimaryComponentTick.RemovePrerequisite(Robe,Robe->ClothTickFunction);
        PrimaryComponentTick.RemovePrerequisite(Robe,Robe->ClothEndTickFunction);
    }
    if(P.SecondaryMotion)
    {
        if(auto* Source=P.Source.Get())RemoveTickPrerequisiteComponent(Source);
        P.SecondaryMotion.Reset();
    }
    if(auto* Source=P.Source.Get();Source&&Source->GetSkeletalMeshAsset()==P.SourceAsset)
        for(int32 L=0;L<P.PreviouslyVisible.Num();++L)
            for(const int32 Material:P.PreviouslyVisible[L])FPSModularOutfit::Section(Source,Material,L,true);
    P.QuiverMotion.Reset();
    for(auto Part:P.Parts)if(IsValid(Part))Part->DestroyComponent();
    P.StairSections.Reset();
    P.RobeHem.Reset();
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
    UpdateRobeStairVisibility();
    // Visibility changes (scope, casting, dual hand and third-person camera) are
    // followed every frame, without rebuilding meshes or parsing inventory JSON.
    for(auto& P:Presentations)
    {
        FollowVisibility(P);
        if(P.QuiverMotion)P.QuiverMotion->Tick(Delta);
        for(auto Part:P.Parts)FPSOutfitRobeCloth::Update(Part,Delta);
        if(P.RobeHem)P.RobeHem->Update(bHideRobeCalves,Delta);
        for(auto& Sections:P.StairSections)
        {
            Sections.Apply(bHideRobeCalves);
            if(P.RobeHem)Sections.Conform(*P.RobeHem);
        }
        if(P.SecondaryMotion)P.SecondaryMotion->Tick(Delta);
    }
}
void UFPSModularOutfitComponent::ResetBodyPresentation()
{
    for(auto& Load:PendingLoads)if(Load.Value)Load.Value->CancelHandle();
    PendingLoads.Reset();FailedLoads.Reset();
    for(auto& Presentation:Presentations)ReleasePresentation(Presentation);
    Presentations.Reset();bDirty=true;DiscoverCountdown=0.f;
}

void UFPSModularOutfitComponent::SetBodyType(FName BodyId)
{
    const auto* Next=BodyConfigurations.Find(BodyId);
    if(!Next||Configuration==*Next)return;
    ResetBodyPresentation();Configuration=*Next;
}

void UFPSModularOutfitComponent::CollectBodyAssets(FName BodyId,const FString& BodyMesh,TArray<FSoftObjectPath>& Out) const
{
    using namespace FPSModularOutfit;
    const auto* Target=BodyConfigurations.Find(BodyId);if(!Target)return;
    const auto Profiles=Object(*Target,TEXT("profiles"));if(!Profiles)return;
    const auto Items=Object(*Target,TEXT("items"));
    const auto Shirt=Object(Items,Equipped.FindRef(7).ToString());
    const auto Pants=Object(Items,Equipped.FindRef(15).ToString());
    const auto Shoes=Object(Items,Equipped.FindRef(13).ToString());
    const auto Gloves=Object(Items,Equipped.FindRef(3).ToString());
    TSet<FString> Rigs,SelectedPants,SelectedInnerSources;
    bool bHasExactShirtFit=false;
    TFunction<void(const TSharedPtr<FJsonValue>&)> Collect;
    Collect=[&](const TSharedPtr<FJsonValue>& Value)
    {
        if(!Value)return;
        if(Value->Type==EJson::String)
        {const FString Path=Value->AsString();if(Path.StartsWith(TEXT("/Game/")))Out.AddUnique(FSoftObjectPath(Path));}
        else if(Value->Type==EJson::Array)for(const auto& Child:Value->AsArray())Collect(Child);
        else if(Value->Type==EJson::Object)for(const auto& Child:Value->AsObject()->Values)
        {
            // Rig maps carry dozens of native viewmodels. Stream only the rigs
            // owned by this pawn plus its new body, not every weapon in the game.
            if(Child.Key==TEXT("rig_meshes")||Child.Key==TEXT("owner_body_meshes")||Child.Key==TEXT("skin_meshes")||Child.Key==TEXT("base_material_overrides"))
            {
                const auto Map=Child.Value->AsObject();
                if(Map)for(const FString& Rig:Rigs)Collect(Map->TryGetField(Rig));
            }
            else if(Child.Key==TEXT("shoe_fit_meshes"))
            {
                const auto Fit=Object(Child.Value->AsObject(),Equipped.FindRef(13).ToString());
                if(Fit)for(const FString& Rig:Rigs)Collect(Fit->TryGetField(Rig));
            }
            else if(Child.Key==TEXT("pants_mesh_fit_meshes"))
            {
                const auto Map=Child.Value->AsObject();
                if(Map)for(const FString& Path:SelectedPants)Collect(Map->TryGetField(Path));
            }
            else if(Child.Key==TEXT("pants_fit_meshes"))
            {
                if(!bHasExactShirtFit&&!SelectedPants.IsEmpty())
                    Collect(Child.Value->AsObject()->TryGetField(Equipped.FindRef(15).ToString()));
            }
            else if(Child.Key==TEXT("pants_fit_default"))
            {if(!bHasExactShirtFit&&!SelectedPants.IsEmpty())Collect(Child.Value);}
            else if(Child.Key==TEXT("underlayer_meshes"))
            {
                const auto Map=Child.Value->AsObject();
                if(Map)for(const FString& Path:SelectedInnerSources)Collect(Map->TryGetField(Path));
            }
            else Collect(Child.Value);
        }
    };
    TArray<USkeletalMeshComponent*> Sources;GetOwner()->GetComponents(Sources);
    TSet<FString> SourcePaths;SourcePaths.Add(BodyMesh);
    for(auto* Source:Sources)if(Source&&Source->bOnlyOwnerSee&&Source->GetSkeletalMeshAsset()
        &&!Source->ComponentHasTag(TEXT("ModularOutfit"))&&((Source->IsVisible()&&!Source->bHiddenInGame)
            ||Source->ComponentHasTag(TEXT("PreloadModularOutfit"))))SourcePaths.Add(Source->GetSkeletalMeshAsset()->GetPathName());
    for(const FString& Path:SourcePaths)if(const auto Profile=Object(Profiles,Path))
    {
        Rigs.Add(String(Profile,TEXT("rig_profile")));
        const FString Base=String(Profile,TEXT("native_bare_skin")).IsEmpty()?String(Profile,TEXT("base")):String(Profile,TEXT("native_bare_skin"));
        if(!Base.IsEmpty()){Out.AddUnique(FSoftObjectPath(Base));SelectedInnerSources.Add(Base);}
        if(String(Gloves,TEXT("first_person_mode"))==TEXT("source_arms"))Collect(Profile->TryGetField(TEXT("original_gloved_arms")));
        if(CVarBareArmsCandidate.GetValueOnGameThread()==1)Collect(Profile->TryGetField(TEXT("bare_arms_candidate")));
    }
    const auto ShoeFit=Object(Object(Pants,TEXT("shoe_fit_meshes")),Equipped.FindRef(13).ToString());
    for(const FString& Rig:Rigs)
    {
        FString Trouser=String(ShoeFit,*Rig);
        if(Trouser.IsEmpty())Trouser=String(Object(Pants,TEXT("rig_meshes")),*Rig);
        if(!Trouser.IsEmpty())
        {
            SelectedPants.Add(Trouser);SelectedInnerSources.Add(Trouser);
            bHasExactShirtFit|=Object(Object(Shirt,TEXT("pants_mesh_fit_meshes")),Trouser).IsValid();
        }
        for(const FString& Part:{String(Object(Shoes,TEXT("rig_meshes")),*Rig),String(Object(Gloves,TEXT("skin_meshes")),*Rig)})
            if(!Part.IsEmpty())SelectedInnerSources.Add(Part);
    }
    if(Items)for(const auto& Entry:Equipped)
        Collect(Items->TryGetField(Entry.Value.ToString()));
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
    const bool bWearingLowerBody=Object(Recipes,Equipped.FindRef(15).ToString()).IsValid()
        ||Object(Recipes,Equipped.FindRef(13).ToString()).IsValid()
        ||Object(Recipes,Equipped.FindRef(10).ToString()).IsValid();
    bool bNativeBareHandsDefault=false;
    Configuration->TryGetBoolField(TEXT("native_bare_hands_default"),bNativeBareHandsDefault);
    const auto* Pawn=Cast<APawn>(GetOwner());
    const bool bTryCandidate=!bRestoreSourceArms&&!bWearingModularOutfit&&Pawn&&Pawn->IsLocallyControlled()
        &&CVarBareArmsCandidate.GetValueOnGameThread()==1;
    auto* BodyComponent=GetOwner()->FindComponentByClass<UFPSPlayerBodyComponent>();
    auto* Body=BodyComponent?BodyComponent->GetBodyMesh():nullptr;
    auto* LowerBody=BodyComponent?BodyComponent->GetFirstPersonLowerBodyMesh():nullptr;
    if(!LowerBody&&!bWearingModularOutfit&&!bWearingLowerBody&&!bNativeBareHandsDefault&&!bTryCandidate&&!bRestoreSourceArms)
    {
        // Returning the candidate switch to zero restores original sections.
        for(auto& Load:PendingLoads)if(Load.Value)Load.Value->CancelHandle();
        PendingLoads.Reset();
        for(auto& P:Presentations)ReleasePresentation(P);
        Presentations.Reset();
        return;
    }
    const auto Profiles=Object(Configuration,TEXT("profiles"));if(!Profiles)return;
    TArray<USkeletalMeshComponent*> Sources;GetOwner()->GetComponents(Sources);
    const auto WantsCandidate=[&](USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile)
    {
        return bTryCandidate&&Source!=Body&&Source!=LowerBody&&Source->bOnlyOwnerSee
            &&!Flag(Profile,TEXT("native_bare_arms"))
            &&!String(Profile,TEXT("bare_arms_candidate")).IsEmpty();
    };
    TSet<FString> CurrentKeys;
    for(auto* Source:Sources)if(Source&&Source->GetSkeletalMeshAsset()&&!Source->ComponentHasTag(TEXT("ModularOutfit"))
        &&(Source==Body||(Source->IsVisible()&&!Source->bHiddenInGame)
            ||(Source->bOnlyOwnerSee&&Source->ComponentHasTag(TEXT("PreloadModularOutfit")))))
    {
        const auto Profile=Object(Profiles,Source->GetSkeletalMeshAsset()->GetPathName());
        if(Source!=Body&&Source!=LowerBody)
        {
            const bool bBaked=Flag(Profile,TEXT("native_bare_arms"));
            if((bRestoreSourceArms&&!bBaked)||(bBaked&&!bRestoreSourceArms&&!bWearingModularOutfit))continue;
        }
        const bool bHasLegs=Source==Body||Source==LowerBody;
        CurrentKeys.Add(PresentationKey(Source,Equipped.FindRef(7),Source==LowerBody?NAME_None:Equipped.FindRef(3),WantsCandidate(Source,Profile),
            bHasLegs?Equipped.FindRef(15):NAME_None,bHasLegs?Equipped.FindRef(13):NAME_None,bHasLegs?Equipped.FindRef(10):NAME_None));
    }
    for(auto It=PendingLoads.CreateIterator();It;++It)
        if(!CurrentKeys.Contains(It.Key())||FailedLoads.Contains(It.Key()))
        {if(It.Value()&&!It.Value()->HasLoadCompleted())It.Value()->CancelHandle();It.RemoveCurrent();}
    TSet<USkeletalMeshComponent*> ActiveSources;
    for(auto* Source:Sources)
    {
        if(!IsValid(Source)||!Source->GetSkeletalMeshAsset()||Source->ComponentHasTag(TEXT("ModularOutfit")))continue;
        const bool bWorld=Source==Body;
        const bool bLowerBody=Source==LowerBody;
        const bool bHasLegs=bWorld||bLowerBody;
        if(bWorld&&FPSPlayerBodyWorldBodySuppressed())continue;
        if(!bWorld&&(!Pawn||!Pawn->IsLocallyControlled()))continue;
        auto Profile=Object(Profiles,Source->GetSkeletalMeshAsset()->GetPathName());
        if(!Profile)continue;
        const bool bBakedBare=!bHasLegs&&Flag(Profile,TEXT("native_bare_arms"));
        if(!bHasLegs&&bRestoreSourceArms&&!bBakedBare)continue;
        // Baked viewmodels already contain the bare surface on their native rig.
        // No follower, async load or first-frame appearance swap is needed.
        if(bBakedBare&&!bWearingModularOutfit&&!bRestoreSourceArms)continue;
        const bool bOriginalGloves=bBakedBare&&bRestoreSourceArms;
        const bool bCandidate=WantsCandidate(Source,Profile);
        if(!bLowerBody&&!bWearingModularOutfit&&!(bWorld&&bWearingLowerBody)&&!bNativeBareHandsDefault&&!bCandidate&&!bOriginalGloves)continue;
        // A future profile without a native default keeps its accepted source.
        // Never revive the old FBX-rebound base merely because the global default
        // is enabled for other weapons.
        if(!bWearingModularOutfit&&!(bHasLegs&&bWearingLowerBody)&&!bCandidate&&String(Profile,TEXT("native_bare_skin")).IsEmpty())continue;
        // World weapon copies have the same mesh paths as viewmodels, but have
        // no camera-space ownership. Never grow a second pair of arms on them.
        if(!bWorld&&!Source->bOnlyOwnerSee)continue;
        // Traversal needs its outfit before the hands enter view. Retain this
        // presentation between actions; FollowVisibility still gates rendering.
        if(!bWorld&&(!Source->IsVisible()||Source->bHiddenInGame)
            &&!Source->ComponentHasTag(TEXT("PreloadModularOutfit")))continue;
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
        ActiveSources.Add(Source);
        UpdatePresentation(Source,Profile,bWorld,bLowerBody);
    }
    // A new equipment key can still be loading. Keep the last complete outfit
    // until UpdatePresentation commits its replacement; removing it by key here
    // exposes the source body (or empties the owner-only body) between loads.
    // Sources which no longer participate still restore their original sections.
    for(int32 I=Presentations.Num()-1;I>=0;--I)
    {
        auto& P=Presentations[I];auto* Source=P.Source.Get();
        if(!Source||Source->GetSkeletalMeshAsset()!=P.SourceAsset||!ActiveSources.Contains(Source))
        {ReleasePresentation(P);Presentations.RemoveAt(I);}
    }
}
void UFPSModularOutfitComponent::UpdatePresentation(USkeletalMeshComponent* Source,const TSharedPtr<FJsonObject>& Profile,bool bWorld,bool bLowerBody)
{
    using namespace FPSModularOutfit;
    const bool bHasLegs=bWorld||bLowerBody;
    const auto Recipes=Object(Configuration,TEXT("items"));
    auto Shirt=Flag(Profile,TEXT("restore_original_gloves"))?nullptr:Object(Recipes,Equipped.FindRef(7).ToString());
    const FString OwnerShirt=String(Object(Shirt,TEXT("owner_body_meshes")),*String(Profile,TEXT("rig_profile")));
    const auto BaseMaterials=Object(Object(Shirt,TEXT("base_material_overrides")),String(Profile,TEXT("rig_profile")));
    // Only display an authored torso section set. A missing owner variant must
    // not introduce duplicate arms. Material-only shirts use the native body.
    if(bLowerBody&&OwnerShirt.IsEmpty()&&(!BaseMaterials||BaseMaterials->Values.IsEmpty()))Shirt=nullptr;
    const auto GloveRecipe=Object(Recipes,Equipped.FindRef(3).ToString());
    const TSharedPtr<FJsonObject> Gloves=bLowerBody||String(GloveRecipe,TEXT("first_person_mode"))==TEXT("source_arms")
        ?nullptr:GloveRecipe;
    const auto Pants=bHasLegs?Object(Recipes,Equipped.FindRef(15).ToString()):nullptr;
    const auto Shoes=bHasLegs?Object(Recipes,Equipped.FindRef(13).ToString()):nullptr;
    const auto Belt=bHasLegs?Object(Recipes,Equipped.FindRef(10).ToString()):nullptr;
    bool bCandidate=false;Profile->TryGetBoolField(TEXT("candidate_active"),bCandidate);
    FString Key=PresentationKey(Source,Equipped.FindRef(7),bLowerBody?NAME_None:Equipped.FindRef(3),bCandidate,
        bHasLegs?Equipped.FindRef(15):NAME_None,bHasLegs?Equipped.FindRef(13):NAME_None,bHasLegs?Equipped.FindRef(10):NAME_None);
    auto* Existing=Presentations.FindByPredicate([Source](const auto& P){return P.Source==Source;});
    if(Existing&&Existing->Key==Key)
    {
        // Other equipment refreshes can restore source sections; conceal only
        // the arm/body sections owned by this presentation, never weapon parts.
        for(int32 L=0;L<Existing->PreviouslyVisible.Num();++L)for(int32 M:Existing->HiddenMaterials)
            if(Source->IsMaterialSectionShown(M,L))Section(Source,M,L,false);
        return;
    }
    TMap<int32,FString> BaseMaterialPaths;
    if(BaseMaterials)for(const auto& Entry:BaseMaterials->Values)
    {
        FString Path;
        if(FString(*Entry.Key).IsNumeric()&&Entry.Value->TryGetString(Path)&&!Path.IsEmpty())
            BaseMaterialPaths.Add(FCString::Atoi(*Entry.Key),MoveTemp(Path));
    }
    const FString NativeBase=String(Profile,TEXT("native_bare_skin"));
    // Open gloves can keep the exposed fingers while omitting skin hidden
    // beneath the leather. The shared naked-hand mesh remains untouched.
    const FString GloveSkin=String(Object(Gloves,TEXT("skin_meshes")),*String(Profile,TEXT("rig_profile")));
    // Long garments supply clipped inner layers in the same native binding.
    // An explicit empty replacement omits a fully covered clothing part only;
    // equipment state, the complete pose source and shoe selection stay intact.
    const auto Underlayers=bHasLegs?Object(Shirt,TEXT("underlayer_meshes")):nullptr;
    const auto UnderlayerMesh=[&Underlayers](const FString& Path)
    {return Underlayers&&Underlayers->HasField(Path)?String(Underlayers,*Path):Path;};
    TArray<FString> MeshPaths{UnderlayerMesh(!GloveSkin.IsEmpty()?GloveSkin:NativeBase.IsEmpty()?String(Profile,TEXT("base")):NativeBase)};
    TArray<FString> MaterialPaths{TEXT("")};
    const auto PartMesh=[&Profile](const TSharedPtr<FJsonObject>& Recipe,const TCHAR* Part)
    {
        // New shapes register their own bound mesh for every supported rig.
        const auto RigMeshes=Object(Recipe,TEXT("rig_meshes"));
        const FString Override=String(RigMeshes,*String(Profile,TEXT("rig_profile")));
        return RigMeshes?Override:String(Profile,Part);
    };
    const FString OutfitRig=String(Profile,TEXT("rig_profile"));
    const auto ShoeFit=Object(Object(Pants,TEXT("shoe_fit_meshes")),Equipped.FindRef(13).ToString());
    const FString FittedPants=String(ShoeFit,*OutfitRig);
    const FString SelectedPants=Pants?(FittedPants.IsEmpty()?PartMesh(Pants,TEXT("pants")):FittedPants):FString();
    const bool bUseShirtMesh=Shirt&&(!bLowerBody||!OwnerShirt.IsEmpty());
    if(bUseShirtMesh)
    {
        // Fit the actual boot-selected waist first. New pants without an
        // authored pair still use the shirt's tucked default; removing pants
        // restores its normal silhouette through the existing presentation key.
        const auto ReadFit=[&](const TSharedPtr<FJsonObject>& Fit)
        {return String(Object(Fit,bLowerBody?TEXT("owner_body_meshes"):TEXT("rig_meshes")),*OutfitRig);};
        FString FittedShirt;
        if(bHasLegs&&Pants&&!SelectedPants.IsEmpty())
        {
            FittedShirt=ReadFit(Object(Object(Shirt,TEXT("pants_mesh_fit_meshes")),SelectedPants));
            if(FittedShirt.IsEmpty())FittedShirt=ReadFit(Object(Object(Shirt,TEXT("pants_fit_meshes")),Equipped.FindRef(15).ToString()));
            if(FittedShirt.IsEmpty())FittedShirt=ReadFit(Object(Shirt,TEXT("pants_fit_default")));
        }
        MeshPaths.Add(!FittedShirt.IsEmpty()?FittedShirt:bLowerBody?OwnerShirt:PartMesh(Shirt,TEXT("shirt")));
        MaterialPaths.Add(String(Shirt,TEXT("material")));
    }
    // Optional per-slot view materials leave the saved meshes and world-body
    // materials intact. Load them in the same async batch as the outfit.
    TArray<FString> ShirtViewMaterials;
    const TArray<TSharedPtr<FJsonValue>>* ViewMaterials=nullptr;
    if(!bHasLegs&&Shirt&&Shirt->TryGetArrayField(TEXT("first_person_materials"),ViewMaterials))
        for(const auto& Value:*ViewMaterials)ShirtViewMaterials.Add(Value->AsString());
    bool bGloveInBase=false;if(Gloves)Gloves->TryGetBoolField(TEXT("glove_in_base"),bGloveInBase);
    if(Flag(Profile,TEXT("separate_gloves")))bGloveInBase=false;
    if(Gloves&&!bGloveInBase){MeshPaths.Add(PartMesh(Gloves,TEXT("gloves")));MaterialPaths.Add(String(Gloves,TEXT("material")));}
    if(Pants)
    {
        // Boot-specific cuffs share the normal inventory item and follow the
        // same async outfit load; switching shoes restores the default trousers.
        FString PantsPath=UnderlayerMesh(SelectedPants);
        if(!(Underlayers&&Underlayers->HasField(SelectedPants)))
        {
            // A long robe can cover future trousers before their exact inner
            // layer is authored. This keeps complete native legs and follows
            // the selected boot cuff, without showing a wide outer trouser.
            const auto DefaultInner=Object(Shirt,TEXT("pants_underlayer_default"));
            const FString BootInner=String(Object(Object(DefaultInner,TEXT("shoe_fit_meshes")),Equipped.FindRef(13).ToString()),*OutfitRig);
            const FString Inner=BootInner.IsEmpty()?String(Object(DefaultInner,TEXT("rig_meshes")),*OutfitRig):BootInner;
            if(!Inner.IsEmpty())PantsPath=Inner;
        }
        if(PantsPath.IsEmpty()&&!(Underlayers&&Underlayers->HasField(SelectedPants)))return;
        if(!PantsPath.IsEmpty()){MeshPaths.Add(PantsPath);MaterialPaths.Add(String(Pants,TEXT("material")));}
    }
    if(Shoes)
    {
        const FString SelectedShoes=PartMesh(Shoes,TEXT("shoes"));
        const FString ShoesPath=UnderlayerMesh(SelectedShoes);
        if(ShoesPath.IsEmpty()&&!(Underlayers&&Underlayers->HasField(SelectedShoes)))return;
        if(!ShoesPath.IsEmpty()){MeshPaths.Add(ShoesPath);MaterialPaths.Add(String(Shoes,TEXT("material")));}
    }
    const int32 BeltIndex=Belt?MeshPaths.Num():INDEX_NONE;
    const auto QuiverSettings=Object(Belt,TEXT("quiver_motion"));
    const FString QuiverArrowPath=String(QuiverSettings,TEXT("arrow_mesh"));
    if(Belt)
    {
        // Waist accessories follow the native world/owner body pose and share
        // the existing equipment transaction; weapon viewmodels never own them.
        const FString OwnerBelt=String(Object(Belt,TEXT("owner_body_meshes")),*OutfitRig);
        MeshPaths.Add(bLowerBody&&!OwnerBelt.IsEmpty()?OwnerBelt:PartMesh(Belt,TEXT("belt")));
        MaterialPaths.Add(String(Belt,TEXT("material")));
    }
    TArray<FSoftObjectPath> Paths;
    bool bLoaded=true;
    if(!QuiverArrowPath.IsEmpty())
    {Paths.AddUnique(FSoftObjectPath(QuiverArrowPath));bLoaded&=Cast<UStaticMesh>(FSoftObjectPath(QuiverArrowPath).ResolveObject())!=nullptr;}
    for(const FString& Path:MeshPaths)
    {if(Path.IsEmpty())return;Paths.AddUnique(FSoftObjectPath(Path));bLoaded&=Cast<USkeletalMesh>(FSoftObjectPath(Path).ResolveObject())!=nullptr;}
    for(const FString& Path:MaterialPaths)if(!Path.IsEmpty())
    {Paths.AddUnique(FSoftObjectPath(Path));bLoaded&=Cast<UMaterialInterface>(FSoftObjectPath(Path).ResolveObject())!=nullptr;}
    for(const FString& Path:ShirtViewMaterials)
    {Paths.AddUnique(FSoftObjectPath(Path));bLoaded&=Cast<UMaterialInterface>(FSoftObjectPath(Path).ResolveObject())!=nullptr;}
    for(const auto& Entry:BaseMaterialPaths)
    {Paths.AddUnique(FSoftObjectPath(Entry.Value));bLoaded&=Cast<UMaterialInterface>(FSoftObjectPath(Entry.Value).ResolveObject())!=nullptr;}
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
        Part->SetVisibility(false);
        // Owner skin/clothes consume the world body's buffer directly; the
        // display anchor never adds a second pose or a second IK correction.
        Part->SetLeaderPoseComponent(bLowerBody&&Source->LeaderPoseComponent.IsValid()?Source->LeaderPoseComponent.Get():Source);
        if(bLowerBody)
        {
            Part->SetHiddenInSceneCapture(true);
            Part->SetVisibleInRayTracing(false);
            Part->bAffectDynamicIndirectLighting=false;
        }
        Part->bUseAttachParentBound=true;Part->RegisterComponent();
        Part->SetComponentTickEnabled(false);
        if(I==1&&bUseShirtMesh&&bHasLegs&&String(Shirt,TEXT("cloth_simulation"))==TEXT("blue_mage_robe_v1"))
            FPSOutfitRobeCloth::Initialize(Part,bLowerBody&&Source->LeaderPoseComponent.IsValid()
                ?Cast<USkeletalMeshComponent>(Source->LeaderPoseComponent.Get()):Source);
        if(!MaterialPaths[I].IsEmpty())
            for(int32 M=0;M<Part->GetNumMaterials();++M)Part->SetMaterial(M,Cast<UMaterialInterface>(FSoftObjectPath(MaterialPaths[I]).ResolveObject()));
        if(I==0)for(const auto& Entry:BaseMaterialPaths)
            if(Entry.Key>=0&&Entry.Key<Part->GetNumMaterials())
                Part->SetMaterial(Entry.Key,Cast<UMaterialInterface>(FSoftObjectPath(Entry.Value).ResolveObject()));
        if(I==1&&bUseShirtMesh)
        {
            for(int32 M=0;M<FMath::Min(Part->GetNumMaterials(),ShirtViewMaterials.Num());++M)
                Part->SetMaterial(M,Cast<UMaterialInterface>(FSoftObjectPath(ShirtViewMaterials[M]).ResolveObject()));
            if(bLowerBody)
            {
                const auto HiddenByRig=Object(Shirt,TEXT("owner_body_hidden_materials"));
                const auto Hidden=Numbers(HiddenByRig,*String(Profile,TEXT("rig_profile")));
                const auto* Data=Part->GetSkeletalMeshAsset()->GetResourceForRendering();
                if(Data)for(int32 L=0;L<Data->LODRenderData.Num();++L)for(int32 M:Hidden)Section(Part,M,L,false);
            }
        }
        NewParts.Add(Part);
    }
    // Cover the body only once the entire mesh/material recipe is resident.
    auto* Base=NewParts[0].Get();const auto* BaseData=Base->GetSkeletalMeshAsset()->GetResourceForRendering();
    TArray<int32> Covered=Numbers(Profile,TEXT("base_hide_materials"));
    if(bLowerBody)Covered.Append(Numbers(Profile,TEXT("owner_body_hidden_materials")));
    // Continuous robe inner legs extend through the thigh. The robe's broad
    // torso/hip coverage still hides original sections, but must not delete
    // their separately partitioned leg surfaces when the hem rises.
    TArray<int32> RobeInnerCovered=Covered;
    if(Shirt)
    {
        // Short sleeves retain the native arms. Body coverage is independent
        // because its torso section does not exist on first-person profiles.
        const TCHAR* CoverageKey=bHasLegs&&Shirt->HasField(TEXT("world_covers"))?TEXT("world_covers"):TEXT("covers");
        const auto RigCoverage=bHasLegs?Object(Shirt,TEXT("rig_world_covers")):nullptr;
        const FString Rig=String(Profile,TEXT("rig_profile"));
        if(RigCoverage&&RigCoverage->HasField(Rig))Covered.Append(Numbers(RigCoverage,*Rig));
        else Covered.Append(Shirt->HasField(CoverageKey)?Numbers(Shirt,CoverageKey):Numbers(Profile,TEXT("shirt_covers")));
    }
    // Open-finger gloves keep the exposed skin sections in the assembled base.
    // Missing per-item coverage preserves the existing full-glove recipe.
    if(Gloves)
    {
        const auto GloveCoverage=Gloves->HasField(TEXT("covers"))?Numbers(Gloves,TEXT("covers")):Numbers(Profile,TEXT("glove_covers"));
        Covered.Append(GloveCoverage);RobeInnerCovered.Append(GloveCoverage);
    }
    for(const auto& Lower:{Pants,Shoes})if(Lower)
    {
        const auto RigCoverage=Object(Lower,TEXT("rig_world_covers"));
        const FString Rig=String(Profile,TEXT("rig_profile"));
        const auto LowerCoverage=RigCoverage&&RigCoverage->HasField(Rig)?Numbers(RigCoverage,*Rig):Numbers(Lower,TEXT("world_covers"));
        Covered.Append(LowerCoverage);RobeInnerCovered.Append(LowerCoverage);
    }
    if(BaseData)for(int32 L=0;L<BaseData->LODRenderData.Num();++L)for(const int32 M:Covered)Section(Base,M,L,false);
    if(Existing)ReleasePresentation(*Existing);
    else Existing=&Presentations.AddDefaulted_GetRef();
    Existing->Source=Source;Existing->SourceAsset=Source->GetSkeletalMeshAsset();Existing->Key=Key;Existing->bWorld=bWorld;
    Existing->Parts=MoveTemp(NewParts);Existing->HiddenMaterials=Numbers(Profile,TEXT("hide_source_materials"));
    if(QuiverSettings&&Existing->Parts.IsValidIndex(BeltIndex))
    {
        Existing->QuiverMotion=MakeShared<FFPSQuiverMotion>();
        auto* Leader=bLowerBody&&Source->LeaderPoseComponent.IsValid()?Cast<USkeletalMeshComponent>(Source->LeaderPoseComponent.Get()):Source;
        Existing->QuiverMotion->Initialize(Leader,Existing->Parts[BeltIndex],QuiverSettings,
            Cast<UStaticMesh>(FSoftObjectPath(QuiverArrowPath).ResolveObject()),bLowerBody);
    }
    if(bHasLegs&&WantsRobeStairSupport())
    {
        const TArray<int32> None;
        for(auto Part:Existing->Parts)if(Part&&Part->ComponentHasTag(TEXT("OutfitRobeDrape")))
        {
            Existing->RobeHem=MakeShared<FFPSRobeHemEnvelope>();
            Existing->RobeHem->Initialize(Part);
            // The default cloth completion/writeback runs in LastDemotable,
            // after our PostUpdateWork tick. Reading earlier sees an empty or
            // previous-frame cache, especially visible during planted turns.
            // Tick prerequisites defer only this actor's presentation until
            // its pose and cloth cache are the same ones sent for rendering.
            // ClothTick covers the in-tick wait mode; ClothEndTick covers the
            // normal asynchronous mode. Inactive tick functions are skipped.
            PrimaryComponentTick.AddPrerequisite(Part,Part->PrimaryComponentTick);
            PrimaryComponentTick.AddPrerequisite(Part,Part->ClothTickFunction);
            PrimaryComponentTick.AddPrerequisite(Part,Part->ClothEndTickFunction);
            break;
        }
        for(int32 I=0;I<Existing->Parts.Num();++I)
        {
            FFPSRobeStairSections Sections;
            Sections.Initialize(Existing->Parts[I],I==0?RobeInnerCovered:None);
            if(!Sections.Sections.IsEmpty())
            {Sections.Apply(bHideRobeCalves);Existing->StairSections.Add(MoveTemp(Sections));}
        }
    }
    const FString SecondaryStyle=String(Shirt,TEXT("secondary_motion"));
    const bool bRobeCuffs=SecondaryStyle==TEXT("robe_shared_sway_v1");
    if(!bHasLegs&&Shirt&&(bRobeCuffs||SecondaryStyle==TEXT("chainmail_shared_sway_v1"))&&Existing->Parts.IsValidIndex(1))
    {
        Existing->SecondaryMotion=MakeShared<FFPSOutfitSecondaryMotion>();
        Existing->SecondaryMotion->Initialize(Source,Existing->Parts[1],bRobeCuffs);
        AddTickPrerequisiteComponent(Source);
    }
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
    // Keep enough geometry around the shared bare-finger/leather boundary.
    // Aggressive 20% reduction folds the narrow opening lip into the skin.
    const bool bFingerlessAssembly=Mesh->GetMaterials().ContainsByPredicate([](const FSkeletalMaterial& Material)
    {
        return Material.MaterialSlotName==TEXT("FingerlessGloveLeather");
    });
    Mesh->Modify();
    while(Mesh->GetLODNum()<3)Mesh->AddLODInfo();
    for(int32 L=1;L<3;++L)
    {
        auto& Info=*Mesh->GetLODInfo(L);Info.BuildSettings=Build;
        Info.ScreenSize.Default=L==1?.18f:.075f;Info.LODHysteresis=.015f;
        auto& R=Info.ReductionSettings;R.BaseLOD=0;R.TerminationCriterion=SMTC_NumOfTriangles;
        R.NumOfTrianglesPercentage=L==1?.5f:(bFingerlessAssembly?.35f:.2f);R.MaxBonesPerVertex=8;
        R.bRecalcNormals=false;R.bEnforceBoneBoundaries=true;R.bLockEdges=true;R.bLockColorBounaries=true;
        Info.bHasBeenSimplified=true;
    }
    Mesh->MarkPackageDirty();return true;
#else
    return false;
#endif
}
