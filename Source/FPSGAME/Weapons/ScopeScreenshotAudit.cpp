// Explicit screenshot-only review. Uses a private profile and never runs by default.
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Materials/MaterialInterface.h"
#include "Components/SkeletalMeshComponent.h"
#include "PhysicalScopeView.h"
#include "WeaponBipodDeploymentComponent.h"
#include "PKMBipodComponent.h"
#include "Components/BoxComponent.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"
#include "Bow/PeakwatchCoverageAudit.inl"
#include "../Monsters/FatZombie.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "ThermalScopeReview.inl"

namespace ScopeScreenshotAudit
{
struct FCase {const TCHAR* Name;const TCHAR* Weapon;const TCHAR* Slot;const TCHAR* Optic;float Zoom;int32 Loadout=-1;bool Motion=false;};
const FCase DefaultCases[]={
    {TEXT("01_m24_hip"),TEXT("ue_m24"),TEXT("optic"),TEXT("m24_custom_scope_6x"),0},
    {TEXT("02_m24_factory_6x"),TEXT("ue_m24"),TEXT("optic"),TEXT("m24_custom_scope_6x"),6},
    {TEXT("03_m24_upper_1x"),TEXT("ue_m24"),TEXT("optic"),TEXT("m24_custom_scope_6x"),1},
    {TEXT("04_m24_prism_2x"),TEXT("ue_m24"),TEXT("optic"),TEXT("prism_scope_2x"),2},
    {TEXT("05_m24_lpvo_1x"),TEXT("ue_m24"),TEXT("optic"),TEXT("lpvo_1_6x"),1},
    {TEXT("06_m24_lpvo_4x"),TEXT("ue_m24"),TEXT("optic"),TEXT("lpvo_1_6x"),4},
    {TEXT("07_m24_lpvo_6x"),TEXT("ue_m24"),TEXT("optic"),TEXT("lpvo_1_6x"),6},
    {TEXT("08_m24_kv_1x"),TEXT("ue_m24"),TEXT("optic"),TEXT("kv_scope_4x"),1},
    {TEXT("09_m24_kv_4x"),TEXT("ue_m24"),TEXT("optic"),TEXT("kv_scope_4x"),4},
    {TEXT("10_m24_thermal_1p5x"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),1.5},
    {TEXT("11_m24_thermal_8x"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),8},
    {TEXT("12_svd_pso_4x"),TEXT("ue_svd"),TEXT("optic"),TEXT("false"),4},
    {TEXT("13_akm_pso_4x"),TEXT("ue_akm"),TEXT("optic"),TEXT("pso1_4x"),4},
    {TEXT("14_dw715_2x"),TEXT("ue_dan_wesson715"),TEXT("optic"),TEXT("dw715_handgun_scope_2x"),2},
    {TEXT("15_bow_farwatch_4x"),TEXT("bow_woodsteel"),TEXT("sight"),TEXT("bow_farwatch_4x"),4},
    {TEXT("16_bow_peakwatch_3x"),TEXT("bow_woodsteel"),TEXT("sight"),TEXT("highland_peakwatch_3_6x"),3},
    {TEXT("17_bow_peakwatch_6x"),TEXT("bow_woodsteel"),TEXT("sight"),TEXT("highland_peakwatch_3_6x"),6},
    {TEXT("18_bow_clearfield_2x"),TEXT("bow_dark"),TEXT("sight"),TEXT("bow_clearfield_2x"),2},
    {TEXT("19_svch_kv_4x"),TEXT("ue_svch"),TEXT("optic"),TEXT("kv_scope_4x"),4}
};
const FCase M249Cases[]={
    {TEXT("01_m249_lpvo_1x"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),1},
    {TEXT("02_m249_lpvo_6x"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,-1,true},
    {TEXT("03_m249_kv_4x"),TEXT("ue_m249"),TEXT("optic"),TEXT("kv_scope_4x"),4,-1,true},
    {TEXT("04_m249_factory"),TEXT("ue_m249"),TEXT("optic"),TEXT("false"),1,-1,true},
    {TEXT("05_m249_holographic"),TEXT("ue_m249"),TEXT("optic"),TEXT("holographic"),1,-1,true},
    {TEXT("06_m249_eoth"),TEXT("ue_m249"),TEXT("optic"),TEXT("eoth_holographic"),1,-1,true},
    {TEXT("07_m249_panoramic"),TEXT("ue_m249"),TEXT("optic"),TEXT("panoramic_red_dot"),1,-1,true},
    {TEXT("08_m249_prism_2x"),TEXT("ue_m249"),TEXT("optic"),TEXT("prism_scope_2x"),2,-1,true},
    {TEXT("09_m249_kv_1x"),TEXT("ue_m249"),TEXT("optic"),TEXT("kv_scope_4x"),1},
    {TEXT("10_m249_thermal_1p5x"),TEXT("ue_m249"),TEXT("optic"),TEXT("thermal_scope"),1.5},
    {TEXT("11_m249_thermal_3x"),TEXT("ue_m249"),TEXT("optic"),TEXT("thermal_scope"),3},
    {TEXT("12_m249_thermal_8x"),TEXT("ue_m249"),TEXT("optic"),TEXT("thermal_scope"),8,-1,true},
    {TEXT("13_m249_parts_0"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,0},
    {TEXT("14_m249_parts_1"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,1},
    {TEXT("15_m249_parts_2"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,2},
    {TEXT("16_m249_parts_3"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,3},
    {TEXT("17_m249_parts_4"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6,4}
};
const FCase M249OutfitCases[]={
    {TEXT("01_outfit_prism_2x"),TEXT("ue_m249"),TEXT("optic"),TEXT("prism_scope_2x"),2},
    {TEXT("02_outfit_lpvo_6x"),TEXT("ue_m249"),TEXT("optic"),TEXT("lpvo_1_6x"),6},
    {TEXT("03_outfit_kv_4x"),TEXT("ue_m249"),TEXT("optic"),TEXT("kv_scope_4x"),4},
    {TEXT("04_outfit_thermal_8x"),TEXT("ue_m249"),TEXT("optic"),TEXT("thermal_scope"),8},
    {TEXT("05_outfit_holographic"),TEXT("ue_m249"),TEXT("optic"),TEXT("holographic"),1},
    {TEXT("06_outfit_eoth"),TEXT("ue_m249"),TEXT("optic"),TEXT("eoth_holographic"),1},
    {TEXT("07_outfit_panoramic"),TEXT("ue_m249"),TEXT("optic"),TEXT("panoramic_red_dot"),1},
    {TEXT("08_outfit_factory"),TEXT("ue_m249"),TEXT("optic"),TEXT("false"),1}
};
const FCase PSOCases[]={
    {TEXT("12_svd_pso_4x"),TEXT("ue_svd"),TEXT("optic"),TEXT("false"),4},
    {TEXT("13_akm_pso_4x"),TEXT("ue_akm"),TEXT("optic"),TEXT("pso1_4x"),4},
    {TEXT("20_rsh12_pso_4x"),TEXT("ue_rsh12"),TEXT("optic"),TEXT("pso1_4x"),4},
    {TEXT("21_a762_pso_4x"),TEXT("ue_a762"),TEXT("optic"),TEXT("pso1_4x"),4},
    {TEXT("22_pkm_pso_4x"),TEXT("ue_pkm_lowpoly"),TEXT("optic"),TEXT("pso1_4x"),4}
};
TConstArrayView<FCase> SelectedCases()
{
    if(ThermalScopeReview::Requested())
    {
        static const FCase ThermalCases[]={
            {TEXT("thermal_1p5x"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),1.5f},
            {TEXT("thermal_3x"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),3.f},
            {TEXT("thermal_8x"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),8.f},
            {TEXT("thermal_3x_dark"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),3.f},
            {TEXT("thermal_3x_bright"),TEXT("ue_m24"),TEXT("optic"),TEXT("thermal_scope"),3.f}};
        return MakeArrayView(ThermalCases);
    }
    if(FParse::Param(FCommandLine::Get(),TEXT("PSOGlassAudit")))return MakeArrayView(PSOCases);
    FString OutfitSource;
    if(FParse::Value(FCommandLine::Get(),TEXT("M249OpticEquipment="),OutfitSource))return MakeArrayView(M249OutfitCases);
    return FParse::Param(FCommandLine::Get(),TEXT("M249OpticObstruction"))
        ?MakeArrayView(M249Cases):MakeArrayView(DefaultCases);
}
struct FRun {FString Out;int32 Index=0,Phase=0;double At=0;bool Done=false,EntryShot=false;TWeakObjectPtr<AActor> Support;TArray<TSharedPtr<FJsonValue>> Rows;} Run;
void Write()
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("complete"),Run.Index==SelectedCases().Num());
    Root->SetArrayField(TEXT("screenshots"),Run.Rows);FString JSON;
    FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&JSON));
    FFileHelper::SaveStringToFile(JSON,*(Run.Out/TEXT("capture.json")));
}
void Capture(AFPSGAMECharacter* C,const FCase& Case,const TCHAR* Suffix)
{
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),FString(Case.Name)+Suffix+TEXT(".png"));
    Row->SetStringField(TEXT("weapon"),C->ActiveInventoryWeaponDefinition);Row->SetStringField(TEXT("optic"),C->GetGunsmithOpticVariant());
    Row->SetNumberField(TEXT("requested_zoom"),Case.Zoom);Row->SetNumberField(TEXT("actual_zoom"),C->GetOpticMagnification());
    Row->SetNumberField(TEXT("displayed_zoom"),C->GetDisplayedOpticMagnification());Row->SetNumberField(TEXT("scope_alpha"),C->GetScopePresentationAlpha());
    Row->SetBoolField(TEXT("aiming"),C->IsAiming());Row->SetNumberField(TEXT("camera_fov"),C->FirstPersonCamera->FieldOfView);
    Row->SetStringField(TEXT("camera_transform"),C->FirstPersonCamera->GetComponentTransform().ToString());
    if(ThermalScopeReview::Requested())
        ThermalScopeReview::Record(*Row,CastChecked<APlayerController>(C->GetController()));
    FPhysicalScopeView Physical;
    if(C->GetPhysicalScopeView(Physical))
    {
        Row->SetStringField(TEXT("physical_glass"),GetPathNameSafe(Physical.Mesh->GetMaterial(Physical.Glass)));
        Row->SetStringField(TEXT("physical_center"),Physical.Center.ToString());
        Row->SetStringField(TEXT("physical_mesh"),Physical.Mesh->GetComponentTransform().ToString());
        Row->SetNumberField(TEXT("glass_radius"),Physical.Radius.X);
        Row->SetStringField(TEXT("physical_forward"),Physical.Forward.ToString());
    }
    if(C->AKMViewmodel)
    {
        auto Sections=MakeShared<FJsonObject>();
        for(const TCHAR* Name:{TEXT("M249_OpticalHousing"),TEXT("M249_MagnifierGlass"),TEXT("M249_MagnifierReticle")})
        {
            const int32 Material=C->AKMViewmodel->GetMaterialIndex(Name);
            if(Material!=INDEX_NONE)Sections->SetBoolField(Name,C->AKMViewmodel->IsMaterialSectionShown(Material,0));
        }
        Row->SetObjectField(TEXT("factory_sections"),Sections);
    }
    if(auto* Optic=C->GetM24FactoryOptic())
    {
        Row->SetStringField(TEXT("glass_material"),GetPathNameSafe(Optic->GetMaterial(Optic->GetMaterialIndex(TEXT("M24_ScopeGlass")))));
        Row->SetBoolField(TEXT("owner_hidden"),Optic->bOwnerNoSee);
    }
    Row->SetNumberField(TEXT("loadout"),Case.Loadout);
    TArray<TSharedPtr<FJsonValue>> Meshes;
    TArray<USkeletalMeshComponent*> Skeletal;C->GetComponents(Skeletal);
    for(auto* Mesh:Skeletal)if(Mesh->IsVisible()&&!Mesh->bHiddenInGame&&Mesh->GetSkeletalMeshAsset())
        Meshes.Add(MakeShared<FJsonValueString>(GetPathNameSafe(Mesh->GetSkeletalMeshAsset())));
    Row->SetArrayField(TEXT("visible_skeletal_meshes"),Meshes);
    Row->SetNumberField(TEXT("bipod_blend"),C->BipodDeployment?C->BipodDeployment->GetDeploymentBlend():0.f);
    Row->SetBoolField(TEXT("bipod_deployed"),C->BipodDeployment&&C->BipodDeployment->IsDeployed());
    Run.Rows.Add(MakeShared<FJsonValueObject>(Row));Write();
    FScreenshotRequest::RequestScreenshot(Run.Out/(FString(Case.Name)+Suffix+TEXT(".png")),true,false);
}
void Tick(UWorld* World,ELevelTick,float)
{
    if(Run.Done||!World||World->WorldType!=EWorldType::Game||World->GetTimeSeconds()<4)return;
    auto* PC=World->GetFirstPlayerController();auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    if(!C)return;
    auto* Profile=World->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    if(!Profile||!Profile->IsAudit()||!Profile->ProfileSlot().Contains(TEXT("ScopeScreenshotAudit")))return;
    if(Run.Out.IsEmpty())
    {
        if(!FParse::Value(FCommandLine::Get(),TEXT("ScopeScreenshotOutput="),Run.Out))return;
        IFileManager::Get().MakeDirectory(*Run.Out,true);
        if(ThermalScopeReview::Requested())ThermalScopeReview::SetUp(World,C,PC);
    }
    const double Now=World->GetTimeSeconds();
    const auto Key=[&](EInputEvent Event){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,Event,Event==IE_Pressed?1.f:0.f));};
    const auto Cases=SelectedCases();
    if(Run.Index==Cases.Num())
    {
        Write();Run.Done=true;UE_LOG(LogTemp,Display,TEXT("SCOPE_SCREENSHOTS_COMPLETE count=%d"),Run.Rows.Num());
        FPlatformMisc::RequestExitWithStatus(false,0);return;
    }
    const auto& Case=Cases[Run.Index];
    if(Run.Phase==0)
    {
        Key(IE_Released);C->bMPAutoInputActive=true;
        if(Run.Support.IsValid()){Run.Support->Destroy();Run.Support.Reset();}
        Run.EntryShot=false;
        if(FParse::Param(FCommandLine::Get(),TEXT("M249OpticObstruction")))PC->SetControlRotation(FRotator(15.f,0.f,0.f));
        auto State=Profile->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);State.ActiveWeaponSlot=9;
        FString OutfitSource;
        if(FParse::Value(FCommandLine::Get(),TEXT("M249OpticEquipment="),OutfitSource))
        {
            TArray<uint8> Bytes;
            auto* Saved=FFileHelper::LoadFileToArray(Bytes,*OutfitSource)?Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromMemory(Bytes)):nullptr;
            if(!Saved){Run.Done=true;FPlatformMisc::RequestExitWithStatus(false,3);return;}
            for(const auto& Item:Saved->Profile.Items)if(Item.Place==1&&Item.Cell!=6&&Item.Cell!=9)State.Items.Add(Item);
        }
        auto Gun=Profile->CreateItem(Case.Weapon);Gun.Place=1;Gun.Cell=9;Gun.Magazine=5;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        if(!Data.IsValid())Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(Case.Slot,Case.Optic);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        if(Case.Loadout>=0)
        {
            const TCHAR* Stocks[]={TEXT("skeleton"),TEXT("core_stock"),TEXT("qr_performance"),TEXT("tactical_telescopic"),TEXT("legendary_adjustable_tactical_stock")};
            const TCHAR* Rear[]={TEXT("phantom_reargrip"),TEXT("stable_antislip_reargrip"),TEXT("balanced_reargrip")};
            const TCHAR* Front[]={TEXT("vertical_foregrip"),TEXT("tactical_vertical_foregrip"),TEXT("canted_foregrip"),TEXT("angled_foregrip"),TEXT("prism_handstop")};
            const TCHAR* Muzzle[]={TEXT("true"),TEXT("tactical_suppressor"),TEXT("brake"),TEXT("titanium_brake"),TEXT("multi_caliber_suppressor")};
            Parts->SetStringField(TEXT("stock"),Stocks[Case.Loadout]);Parts->SetStringField(TEXT("reargrip"),Rear[Case.Loadout%3]);
            Parts->SetStringField(TEXT("underbarrel"),Front[Case.Loadout]);Parts->SetStringField(TEXT("muzzle"),Muzzle[Case.Loadout]);
        }
        Gun.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));State.Items.Add(Gun);
        if(!Profile->CommitState(State)){Run.Done=true;FPlatformMisc::RequestExitWithStatus(false,2);return;}
        Run.At=Now;Run.Phase=1;
        UE_LOG(LogTemp,Display,TEXT("SCOPE_SCREENSHOT_BEGIN %s"),Case.Name);return;
    }
    if(Run.Phase==1&&Now-Run.At>8)
    {
        if(Case.Zoom>0)Key(IE_Pressed);
        Run.At=Now;Run.Phase=2;return;
    }
    if(Run.Phase==2&&Case.Motion&&!Run.EntryShot&&Now-Run.At>.16&&!FScreenshotRequest::IsScreenshotRequested())
    {
        Capture(C,Case,TEXT("_entry"));Run.EntryShot=true;return;
    }
    if(Run.Phase==2&&Now-Run.At>1.5)
    {
        if(ThermalScopeReview::Requested()&&Run.Index>=3)
        {
            auto& Exposure=C->FirstPersonCamera->PostProcessSettings;
            Exposure.bOverride_AutoExposureBias=true;
            Exposure.AutoExposureBias=Run.Index==3?-2.f:2.f;
        }
        if(Case.Zoom>0)
        {
            if(FString(Case.Optic)==TEXT("lpvo_1_6x"))C->SetLPVOMagnification(Case.Zoom);
            else for(int32 I=0;I<10;++I)
            {
                const float Current=C->GetOpticMagnification();if(FMath::IsNearlyEqual(Current,Case.Zoom,.01f))break;
                if(!C->AdjustOpticMagnification(Case.Zoom>Current?1.f:-1.f))break;
            }
        }
        Run.At=Now;Run.Phase=3;return;
    }
    if(Run.Phase==3&&Now-Run.At>4&&!FScreenshotRequest::IsScreenshotRequested())
    {
        Capture(C,Case,TEXT(""));
        Run.At=Now;Run.Phase=4;return;
    }
    if(Run.Phase==4&&Now-Run.At>1&&!FScreenshotRequest::IsScreenshotRequested())
    {
        if(!Case.Motion)
        {
            ++Run.Index;
            // Keep the same glass, thermal proxy and pose for the full series.
            Run.Phase=ThermalScopeReview::Requested()?2:0;
            Run.At=Now;
            return;
        }
        if(auto* Bipod=C->FindComponentByClass<UPKMBipodComponent>())
        {
            const FTransform Camera=C->FirstPersonCamera->GetComponentTransform();
            const FTransform Level(FRotator(0,C->GetControlRotation().Yaw,0),C->GetMeleeAimTransform().GetLocation());
            const FVector A=Level.TransformPosition(Camera.InverseTransformPosition(Bipod->GetRestFootWorld(0)));
            const FVector B=Level.TransformPosition(Camera.InverseTransformPosition(Bipod->GetRestFootWorld(1)));
            auto* Support=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Support);
            Support->SetRootComponent(Box);Support->AddInstanceComponent(Box);
            Box->SetBoxExtent(FVector(35,30,5));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
            Box->SetCollisionResponseToAllChannels(ECR_Block);Box->SetWorldLocation((A+B)*.5-FVector(0,0,5.12));
            Box->RegisterComponent();Run.Support=Support;
            if(C->BipodDeployment)C->BipodDeployment->TryDeployFromADS();
        }
        Run.At=Now;Run.Phase=5;return;
    }
    if(Run.Phase==5&&Now-Run.At>4.5&&!FScreenshotRequest::IsScreenshotRequested())
    {Capture(C,Case,TEXT("_mounted"));Run.At=Now;Run.Phase=6;return;}
    if(Run.Phase==6&&Now-Run.At>1&&!FScreenshotRequest::IsScreenshotRequested())
    {Key(IE_Released);Run.At=Now;Run.Phase=7;return;}
    if(Run.Phase==7&&Now-Run.At>.2&&!FScreenshotRequest::IsScreenshotRequested())
    {Capture(C,Case,TEXT("_exit"));Run.At=Now;Run.Phase=8;return;}
    if(Run.Phase==8&&Now-Run.At>4.5&&!FScreenshotRequest::IsScreenshotRequested())
    {
        if(Run.Support.IsValid()){Run.Support->Destroy();Run.Support.Reset();}
        Key(IE_Pressed);Run.At=Now;Run.Phase=9;return;
    }
    if(Run.Phase==9&&Now-Run.At>3&&!FScreenshotRequest::IsScreenshotRequested())
    {Capture(C,Case,TEXT("_reaim"));Run.At=Now;Run.Phase=10;return;}
    if(Run.Phase==10&&Now-Run.At>1&&!FScreenshotRequest::IsScreenshotRequested()){++Run.Index;Run.Phase=0;}
}
struct FRegister
{
    FRegister(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){if(FParse::Param(FCommandLine::Get(),TEXT("ScopeScreenshotAudit")))
        FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);});}
} Register;
}
