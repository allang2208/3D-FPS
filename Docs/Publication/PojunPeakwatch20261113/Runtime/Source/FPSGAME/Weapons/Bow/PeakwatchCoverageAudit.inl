// Explicit, isolated offscreen review of the production Peakwatch ADS path.
#include "BowWeaponComponent.h"
#include "BowArmsMeshComponent.h"
#include "BowPartComponent.h"
#include "../PhysicalScopeView.h"
#include "../../FPSGAMECharacter.h"
#include "../../UI/ColdSteelStatusModel.h"
#include "Camera/CameraComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "HAL/FileManager.h"
#include "HAL/PlatformMisc.h"
#include "InputKeyEventArgs.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/CommandLine.h"
#include "Misc/CoreDelegates.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "SceneView.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/StrongObjectPtr.h"
#include "UnrealClient.h"

namespace PeakwatchCoverageAudit
{
enum class EAction { None,Aim,Draw,Release,Zoom,Mask,Picture,Exit };
struct FStep {const TCHAR* Name;EAction Action;float Delay;float Zoom=0;bool Full=false;};
const FStep Steps[]={
    {TEXT("01_ads_3x"),EAction::Aim,1.5f},
    {TEXT("02_drawing_3x"),EAction::Draw,1.f},
    {TEXT("03_full_3x"),EAction::None,1.5f,0,true},
    {TEXT("04_zoom_to_4p5"),EAction::Zoom,.08f,4.5f},
    {TEXT("05_full_4p5x"),EAction::None,.6f,0,true},
    {TEXT("06_zoom_to_6"),EAction::Zoom,.08f,6.f},
    {TEXT("07_full_6x"),EAction::None,.6f,0,true},
    {TEXT("08_mask_full_6x"),EAction::Mask,.12f,0,true},
    {TEXT("09_picture_full_6x"),EAction::Picture,.12f,0,true},
    {TEXT("10_release_6x_start"),EAction::Release,.035f},
    {TEXT("10b_mask_release_6x"),EAction::Mask,.035f},
    {TEXT("10c_picture_release_6x"),EAction::Picture,.035f},
    {TEXT("11_release_6x_mid"),EAction::None,.12f},
    {TEXT("12_release_6x_recover"),EAction::None,.28f},
    {TEXT("13_release_6x_settled"),EAction::None,.9f},
    {TEXT("14_zoom_back_3"),EAction::Zoom,.08f,3.f},
    {TEXT("15_ads_3x_restored"),EAction::None,.6f},
    {TEXT("16_drawing_again_3x"),EAction::Draw,1.f},
    {TEXT("17_full_again_3x"),EAction::None,1.5f,0,true},
    {TEXT("18_mask_full_3x"),EAction::Mask,.12f,0,true},
    {TEXT("19_picture_full_3x"),EAction::Picture,.12f,0,true},
    {TEXT("20_release_3x_start"),EAction::Release,.035f},
    {TEXT("20b_mask_release_3x"),EAction::Mask,.035f},
    {TEXT("20c_picture_release_3x"),EAction::Picture,.035f},
    {TEXT("21_release_3x_recover"),EAction::None,.3f},
    {TEXT("22_release_3x_settled"),EAction::None,1.1f},
    {TEXT("23_exit_ads"),EAction::Exit,.15f},
    {TEXT("24_exit_settled"),EAction::None,.6f}
};
struct FRun
{
    FString Out;int32 Step=-1;double At=0,Started=0;bool Seeded=false,Entered=false,Done=false;
    TArray<TSharedPtr<FJsonValue>> Rows;
    TStrongObjectPtr<UTextureRenderTarget2D> Mask;
    TStrongObjectPtr<UTexture> Picture;
} Run;
void Write(bool Complete,const FString& Error=FString())
{
    auto Root=MakeShared<FJsonObject>();Root->SetBoolField(TEXT("complete"),Complete);
    Root->SetStringField(TEXT("error"),Error);Root->SetArrayField(TEXT("frames"),Run.Rows);
    FString Json;FJsonSerializer::Serialize(Root,TJsonWriterFactory<>::Create(&Json));
    FFileHelper::SaveStringToFile(Json,*(Run.Out/TEXT("capture.json")));
}
void Fail(const FString& Why)
{
    Write(false,Why);Run.Done=true;UE_LOG(LogTemp,Error,TEXT("PEAKWATCH_COVERAGE_FAILED %s"),*Why);
    FPlatformMisc::RequestExitWithStatus(false,2);
}
void Key(APlayerController* PC,FKey Key,EInputEvent Event)
{PC->InputKey(FInputKeyEventArgs::CreateSimulated(Key,Event,Event==IE_Pressed?1.f:0.f));}
void Sample(AFPSGAMECharacter* C,UBowWeaponComponent* Bow,const FStep& Step)
{
    auto Row=MakeShared<FJsonObject>();Row->SetStringField(TEXT("image"),FString(Step.Name)+TEXT(".png"));
    Row->SetNumberField(TEXT("world_seconds"),C->GetWorld()->GetTimeSeconds());
    Row->SetNumberField(TEXT("draw"),Bow->DrawFraction());Row->SetNumberField(TEXT("stage"),int32(Bow->GetStage()));
    Row->SetNumberField(TEXT("requested_zoom"),Bow->ScopeMagnification());
    Row->SetNumberField(TEXT("displayed_zoom"),Bow->DisplayedScopeMagnification());
    Row->SetNumberField(TEXT("aim"),Bow->AimAlpha());
    auto* Camera=C->FirstPersonCamera.Get();Row->SetNumberField(TEXT("world_fov"),Camera->FieldOfView);
    Row->SetNumberField(TEXT("viewmodel_fov"),Camera->FirstPersonFieldOfView);
    Row->SetBoolField(TEXT("first_person_enabled"),Camera->bEnableFirstPersonFieldOfView);
    Row->SetStringField(TEXT("camera"),Camera->GetComponentTransform().ToString());
    auto* PC=Cast<APlayerController>(C->GetController());auto* Local=PC->GetLocalPlayer();
    FSceneViewProjectionData Projection;FPhysicalScopeView Optic;
    if(Bow->GetPhysicalScopeView(Optic))
    {
        Row->SetStringField(TEXT("mesh"),Bow->PartMeshPath(TEXT("sight")));
        Row->SetStringField(TEXT("lens_center"),Optic.Center.ToString());
        if(auto* Lens=Cast<UMaterialInstanceDynamic>(Optic.Mesh->GetMaterial(Optic.Glass)))
        {
            Row->SetStringField(TEXT("material_parent"),GetPathNameSafe(Lens->Parent));
            Row->SetNumberField(TEXT("lens_blend"),Lens->K2_GetScalarParameterValue(TEXT("LensBlend")));
            Row->SetNumberField(TEXT("reticle_style"),Lens->K2_GetScalarParameterValue(TEXT("ReticleStyle")));
            Row->SetNumberField(TEXT("capture_tan_half_fov"),Lens->K2_GetScalarParameterValue(TEXT("CaptureTanHalfFOV")));
            Row->SetBoolField(TEXT("coverage_mask"),Lens->K2_GetTextureParameterValue(TEXT("ScopeScene"))==Run.Mask.Get());
        }
        if(Local&&Local->ViewportClient&&Local->ViewportClient->Viewport&&Local->GetProjectionData(Local->ViewportClient->Viewport,Projection))
        {
            const FIntRect Rect=Projection.GetConstrainedViewRect();const FMatrix VP=Projection.ComputeViewProjectionMatrix();
            const FVector2D ScreenCenter(Rect.Min.X+Rect.Width()*.5,Rect.Min.Y+Rect.Height()*.5);
            const double Factor=Camera->bEnableFirstPersonFieldOfView
                ?FMath::Tan(FMath::DegreesToRadians(Camera->FieldOfView)*.5)/FMath::Tan(FMath::DegreesToRadians(Camera->FirstPersonFieldOfView)*.5):1.;
            TArray<TSharedPtr<FJsonValue>> Boundary;
            for(int32 I=0;I<64;++I)
            {
                const double A=2.*PI*I/64.;FVector2D Pixel;
                if(FSceneView::ProjectWorldToScreen(Optic.Center+Optic.Right*(FMath::Cos(A)*Optic.Radius.X)+Optic.Up*(FMath::Sin(A)*Optic.Radius.Y),Rect,VP,Pixel))
                {
                    Pixel=ScreenCenter+(Pixel-ScreenCenter)*Factor;
                    TArray<TSharedPtr<FJsonValue>> Point={MakeShared<FJsonValueNumber>(Pixel.X),MakeShared<FJsonValueNumber>(Pixel.Y)};
                    Boundary.Add(MakeShared<FJsonValueArray>(Point));
                }
            }
            Row->SetArrayField(TEXT("projected_lens_boundary"),Boundary);
        }
    }
    Run.Rows.Add(MakeShared<FJsonValueObject>(Row));Write(false);
    FScreenshotRequest::RequestScreenshot(Run.Out/(FString(Step.Name)+TEXT(".png")),true,false);
    UE_LOG(LogTemp,Display,TEXT("PEAKWATCH_FRAME %s draw=%.3f zoom=%.3f stage=%d"),Step.Name,Bow->DrawFraction(),Bow->DisplayedScopeMagnification(),int32(Bow->GetStage()));
}
void Tick(UWorld* W,ELevelTick,float)
{
    if(Run.Done||!W||W->WorldType!=EWorldType::Game||W->GetTimeSeconds()<4)return;
    auto* PC=W->GetFirstPlayerController();auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;
    auto* P=W->GetGameInstance()?W->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    if(!C||!P||!P->IsAudit()||!P->ProfileSlot().Contains(TEXT("PeakwatchCoverageAudit")))return;
    if(Run.Out.IsEmpty())
    {
        if(!FParse::Value(FCommandLine::Get(),TEXT("PeakwatchCoverageOutput="),Run.Out))return;
        IFileManager::Get().MakeDirectory(*Run.Out,true);Run.Started=FPlatformTime::Seconds();
    }
    if(FPlatformTime::Seconds()-Run.Started>180){Fail(TEXT("Runtime fixture timed out"));return;}
    auto* Bow=C->FindComponentByClass<UBowWeaponComponent>();if(!Bow)return;
    const double Now=W->GetTimeSeconds();
    if(!Run.Seeded)
    {
        C->bMPAutoInputActive=true;PC->SetControlRotation(FRotator::ZeroRotator);
        C->GetCharacterMovement()->StopMovementImmediately();C->GetCharacterMovement()->DisableMovement();
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        S.ActiveWeaponSlot=9;S.ActiveProductionTool.Reset();S.DungeonRun={};
        auto Item=P->CreateItem(TEXT("bow_woodsteel"));Item.Place=1;Item.Cell=9;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data),Data);
        if(!Data)Data=MakeShared<FJsonObject>();
        auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("sight"),TEXT("highland_peakwatch_3_6x"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);
        Item.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Item.Data));
        S.Items.Add(Item);S.AmmoPouch.Add(P->AmmoDefinitionFor(Item),100);
        if(!P->CommitState(S)){Fail(TEXT("Isolated profile rejected: ")+P->ResultMessage());return;}
        Run.Seeded=true;Run.At=Now;return;
    }
    if(Run.Step<0)
    {
        auto* Sight=Bow->FindPart(TEXT("sight"));
        if(Now-Run.At<15||!Bow->IsEquipped()||Bow->GetStage()!=EBowStage::Ready||!Sight||!Sight->HasMesh()
            ||!Bow->ArmsMesh()||!Bow->ArmsMesh()->IsVisible())return;
        Run.Step=0;
    }
    if(Run.Step==UE_ARRAY_COUNT(Steps))
    {
        if(FScreenshotRequest::IsScreenshotRequested()||Now-Run.At<.5)return;
        Write(true);Run.Done=true;UE_LOG(LogTemp,Display,TEXT("PEAKWATCH_COVERAGE_COMPLETE frames=%d"),Run.Rows.Num());
        FPlatformMisc::RequestExitWithStatus(false,0);return;
    }
    const auto& Step=Steps[Run.Step];
    if(!Run.Entered)
    {
        if(FScreenshotRequest::IsScreenshotRequested())return;
        switch(Step.Action)
        {
        case EAction::Aim:Key(PC,EKeys::RightMouseButton,IE_Pressed);break;
        case EAction::Draw:Key(PC,EKeys::LeftMouseButton,IE_Pressed);break;
        case EAction::Release:Key(PC,EKeys::LeftMouseButton,IE_Released);break;
        case EAction::Exit:Key(PC,EKeys::RightMouseButton,IE_Released);break;
        case EAction::Zoom:
            for(int32 I=0;I<6&&!FMath::IsNearlyEqual(Bow->ScopeMagnification(),Step.Zoom,.01f);++I)
                C->AdjustOpticMagnification(FMath::Clamp(Step.Zoom-Bow->ScopeMagnification(),-.5f,.5f));
            break;
        case EAction::Mask:case EAction::Picture:
        {
            FPhysicalScopeView Optic;
            auto* Lens=Bow->GetPhysicalScopeView(Optic)?Cast<UMaterialInstanceDynamic>(Optic.Mesh->GetMaterial(Optic.Glass)):nullptr;
            if(!Lens){Fail(TEXT("Production lens MID unavailable"));return;}
            if(Step.Action==EAction::Mask)
            {
                Run.Picture.Reset(Lens->K2_GetTextureParameterValue(TEXT("ScopeScene")));
                if(!Run.Mask.IsValid())
                {
                    Run.Mask.Reset(NewObject<UTextureRenderTarget2D>(GetTransientPackage()));
                    Run.Mask->RenderTargetFormat=RTF_RGBA16f;Run.Mask->ClearColor=FLinearColor(0,1,0,1);
                    Run.Mask->InitAutoFormat(32,32);Run.Mask->UpdateResourceImmediate(true);
                }
                Lens->SetTextureParameterValue(TEXT("ScopeScene"),Run.Mask.Get());
            }
            else Lens->SetTextureParameterValue(TEXT("ScopeScene"),Run.Picture.Get());
            break;
        }
        default:break;
        }
        Run.Entered=true;Run.At=Now;return;
    }
    if(Now-Run.At<Step.Delay||FScreenshotRequest::IsScreenshotRequested())return;
    if(Step.Full&&Bow->GetStage()!=EBowStage::Holding)
    {if(Now-Run.At>8)Fail(FString(TEXT("Full draw was not reached: "))+Step.Name);return;}
    Sample(C,Bow,Step);++Run.Step;Run.Entered=false;Run.At=Now;
}
struct FRegister
{
    FRegister(){FCoreDelegates::GetOnPostEngineInit().AddLambda([](){
        if(FParse::Param(FCommandLine::Get(),TEXT("PeakwatchCoverageAudit")))FWorldDelegates::OnWorldPostActorTick.AddStatic(&Tick);
    });}
} Register;
}
