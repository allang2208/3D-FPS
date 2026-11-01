// Explicit screenshot-only review. Uses a private profile and never runs by default.
#include "../FPSGAMECharacter.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Materials/MaterialInterface.h"
#include "Serialization/JsonSerializer.h"
#include "UnrealClient.h"

namespace ScopeScreenshotAudit
{
struct FCase {const TCHAR* Name;const TCHAR* Weapon;const TCHAR* Slot;const TCHAR* Optic;float Zoom;};
const FCase Cases[]={
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
    {TEXT("17_bow_peakwatch_6x"),TEXT("bow_woodsteel"),TEXT("sight"),TEXT("highland_peakwatch_3_6x"),6}
};
struct FRun {FString Out;int32 Index=0,Phase=0;double At=0;bool Done=false;TArray<TSharedPtr<FJsonValue>> Rows;} Run;
void Write()
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("complete"),Run.Index==UE_ARRAY_COUNT(Cases));
    Root->SetArrayField(TEXT("screenshots"),Run.Rows);FString JSON;
    FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&JSON));
    FFileHelper::SaveStringToFile(JSON,*(Run.Out/TEXT("capture.json")));
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
    }
    const double Now=World->GetTimeSeconds();
    const auto Key=[&](EInputEvent Event){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,Event,Event==IE_Pressed?1.f:0.f));};
    if(Run.Index==UE_ARRAY_COUNT(Cases))
    {
        Write();Run.Done=true;UE_LOG(LogTemp,Display,TEXT("SCOPE_SCREENSHOTS_COMPLETE count=%d"),Run.Rows.Num());
        FPlatformMisc::RequestExitWithStatus(false,0);return;
    }
    const auto& Case=Cases[Run.Index];
    if(Run.Phase==0)
    {
        Key(IE_Released);C->bMPAutoInputActive=true;
        auto State=Profile->Snapshot();State.Items.Reset();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);State.ActiveWeaponSlot=9;
        auto Gun=Profile->CreateItem(Case.Weapon);Gun.Place=1;Gun.Cell=9;Gun.Magazine=5;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        if(!Data.IsValid())Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(Case.Slot,Case.Optic);Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
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
    if(Run.Phase==2&&Now-Run.At>1.5)
    {
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
        auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),FString(Case.Name)+TEXT(".png"));
        Row->SetStringField(TEXT("weapon"),C->ActiveInventoryWeaponDefinition);Row->SetStringField(TEXT("optic"),C->GetGunsmithOpticVariant());
        Row->SetNumberField(TEXT("requested_zoom"),Case.Zoom);Row->SetNumberField(TEXT("actual_zoom"),C->GetOpticMagnification());
        Row->SetNumberField(TEXT("displayed_zoom"),C->GetDisplayedOpticMagnification());Row->SetNumberField(TEXT("scope_alpha"),C->GetScopePresentationAlpha());
        Row->SetBoolField(TEXT("aiming"),C->IsAiming());Row->SetNumberField(TEXT("camera_fov"),C->FirstPersonCamera->FieldOfView);
        if(auto* Optic=C->GetM24FactoryOptic())
        {
            Row->SetStringField(TEXT("glass_material"),GetPathNameSafe(Optic->GetMaterial(Optic->GetMaterialIndex(TEXT("M24_ScopeGlass")))));
            Row->SetBoolField(TEXT("owner_hidden"),Optic->bOwnerNoSee);
        }
        Run.Rows.Add(MakeShared<FJsonValueObject>(Row));Write();
        FScreenshotRequest::RequestScreenshot(Run.Out/(FString(Case.Name)+TEXT(".png")),true,false);
        Run.At=Now;Run.Phase=4;return;
    }
    if(Run.Phase==4&&Now-Run.At>1&&!FScreenshotRequest::IsScreenshotRequested()){++Run.Index;Run.Phase=0;}
}
struct FRegister
{
    FRegister(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){if(FParse::Param(FCommandLine::Get(),TEXT("ScopeScreenshotAudit")))
        FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);});}
} Register;
}
