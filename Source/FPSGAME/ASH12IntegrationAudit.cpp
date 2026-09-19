#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/PlayerController.h"
#include "InputKeyEventArgs.h"
#include "InputCoreTypes.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Weapons/ASH12WeaponAssets.h"
#include "FPSGAMEPlayerController.h"
#include "Weapons/GunsmithSystem.h"
#include "UI/M4GunsmithWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Engine/StaticMesh.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "TimerManager.h"
#include "StaticMeshResources.h"
#include "DistanceFieldAtlas.h"
#include "Weapons/ASH12AttachmentAssetTools.h"

// Still capture for the ASH-12 viewmodel: hip frame, then iron-sight ADS at
// several eye reliefs, so the shipped framing can be judged from real frames
// instead of a reconstruction.
void AFPSGAMECharacter::RunASH12IntegrationAudit()
{
    auto* P=GetGameInstance()?GetGameInstance()->GetSubsystem<UColdSteelStatusModel>():nullptr;
    auto* PC=Cast<APlayerController>(Controller);
    if(!P||!PC||!P->ProfileSlot().Contains(TEXT("ASH12SightAudit"))||GetWorld()->GetTimeSeconds()<5)return;
    // Targeted regression for the ASH bounds/drag failure; never touches a user profile.
    if(FParse::Param(FCommandLine::Get(),TEXT("ASH12PreviewFixAudit")))
    {
        static bool Started=false;if(Started)return;Started=true;
        auto* AuditPC=Cast<AFPSGAMEPlayerController>(PC);if(!AuditPC||!P->IsAudit())return;
        auto Counts=MakeShared<FIntPoint>(0,0);
        auto Check=[Counts](bool Good,const FString& Name){++Counts->X;if(!Good)++Counts->Y;UE_LOG(LogTemp,Display,TEXT("ASH_PREVIEW_FIX: %s %s"),Good?TEXT("PASS"):TEXT("FAIL"),*Name);};
        auto Panel=[this](){TArray<UUserWidget*> Widgets;UWidgetBlueprintLibrary::GetAllWidgetsOfClass(this,Widgets,UM4GunsmithWidget::StaticClass(),true);return Widgets.IsEmpty()?nullptr:Cast<UM4GunsmithWidget>(Widgets[0]);};
        auto Later=[this](float T,TFunction<void()> F){FTimerHandle H;GetWorldTimerManager().SetTimer(H,[F](){F();},T,false);};
        auto Equip=[P,Check](const TCHAR* Id)
        {
            auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);S.ActiveWeaponSlot=9;
            auto Rifle=P->CreateItem(Id);Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=20;S.Items.Add(Rifle);
            Check(P->CommitState(S),FString(TEXT("isolated equip "))+Id);
        };
        const FString Dir=FPaths::ProjectSavedDir()/TEXT("ASH12PreviewFix");IFileManager::Get().MakeDirectory(*Dir,true);
        auto Shot=[Dir](const FString& Name){FScreenshotRequest::RequestScreenshot(Dir/Name,true,false);};
        auto Fit=[this,Panel,Check](const FString& Name)
        {
            auto* W=Panel();if(!W){Check(false,Name+TEXT(" panel"));return;}
            UpdateGunsmithCapture(W->Capture,false);W->SyncStudioPreview();
            Check(W->PreviewFramingBounds.IsValid&&!W->PreviewFramingBounds.GetCenter().ContainsNaN()&&W->PreviewFramingBounds.GetSize().GetAbsMax()<300.,Name+TEXT(" finite assembled bounds"));
            Check(FMath::IsFinite(W->Capture->OrthoWidth)&&W->Capture->OrthoWidth>30&&W->Capture->OrthoWidth<350,Name+TEXT(" usable framing width"));
            int32 Count=0;
            for(const auto& Pair:W->StudioCopies)if(auto* Mesh=Cast<UStaticMeshComponent>(Pair.Value);Mesh&&Mesh->IsVisible())
            {
                const UStaticMesh* Asset=Mesh->GetStaticMesh();if(!Asset)continue;const auto B=Asset->GetBounds();
                if(Asset->GetPathName().Contains(TEXT("/UniversalAttachments20260919/")))
                {
                    Check(!UASH12AttachmentAssetTools::IsRuntimeFastBuild(Mesh->GetStaticMesh()),Name+TEXT(" imported mesh build mode ")+Asset->GetName());
                    ++Count;Check(!B.Origin.ContainsNaN()&&!B.BoxExtent.ContainsNaN()&&B.BoxExtent.GetMin()>.01&&B.BoxExtent.GetAbsMax()<30&&B.SphereRadius>.1&&B.SphereRadius<40,Name+TEXT(" mesh bounds ")+Asset->GetName());
                    Check(Mesh->GetComponentScale().Equals(FVector::OneVector,.005),Name+TEXT(" physical scale ")+Asset->GetName());
                    if(const auto* Render=Asset->GetRenderData())
                    {
                        const auto RB=Render->Bounds;
                        Check(RB.Origin.Equals(B.Origin,.02)&&RB.BoxExtent.Equals(B.BoxExtent,.02)&&FMath::IsFinite(RB.SphereRadius)&&RB.SphereRadius>.01,Name+TEXT(" rebuilt render bounds ")+Asset->GetName());
                        if(!Render->LODResources.IsEmpty())if(const auto* DF=Render->LODResources[0].DistanceFieldData)
                        {
                            const auto DB=DF->LocalSpaceMeshBounds;
                            // Distance-field coordinates are floats; permit 0.01 mm
                            // conversion rounding against the double-precision box.
                            const float Gap=FMath::Max3(0.f,(DB.Min-FVector3f(B.Origin-B.BoxExtent)).GetMax(),(FVector3f(B.Origin+B.BoxExtent)-DB.Max).GetMax());
                            Check(DB.IsValid&&!DB.Min.ContainsNaN()&&!DB.Max.ContainsNaN()&&DB.GetSize().GetMin()>.01f&&DB.GetSize().GetAbsMax()<100.f&&Gap<=.001f,Name+TEXT(" distance field encloses mesh ")+Asset->GetName());
                            UE_LOG(LogTemp,Display,TEXT("ASH_PREVIEW_DF_ROUNDING_CM %s %.9g"),*Asset->GetName(),Gap);
                        }
                    }
                }
            }
            if(bUseASH12)Check(Count>=2,Name+TEXT(" optic and grip copied into capture"));
        };
        auto Drag=[Panel,Check](const FString& Name)
        {
            auto* W=Panel();if(!W){Check(false,Name+TEXT(" panel"));return;}
            W->SetSidePreview(true);auto Surface=W->GetPreviewSurface();if(!Surface){Check(false,Name+TEXT(" surface"));return;}
            auto& App=FSlateApplication::Get();auto Window=App.FindWidgetWindow(Surface.ToSharedRef());if(!Window){Check(false,Name+TEXT(" window"));return;}
            const auto G=Surface->GetCachedGeometry();const FVector2D Start=G.LocalToAbsolute(G.GetLocalSize()*.5f),End=G.LocalToAbsolute(G.GetLocalSize()*.5f+FVector2D(120,40));
            const TSet<FKey> None,Held{EKeys::LeftMouseButton};
            App.ProcessMouseMoveEvent(FPointerEvent(0,Start,Start,None,FKey(),0,FModifierKeysState()),false);
            App.ProcessMouseButtonDownEvent(Window->GetNativeWindow(),FPointerEvent(0,Start,Start,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));
            Check(Surface->HasMouseCapture(),Name+TEXT(" drag captures pointer"));
            App.ProcessMouseMoveEvent(FPointerEvent(0,End,Start,Held,FKey(),0,FModifierKeysState()),false);
            App.ProcessMouseButtonUpEvent(FPointerEvent(0,End,End,None,EKeys::LeftMouseButton,0,FModifierKeysState()));
            Check(W->GetPreviewOrbit().Equals(FVector2D(42,-14),.02),Name+TEXT(" drag applies matching yaw/pitch"));
            Check(!Surface->HasMouseCapture(),Name+TEXT(" release ends drag"));
            App.ProcessMouseWheelOrGestureEvent(FPointerEvent(0,End,End,None,FKey(),1,FModifierKeysState()),nullptr);
            Check(FMath::IsNearlyEqual(W->PreviewZoom,1.12f,.001f),Name+TEXT(" wheel zoom"));
            W->ZoomPreview(-1);
        };
        Equip(TEXT("ue_ash12"));
        Later(2,[AuditPC,Check](){Check(AuditPC->OpenGunsmith(),TEXT("open ASH workbench"));});
        const TCHAR* Optics[]={TEXT("holographic"),TEXT("panoramic_red_dot"),TEXT("prism_scope_2x"),TEXT("lpvo_1_6x")};
        const TCHAR* Grips[]={TEXT("vertical_foregrip"),TEXT("canted_foregrip"),TEXT("prism_handstop"),TEXT("angled_foregrip")};
        for(int32 I=0;I<4;++I)
        {
            const FString Optic=Optics[I],Grip=Grips[I];const float T=3.f+I*3.f;
            Later(T,[Panel,Optic,Grip](){if(auto* W=Panel()){W->SetSidePreview(true);W->ChooseOption(TEXT("optic"),Optic);W->ChooseOption(TEXT("underbarrel"),Grip);}});
            Later(T+1,[Fit,Optic](){Fit(Optic);});
            Later(T+1.5f,[Shot,I](){Shot(FString::Printf(TEXT("ash-pair-%d.png"),I));});
        }
        Later(15,[Panel](){if(auto* W=Panel())W->ChooseOption(TEXT("stock"),TEXT("ash12_cheek_rest"));});
        Later(16,[this,Check,Fit,Drag](){Check(StockAttachment&&StockAttachment->IsVisible(),TEXT("cheek rest mounted"));Fit(TEXT("ASH before drag"));Drag(TEXT("ASH"));});
        Later(17,[Fit,Shot](){Fit(TEXT("ASH after drag"));Shot(TEXT("ash-dragged.png"));});
        Later(18,[Panel,Check](){if(auto* W=Panel()){Check(W->GetPreviewOrbit().Equals(FVector2D(42,-14),.02),TEXT("ASH orbit persists between captures"));W->ChooseOption(TEXT("optic"),TEXT("false"));W->ChooseOption(TEXT("underbarrel"),TEXT("false"));W->ChooseOption(TEXT("stock"),TEXT("false"));}});
        Later(19,[this,Check,AuditPC,Equip](){Check(!HasVerticalForegrip()&&!HasPrismHandstop()&&(!HolographicOptic||!HolographicOptic->IsVisible())&&(!StockAttachment||!StockAttachment->IsVisible()),TEXT("remove ASH attachments"));AuditPC->CloseGunsmith();Equip(TEXT("ue_m4a1"));});
        Later(21,[AuditPC,Check](){Check(AuditPC->OpenGunsmith(),TEXT("open M4 control workbench"));});
        Later(22,[Panel](){if(auto* W=Panel()){W->ChooseOption(TEXT("optic"),TEXT("holographic"));W->ChooseOption(TEXT("underbarrel"),TEXT("vertical_foregrip"));}});
        Later(23,[Fit,Drag](){Fit(TEXT("M4 before drag"));Drag(TEXT("M4"));});
        Later(24,[Fit,Shot](){Fit(TEXT("M4 after drag"));Shot(TEXT("m4-dragged.png"));});
        Later(25,[AuditPC,Counts](){AuditPC->CloseGunsmith();UE_LOG(LogTemp,Display,TEXT("ASH_PREVIEW_FIX: COMPLETE checks=%d failures=%d"),Counts->X,Counts->Y);AuditPC->ConsoleCommand(TEXT("quit"));});
        return;
    }
    static int Stage=0;static double At=0;static int32 BeatIndex=0;
    static const float EyeReliefs[]={12.f,18.f,24.f};
    FString Run;FParse::Value(FCommandLine::Get(),TEXT("ASH12Run="),Run);Run=FPaths::MakeValidFileName(Run);
    const FString Out=FPaths::ProjectSavedDir()/TEXT("ASH12SightAudit")/Run;
    const double Now=GetWorld()->GetTimeSeconds();
    auto Capture=[&](const TCHAR* Name)
    {
        const FString File=Out/Name;
        UE_LOG(LogTemp,Display,TEXT("ASH12_SIGHT_CAPTURE mesh=%s aim=%s alpha=%.6f eye=%.2f output=%s"),
            *GetPathNameSafe(AKMViewmodel?AKMViewmodel->GetSkeletalMeshAsset():nullptr),
            *GetPathNameSafe(AimAnimation),WeaponADSFactor,ADSRearEyeDistance,*File);
        FScreenshotRequest::RequestScreenshot(File,false,false);
    };
    auto Aim=[&](bool Down){PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::RightMouseButton,Down?IE_Pressed:IE_Released,Down?1:0));};
    if(Stage==0)
    {
        IFileManager::Get().MakeDirectory(*Out,true);
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto Rifle=P->CreateItem(TEXT("ue_ash12"));Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=20;S.Items.Add(Rifle);
        auto Ammo=P->CreateItem(TEXT("ammo_127"),120);if(!Ammo.Data.IsEmpty())S.Items.Add(Ammo);
        if(!P->CommitState(S)){UE_LOG(LogTemp,Error,TEXT("ASH12_SIGHT_CAPTURE could not equip the fixture"));PC->ConsoleCommand(TEXT("quit"));return;}
        ADSRearEyeDistance=EyeReliefs[0];bSightCalibrated=false;
        Stage=1;At=Now;
    }
    else if(Stage==1&&!IsWeaponBusy()&&Now-At>1.5){Capture(TEXT("ASH12-hip.png"));Stage=2;At=Now;}
    else if(Stage==2&&Now-At>0.5){Aim(true);Stage=3;At=Now;}
    else if(Stage>=3&&Stage<=5&&Now-At>2.0)
    {
        const int32 Index=Stage-3;
        Capture(*FString::Printf(TEXT("ASH12-ADS-eye%02d.png"),int32(EyeReliefs[Index])));
        if(Index+1<UE_ARRAY_COUNT(EyeReliefs))
        {
            ADSRearEyeDistance=EyeReliefs[Index+1];bSightCalibrated=false;
            Stage+=1;At=Now;
        }
        else
        {
            // Same aim, shared holographic sight, so an optic complaint can be
            // told apart from an iron-sight one.
            SetGunsmithOpticVariant(TEXT("holographic"));
            Stage=6;At=Now;
        }
    }
    else if(Stage==6&&Now-At>2.0){Capture(TEXT("ASH12-ADS-optic.png"));SetGunsmithOpticVariant(TEXT("false"));Aim(false);Stage=7;At=Now;}
    else if(Stage==7&&Now-At>1.0)
    {
        // Reproduce the states a player actually aims in: walking while aimed,
        // then a burst. A settled still cannot tell those apart from the build.
        Aim(true);Stage=8;At=Now;
    }
    else if(Stage==8&&Now-At>1.5)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Pressed,1.0f));
        Stage=9;At=Now;
    }
    else if(Stage==9&&Now-At>1.2){Capture(TEXT("ASH12-ADS-walk.png"));Stage=10;At=Now;}
    else if(Stage==10&&Now-At>0.3)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Pressed,1.0f));
        Stage=11;At=Now;
    }
    else if(Stage==11&&Now-At>0.45){Capture(TEXT("ASH12-ADS-burst.png"));Stage=12;At=Now;}
    else if(Stage==12&&Now-At>0.3)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::LeftMouseButton,IE_Released,0.0f));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::W,IE_Released,0.0f));
        Aim(false);Stage=13;At=Now;
    }
    else if(Stage==13&&Now-At>1.0){bGunsmithInspection=true;Stage=14;At=Now;}
    else if(Stage==14&&Now-At>1.5){Capture(TEXT("ASH12-closeup.png"));bGunsmithInspection=false;Stage=15;At=Now;}
    else if(Stage==15&&Now-At>0.6)
    {
        // Empty the magazine so the reload that follows is the empty one, then
        // drive it with the same key a player presses. Captures land on the
        // frames the runtime fires its mechanical cues on (21/60, 54/60, 80/60,
        // 130/60 of the 2.7 s clip), plus the pull-out beat.
        auto S=P->Snapshot();S.Items.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
        auto Rifle=P->CreateItem(TEXT("ue_ash12"));Rifle.Place=1;Rifle.Cell=9;Rifle.Magazine=0;S.Items.Add(Rifle);
        auto Ammo=P->CreateItem(TEXT("ammo_127"),120);if(!Ammo.Data.IsEmpty())S.Items.Add(Ammo);
        if(!P->CommitState(S))UE_LOG(LogTemp,Error,TEXT("ASH12_RELOAD_CAPTURE could not empty the rifle"));
        Stage=16;At=Now;
    }
    else if(Stage==16&&Now-At>1.0)
    {
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Pressed,1.0f));
        PC->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::R,IE_Released,0.0f));
        UE_LOG(LogTemp,Display,TEXT("ASH12_RELOAD_CAPTURE key=R source_time=%.4f"),ReloadSourceTime(WeaponStateElapsed));
        Stage=17;At=Now;BeatIndex=0;
    }
    else if(Stage==17)
    {
        static const float Beats[]={0.35f,0.70f,0.90f,1.33f,2.17f};
        const double Since=Now-At;
        if(BeatIndex<int32(UE_ARRAY_COUNT(Beats))&&Since>=Beats[BeatIndex])
        {
            UE_LOG(LogTemp,Display,TEXT("ASH12_RELOAD_CAPTURE beat=%.2f source_time=%.4f"),
                Beats[BeatIndex],ReloadSourceTime(WeaponStateElapsed));
            Capture(*FString::Printf(TEXT("ASH12-reload-t%03d.png"),int32(Beats[BeatIndex]*100)));
            ++BeatIndex;
        }
        else if(BeatIndex>=int32(UE_ARRAY_COUNT(Beats))&&Since>3.6)Stage=20;
    }
    else if(Stage==20){PC->ConsoleCommand(TEXT("quit"));}
}
