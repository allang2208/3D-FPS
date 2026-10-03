#include "TangDaoRuneDiagnosisCommandlet.h"
#include "ModularSwordVisual.h"
#include "../UI/ColdSteelInventoryTypes.h"
#include "AssetCompilingManager.h"
#include "Components/StaticMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "Misc/FileHelper.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Serialization/JsonSerializer.h"

int32 UTangDaoRuneDiagnosisCommandlet::Main(const FString& Params)
{
    FString Text;
    TSharedPtr<FJsonObject> Catalog;
    if(!FFileHelper::LoadFileToString(Text,*(FPaths::ProjectContentDir()/TEXT("ColdSteelData/tang-dao-modules.json"))) ||
        !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Catalog) || !Catalog)return 1;

    const auto Settings=UWorld::InitializationValues().AllowAudioPlayback(false).CreatePhysicsScene(false)
        .RequiresHitProxies(false).CreateNavigation(false).CreateAISystem(false).ShouldSimulatePhysics(false).SetTransactional(false);
    auto* World=UWorld::CreateWorld(EWorldType::EditorPreview,false,TEXT("TangDaoRuneDiagnosis"),nullptr,true,ERHIFeatureLevel::Num,&Settings);
    auto* Actor=World->SpawnActor<AActor>();
    auto* Blade=NewObject<UStaticMeshComponent>(Actor,NAME_None,RF_Transient);
    Actor->SetRootComponent(Blade);Actor->AddInstanceComponent(Blade);Blade->RegisterComponentWithWorld(World);
    FColdSteelItem Item;
    Item.Definition=TEXT("ue_tang_dao");
    Item.InstanceId=TEXT("TransientTangDaoRuneDiagnosis");
    Item.Data=TEXT("{\"modular_sword_catalog\":\"tang-dao-modules.json\"}");
    TArray<TSharedPtr<FJsonValue>> Rows;
    for(const auto& Variant:Catalog->GetObjectField(TEXT("slots"))->GetObjectField(TEXT("blade_1"))->Values)
        for(const FString Rune:{FString(TEXT("resonance_rune")),FString(TEXT("erosion_rune")),FString(TEXT("conduction_rune"))})
        {
            FGunsmithParts Draft;Draft.Add(TEXT("blade_1"),FString(*Variant.Key));Draft.Add(TEXT("blade_2"),Rune);
            auto Row=MakeShared<FJsonObject>();
            Row->SetStringField(TEXT("blade"),Variant.Key);Row->SetStringField(TEXT("rune"),Rune);
            Row->SetBoolField(TEXT("assembly_applied"),ColdSteelModularSword::Apply(Blade,Item,&Draft));
            FAssetCompilingManager::Get().FinishAllCompilation();
            if(UStaticMesh* Mesh=Blade->GetStaticMesh())
            {
                Row->SetStringField(TEXT("mesh"),Mesh->GetPathName());
#if WITH_EDITOR
                Row->SetBoolField(TEXT("nanite_setting"),Mesh->IsNaniteEnabled());
#endif
                Row->SetBoolField(TEXT("has_nanite_render_data"),Mesh->HasValidNaniteData());
            }
            Row->SetBoolField(TEXT("component_force_disable_nanite"),Blade->IsForceDisableNanite());
            auto* Base=Blade->GetMaterial(0);auto* Overlay=Blade->GetOverlayMaterial(true,0);
            Row->SetStringField(TEXT("base"),GetPathNameSafe(Base));
            Row->SetStringField(TEXT("base_name"),Base?Base->GetBaseMaterial()->GetName():FString());
            Row->SetStringField(TEXT("overlay"),GetPathNameSafe(Overlay));
            Row->SetStringField(TEXT("rune_draw"),Overlay?TEXT("overlay"):TEXT("blade_surface"));
            if(auto* MID=Cast<UMaterialInstanceDynamic>(Overlay?Overlay:Base))
            {
                Row->SetNumberField(TEXT("mode"),MID->K2_GetScalarParameterValue(TEXT("RuneMode")));
                Row->SetStringField(TEXT("dimensions"),MID->K2_GetVectorParameterValue(TEXT("Dimensions")).ToString());
                Row->SetStringField(TEXT("origin"),MID->K2_GetVectorParameterValue(TEXT("BladeOrigin")).ToString());
                Row->SetStringField(TEXT("axis"),MID->K2_GetVectorParameterValue(TEXT("BladeAxis")).ToString());
                Row->SetStringField(TEXT("mask"),GetPathNameSafe(MID->K2_GetTextureParameterValue(TEXT("RuneTexture"))));
            }
            Rows.Add(MakeShared<FJsonValueObject>(Row));
        }
    auto Report=MakeShared<FJsonObject>();Report->SetArrayField(TEXT("assemblies"),Rows);
    Report->SetBoolField(TEXT("gameplay_started"),false);Report->SetBoolField(TEXT("assets_saved"),false);
    FString Output=FPaths::ProjectSavedDir()/TEXT("TangDaoRuneDiagnosis.json");
    FParse::Value(*Params,TEXT("Out="),Output);
    FString Json;FJsonSerializer::Serialize(Report,TJsonWriterFactory<>::Create(&Json));
    const bool Written=FFileHelper::SaveStringToFile(Json,*Output);
    ColdSteelModularSword::Clear(Blade);World->DestroyWorld(false);
    UE_LOG(LogTemp,Display,TEXT("TANGDAO_RUNE_DIAGNOSIS %s"),*Output);
    return Written?0:1;
}
