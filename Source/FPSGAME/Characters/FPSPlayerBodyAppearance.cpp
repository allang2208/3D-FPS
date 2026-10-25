#include "FPSPlayerBodyComponent.h"
#include "FPSBodyOutfitResources.h"
#include "FPSPlayerHeadAnimInstance.h"
#include "FPSHeadEquipmentMeshComponent.h"
#include "FPSModularOutfitComponent.h"
#include "UObject/UnrealType.h"
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
void AssetPaths(const TSharedPtr<FJsonValue>& Value,TArray<FSoftObjectPath>& Out)
{
    if(!Value)return;
    if(Value->Type==EJson::String)
    {
        const FString Path=Value->AsString();
        if(Path.StartsWith(TEXT("/Game/"))||Path.StartsWith(TEXT("/Engine/")))Out.AddUnique(FSoftObjectPath(Path));
    }
    else if(Value->Type==EJson::Array)for(const auto& Child:Value->AsArray())AssetPaths(Child,Out);
    else if(Value->Type==EJson::Object)for(const auto& Child:Value->AsObject()->Values)
        if(Child.Key!=TEXT("body_variants"))AssetPaths(Child.Value,Out);
}
}

FFPSBodyAppearance UFPSPlayerBodyComponent::ResolveAppearance(FFPSBodyAppearance Value) const
{
    using namespace FPSBodyAppearance;
    const auto Selected=ConfigurationForHead(Value.HeadId);
    const auto Heads=Object(Selected,TEXT("heads"));
    if(!Object(Heads,Value.HeadId.ToString()))Value.HeadId=FName(*Text(Selected,TEXT("default_head")));
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
    const auto Selected=ConfigurationForHead(Value.HeadId);
    const bool bChangeBody=Selected!=Configuration;
    const auto Head=Object(Object(Selected,TEXT("heads")),Value.HeadId.ToString());
    if(!Head)return;
    const FString MeshPath=Text(Head,TEXT("mesh"));
    const auto MaterialOverrides=Object(Head,TEXT("materials"));
    TArray<TSharedPtr<FJsonObject>> GroomRecipes;Grooms(Head,GroomRecipes);
    const int32 ScalpStart=GroomRecipes.Num();
    Grooms(Object(Object(Head,TEXT("hair_styles")),Value.HairId.ToString()),GroomRecipes);
    TArray<FSoftObjectPath> Paths;Paths.Add(FSoftObjectPath(MeshPath));
    TMap<FName,FSoftObjectPath> Materials;
    if(MaterialOverrides)for(const auto& Pair:MaterialOverrides->Values)
    {FSoftObjectPath Path(Pair.Value->AsString());Paths.AddUnique(Path);Materials.Add(FName(*Pair.Key),Path);}
    for(const auto& Recipe:GroomRecipes)
    {Paths.AddUnique(FSoftObjectPath(Text(Recipe,TEXT("asset"))));Paths.AddUnique(FSoftObjectPath(Text(Recipe,TEXT("binding"))));
        AssetPaths(Recipe->TryGetField(TEXT("materials")),Paths);}
    if(bChangeBody)
    {
        for(const auto& Entry:BodyConfigurations)if(Entry.Value==Selected)
            if(auto* Modular=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>())
                Modular->CollectBodyAssets(Entry.Key,Text(Selected,TEXT("body_mesh")),Paths);
        for(const TCHAR* Key:{TEXT("body_mesh"),TEXT("weapon_pose_reference_mesh")})
            Paths.AddUnique(FSoftObjectPath(Text(Selected,Key)));
        if(const auto Clips=Object(Selected,TEXT("clips")))for(const auto& Clip:Clips->Values)AssetPaths(Clip.Value,Paths);
        const auto Outfits=Object(Selected,TEXT("outfits"));
        const auto Headwear=Object(Selected,TEXT("head_equipment"));
        const auto GatherWornRecipe=[&](const TArray<FFPSBodyOutfitSlot>& Slots,const FFPSBodyOutfitSlot& Slot)
        {
            if(!Outfits)return;
            const auto* Shirt=Slots.FindByPredicate([](const FFPSBodyOutfitSlot& Entry){return Entry.Slot==7;});
            TSet<FSoftObjectPath> SelectedPaths;
            FPSBodyOutfitResources::GatherOutfit(Outfits->TryGetField(Slot.Definition.ToString()),Shirt?Shirt->Definition:NAME_None,SelectedPaths);
            for(const auto& Path:SelectedPaths)Paths.AddUnique(Path);
        };
        for(const auto& Slot:LocalOutfit)
        {
            GatherWornRecipe(LocalOutfit,Slot);
            if(Headwear)AssetPaths(Headwear->TryGetField(Slot.Definition.ToString()),Paths);
        }
        for(const auto& Slot:ReplicatedOutfit)
        {
            GatherWornRecipe(ReplicatedOutfit,Slot);
            if(Headwear)AssetPaths(Headwear->TryGetField(Slot.Definition.ToString()),Paths);
        }
    }
    AppliedAppearance=Value;
    const uint32 Request=++AppearanceRequest;
    if(AppearanceLoad)AppearanceLoad->CancelHandle();
    AppearanceLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(Paths,
        FStreamableDelegate::CreateWeakLambda(this,[this,Value,Request,MeshPath,GroomRecipes,Materials,ScalpStart,Selected,bChangeBody,Paths]()
    {
        if(Request!=AppearanceRequest||!Character.IsValid())return;
        auto* Parent=GetBodyMesh();
        auto* Mesh=Cast<USkeletalMesh>(FSoftObjectPath(MeshPath).ResolveObject());
        if(!Parent||!Mesh){UE_LOG(LogTemp,Error,TEXT("Player head unavailable: %s"),*MeshPath);AppearanceLoad.Reset();AppliedAppearance={};return;}
        for(const auto& Path:Paths)if(Path.IsValid()&&!Path.ResolveObject())
        {UE_LOG(LogTemp,Error,TEXT("Player appearance unavailable: %s"),*Path.ToString());AppearanceLoad.Reset();AppliedAppearance={};return;}
        if(bChangeBody)
        {
            if(auto* Modular=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>())Modular->ResetBodyPresentation();
            if(FirstPersonLowerBody){FirstPersonLowerBody->DestroyComponent();FirstPersonLowerBody=nullptr;}
            bLowerBodyRequested=false;
            ClearHeadEquipment();ClearMotion();ClearFloatingBook();
            for(const auto& Original:OriginalMaterials)if(IsValid(Original.Key))
                for(int32 Index=0;Index<Original.Value.Materials.Num();++Index)
                    Original.Key->SetMaterial(Index,Original.Value.Materials[Index]);
            OriginalMaterials.Reset();
            // Cancel the old-rig load before replacing its skeletal leader.
            ClearOutfitPresentation();
            Parent->EmptyOverrideMaterials();
            DeathCameraTracks[0].Reset();DeathCameraTracks[1].Reset();
            Configuration=Selected;
            if(auto* Modular=GetOwner()->FindComponentByClass<UFPSModularOutfitComponent>())Modular->SetBodyType(GetBodyType());
            InitializeDeathPresentation();InitializeBody(false);
            RebuildWeapons(Character->IsLocallyControlled()?LocalWeapons:ReplicatedWeapons);
            ApplyOutfit(Character->IsLocallyControlled()?LocalOutfit:ReplicatedOutfit);
            RefreshEquipment();
        }
        UpdateHeadEquipment(HeadEquipmentDefinition);
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
        // The native body graph already animates the entire neck/head chain.
        // The stock face post-process also has a procedural head movement IK:
        // disable that second skeletal driver only, retaining facial RigLogic.
        if(auto* Post=HeadMesh->GetPostProcessInstance())
            if(auto* HeadIK=FindFProperty<FBoolProperty>(Post->GetClass(),TEXT("EnableHeadMovementIK")))
                HeadIK->SetPropertyValue_InContainer(Post,false);
        HeadMesh->VisibilityBasedAnimTickOption=EVisibilityBasedAnimTickOption::AlwaysTickPoseAndRefreshBones;
        TMap<FName,FLODMappingData> AuthoredGroomLODMapping;
        int32 GroomIndex=0;
        for(const auto& Recipe:GroomRecipes)
        {
            const bool Scalp=GroomIndex++>=ScalpStart;
            auto* Asset=Cast<UGroomAsset>(FSoftObjectPath(Text(Recipe,TEXT("asset"))).ResolveObject());
            auto* Binding=Cast<UGroomBindingAsset>(FSoftObjectPath(Text(Recipe,TEXT("binding"))).ResolveObject());
            if(!Asset||!Binding){UE_LOG(LogTemp,Error,TEXT("Player groom unavailable for %s"),*Value.HeadId.ToString());continue;}
            auto* Groom=NewObject<UGroomComponent>(GetOwner(),NAME_None,RF_Transient);
            if(Scalp)Groom->ComponentTags.Add(TEXT("HeadScalpHair"));
            GetOwner()->AddInstanceComponent(Groom);Groom->SetupAttachment(HeadMesh);
            Groom->SetGroomAsset(Asset,Binding,false);
            // MetaHuman assembly authors the local simulation frame separately
            // from the groom asset's per-group solver/constraint settings.
            if(const auto Setup=Object(Recipe,TEXT("simulation_setup")))
            {
                auto& NativeSetup=Groom->SimulationSettings.SimulationSetup;
                FString Bone;if(Setup->TryGetStringField(TEXT("local_bone"),Bone))NativeSetup.LocalBone=Bone;
                Setup->TryGetBoolField(TEXT("local_simulation"),NativeSetup.bLocalSimulation);
                double Linear=NativeSetup.LinearVelocityScale,Angular=NativeSetup.AngularVelocityScale;
                Setup->TryGetNumberField(TEXT("linear_velocity_scale"),Linear);
                Setup->TryGetNumberField(TEXT("angular_velocity_scale"),Angular);
                NativeSetup.LinearVelocityScale=Linear;NativeSetup.AngularVelocityScale=Angular;
            }
            const TArray<TSharedPtr<FJsonValue>>* GroomMaterials=nullptr;
            if(Recipe->TryGetArrayField(TEXT("materials"),GroomMaterials))
                for(int32 Index=0;Index<GroomMaterials->Num();++Index)
                    if(auto* Material=Cast<UMaterialInterface>(FSoftObjectPath((*GroomMaterials)[Index]->AsString()).ResolveObject()))
                        Groom->SetMaterial(Index,Material);
            bool Simulate=false;const bool HasSimulationPolicy=Recipe->TryGetBoolField(TEXT("simulate"),Simulate);
            if(Simulate){Groom->AddCollisionComponent(Parent);Groom->ComponentTags.Add(TEXT("BodyHairSimulation"));}
            else if(HasSimulationPolicy)
            {
                Groom->SimulationSettings.bOverrideSettings=true;
                Groom->SimulationSettings.SolverSettings.bEnableSimulation=false;
            }
            Groom->SetCollisionEnabled(ECollisionEnabled::NoCollision);Groom->SetGenerateOverlapEvents(false);
            Groom->RegisterComponent();Groom->AddTickPrerequisiteComponent(HeadMesh);HeadGrooms.Add(Groom);
            const TArray<TSharedPtr<FJsonValue>>* LODs=nullptr;
            if(Recipe->TryGetArrayField(TEXT("lod_mapping"),LODs))
            {
                FLODMappingData Mapping;for(const auto& LOD:*LODs)Mapping.Mapping.Add(static_cast<int32>(LOD->AsNumber()));
                AuthoredGroomLODMapping.Add(Groom->GetFName(),MoveTemp(Mapping));
            }
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
            const int32 GroomLODs=Groom->GetNumSyncLODs();
            const auto* Authored=AuthoredGroomLODMapping.Find(Groom->GetFName());
            const bool ValidAuthored=Authored&&Authored->Mapping.Num()==SyncLODs&&
                !Authored->Mapping.ContainsByPredicate([GroomLODs](int32 LOD){return LOD<0||LOD>=GroomLODs;});
            AppearanceLODSync->CustomLODMapping.Add(Groom->GetFName(),ValidAuthored?*Authored:Mapping(GroomLODs));
        }
        AppearanceLODSync->RegisterComponent();UpdateAppearanceVisibility();
        AppearanceLoad.Reset();
    }));
}
void UFPSPlayerBodyComponent::UpdateAppearanceVisibility()
{
    // Possession can arrive after appearance streaming. Recreate only on that
    // ownership transition so a joining owner also gets the optical layer.
    if(Character.IsValid()&&!HeadEquipmentKey.IsEmpty()&&
       HeadEquipmentKey.EndsWith(TEXT("|owner"))!=Character->IsLocallyControlled())
        UpdateHeadEquipment(HeadEquipmentDefinition);
    const auto* Body=GetBodyMesh();if(!Body)return;
    const bool Visible=Body->IsVisible()&&!Body->bHiddenInGame;
    TArray<UPrimitiveComponent*> Parts;if(HeadMesh)Parts.Add(HeadMesh);
    if(HeadEquipment)Parts.Add(HeadEquipment);
    for(auto Groom:HeadGrooms)if(Groom)Parts.Add(Groom);
    for(auto* Part:Parts)
    {
        const bool HideHead=Body->bOwnerNoSee||(IsDeathViewActive()&&!IsThirdPersonViewEnabled());
        FPSBodyEquipment::ApplyOwnerVisibilityFlags(Part,false,HideHead);
        FPSBodyEquipment::ApplyShadowFlags(Part,ShouldWorldBodyCastShadow());
        const bool PartVisible=Visible&&!(bHeadEquipmentCoversHair&&Part->ComponentHasTag(TEXT("HeadScalpHair")));
        if(Part->IsVisible()!=PartVisible)Part->SetVisibility(PartVisible);
        if(Part->bHiddenInGame==PartVisible)Part->SetHiddenInGame(!PartVisible);
        if(auto* Dynamic=Cast<UFPSHeadEquipmentMeshComponent>(Part))
            Dynamic->SetDynamicsVisible(PartVisible&&(!HideHead||!Character.IsValid()||!Character->IsLocallyControlled()||ShouldWorldBodyCastShadow()));
        // UE 5.8 pauses/resets groom Niagara on visibility transitions. Keep
        // native per-group physics; SetEnableSimulation requires full overrides
        // and otherwise only logs a warning without changing the simulation.
    }
    if(HeadMesh)HeadMesh->VisibilityBasedAnimTickOption=Body->VisibilityBasedAnimTickOption;
}
