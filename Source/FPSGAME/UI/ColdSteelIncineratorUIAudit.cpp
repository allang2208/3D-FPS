#include "../FPSGAMEPlayerController.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelIncineratorWidget.h"
#include "ColdSteelIncineratorStorage.h"
#include "ColdSteelInventoryWidget.h"
#include "Components/ScrollBox.h"
#include "Components/Border.h"
#include "Engine/GameViewportClient.h"
#include "Engine/UserInterfaceSettings.h"
#include "Framework/Application/SlateApplication.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWorldInteraction.h"
#include "../Building/VoxelBuildWorld.h"
#include "../Building/VoxelBuildPrefabActor.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/KismetMathLibrary.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "UObject/GarbageCollection.h"

/** Runs only when explicitly requested, with both a unique audit slot and a redirected Saved tree. */
void RunIncineratorUIAudit(AFPSGAMEPlayerController* PC)
{
    if(!PC||!FParse::Param(FCommandLine::Get(),TEXT("IncineratorUIAudit")))return;
    auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* H=PC->GetColdSteelHUD();
    FString Root;FParse::Value(FCommandLine::Get(),TEXT("IncineratorAuditRoot="),Root);
    if(Root.IsEmpty()){UE_LOG(LogTemp,Error,TEXT("INCINERATOR_UI ABORT: no isolated root"));FPlatformMisc::RequestExitWithStatus(false,2);return;}
    Root=FPaths::ConvertRelativePathToFull(Root);FPaths::NormalizeDirectoryName(Root);
    FString Saved=FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir());FPaths::NormalizeDirectoryName(Saved);
    if(Root.IsEmpty()||!Saved.StartsWith(Root+TEXT("/"))||!M||!H||!M->IsAudit()||!M->ProfileSlot().StartsWith(TEXT("ColdSteel_IncineratorUIAudit_")))
    {UE_LOG(LogTemp,Error,TEXT("INCINERATOR_UI ABORT isolation guard: Saved=%s"),*Saved);FPlatformMisc::RequestExitWithStatus(false,2);return;}
    float DPI=1.f;FParse::Value(FCommandLine::Get(),TEXT("IncineratorAuditDPI="),DPI);GetMutableDefault<UUserInterfaceSettings>()->ApplicationScale=FMath::Clamp(DPI,.75f,2.f);
    const FString Dir=Saved/TEXT("IncineratorAudit");IFileManager::Get().MakeDirectory(*Dir,true);
    struct FRun
    {
        int32 Phase=0,Retries=0,Checks=0,Failures=0;FTimerHandle Timer;
        TWeakObjectPtr<AVoxelBuildWorld> World;TWeakObjectPtr<AVoxelBuildPrefabActor> Piece;TWeakObjectPtr<ACameraActor> Camera;
        FString Report,Potion,Gun,Bag,Nested,Ammo,Container;FVector2D Start;int64 Generation=0;bool Done=false;
    };
    auto R=MakeShared<FRun>();R->Report=TEXT("PROFILE ")+M->ProfileSlot()+TEXT("\nSAVED ")+Saved+TEXT("\n");
    auto Check=[R](bool OK,const FString& Label){++R->Checks;if(!OK)++R->Failures;const FString Line=(OK?TEXT("PASS "):TEXT("FAIL "))+Label;R->Report+=Line+TEXT("\n");UE_LOG(LogTemp,Display,TEXT("INCINERATOR_UI %s"),*Line);return OK;};
    auto Finish=[PC,R,Dir](){if(R->Done)return;R->Done=true;PC->GetWorldTimerManager().ClearTimer(R->Timer);
        R->Report+=FString::Printf(TEXT("RESULT checks=%d failures=%d\n"),R->Checks,R->Failures);
        FFileHelper::SaveStringToFile(R->Report,*(Dir/TEXT("ui.txt")),FFileHelper::EEncodingOptions::ForceUTF8WithoutBOM);
        // Process exit discards the transient runtime world; never switch maps while Python/Slate owns references.
        FPlatformMisc::RequestExitWithStatus(false,R->Failures?1:0);};
    auto Shot=[Dir](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(Dir/(FString(Name)+TEXT(".png")),true,false);};
    PC->GetWorldTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(PC,[PC,M,H,R,Check,Finish,Shot,Dir]()
    {
        if(R->Done)return;
        auto* P=H->IncineratorPanel();const int32 T=R->Phase++;
        auto* BagScroll=Cast<UScrollBox>(H->EquipmentPage);auto* Bag=BagScroll?Cast<UColdSteelInventoryWidget>(BagScroll->GetChildAt(0)):nullptr;auto* Store=P?P->InputBoard():nullptr;
        auto& App=FSlateApplication::Get();
        auto Pointer=[](FVector2D At,FVector2D Last,bool Down,FKey Button=EKeys::Invalid){return FPointerEvent(0,At,Last,Down?TSet<FKey>{Button==EKeys::RightMouseButton?EKeys::RightMouseButton:EKeys::LeftMouseButton}:TSet<FKey>{},Button,0,FModifierKeysState());};
        auto Down=[&](FVector2D At,FKey Key=EKeys::LeftMouseButton){R->Start=At;App.ProcessMouseMoveEvent(Pointer(At,At,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(At,At,true,Key));};
        auto Move=[&](FVector2D At){App.ProcessMouseMoveEvent(Pointer(At,R->Start,true));};
        auto Up=[&](FVector2D At,FKey Key=EKeys::LeftMouseButton){App.ProcessMouseButtonUpEvent(Pointer(At,R->Start,false,Key));};
        auto Cell=[](UColdSteelInventoryWidget* B,int32 C)->FVector2D{if(!B)return FVector2D::ZeroVector;const auto G=B->GetCachedGeometry();const auto L=B->Layout(G);return G.LocalToAbsolute(FVector2D(12+(C%18+.5f)*L.Cell,L.BagY+(C/18+.5f)*L.Cell)/B->Scale);};
        switch(T)
        {
        case 0:
            for(TActorIterator<AVoxelBuildWorld> It(PC->GetWorld());It;++It)if(It->IsReady()){R->World=*It;break;}
            if(!R->World.IsValid()||!PC->GetPawn()||!P){R->Phase=0;if(++R->Retries>30){Check(false,TEXT("fixture initialization timeout"));Finish();}}break;
        case 1:
            if(!Check(R->World->PlacePrefab(VoxelIncineratorId,FIntVector(-3,-3,0),0),TEXT("place independent incinerator through real building API"))){Finish();break;}
            for(TActorIterator<AVoxelBuildPrefabActor> It(PC->GetWorld());It;++It)if(It->PrefabId()==VoxelIncineratorId&&!It->IsFalling())R->Piece=*It;
            if(!Check(R->Piece.IsValid(),TEXT("placed incinerator actor exists"))){Finish();break;}
            R->Camera=PC->GetWorld()->SpawnActor<ACameraActor>();R->Camera->SetActorLocation(FVector(330,-430,240));
            R->Camera->SetActorRotation(UKismetMathLibrary::FindLookAtRotation(R->Camera->GetActorLocation(),FVector(0,0,100)));
            R->Camera->GetCameraComponent()->SetFieldOfView(40);PC->SetViewTarget(R->Camera.Get());break;
        case 3:Shot(TEXT("Incinerator_UE_Model"));break;
        case 4:
        {
            auto S=M->Snapshot();S.Items.Reset();S.AmmoPouch.Reset();S.Hotbar.Init(TEXT(""),4);S.HotbarDefinitions.Init(TEXT(""),4);
            for(auto& B:S.QuickBindings)B=FColdSteelQuickBinding();S.ActiveProductionTool.Reset();
            auto Potion=M->CreateItem(TEXT("hp_potion"),9);Potion.Cell=0;R->Potion=Potion.InstanceId;S.Items.Add(Potion);
            auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Cell=18;Gun.Magazine=17;Gun.VirtualMagazineAmmo=0;R->Gun=Gun.InstanceId;S.Items.Add(Gun);
            R->Ammo=M->AmmoCatalog()[0].Id;S.AmmoPouch.Add(R->Ammo,100);
            if(!Check(M->CommitState(S),TEXT("seed temporary representative inventory"))){Finish();break;}
            R->Generation=M->Snapshot().Generation;
            PC->GetPawn()->SetActorLocation(FVector(0,-200,100));PC->SetControlRotation(FRotator(-10,90,0));
            R->Camera->SetActorLocation(FVector(0,-200,140));R->Camera->SetActorRotation(FRotator(-8,90,0));R->Camera->GetCameraComponent()->SetFieldOfView(60);break;
        }
        case 6:
            Check(ColdSteelWorldInteraction::TraceTarget(PC)==R->Piece.Get(),TEXT("GRID E trace resolves incinerator"));
            static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1));
            if(!Check(H->IsWorkbenchOpen(),TEXT("GRID E opens new spatial panel"))){Finish();break;}
            if(BagScroll)BagScroll->ScrollToEnd();break;
        case 7:static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Released,0));break;
        case 8:
        {
            FString Reason;Check(P->AuditGeometry(Reason),TEXT("GRID empty layout in bounds: ")+Reason);
            const auto Left=P->GetCachedGeometry().GetLayoutBoundingRect(),Right=H->InventoryPanel->GetCachedGeometry().GetLayoutBoundingRect();
            Check(FMath::Abs(Left.GetSize().X-Right.GetSize().X)<2&&FMath::Abs(Left.Right-Right.Left)<2,TEXT("GRID left furnace and right backpack have equal widths and zero gap"));
            Check(PC->bShowMouseCursor&&PC->IsMoveInputIgnored()&&PC->IsLookInputIgnored(),TEXT("GRID panel owns gameplay input locks"));
            Check(P->AuditPreview().Contains(TEXT("产出未配置"))&&!P->AuditReview(),TEXT("GRID empty rule state is explicit and empty input cannot burn"));
            Shot(TEXT("Incinerator_Grid_Empty"));break;
        }
        case 10:
        {
            const auto At=Cell(Bag,0);Down(At,EKeys::RightMouseButton);Up(At,EKeys::RightMouseButton);break;
        }
        case 11:
            Check(M->FindItem(R->Potion)&&M->FindItem(R->Potion)->Container==P->ContainerKey()&&M->FindItem(R->Potion)->Count==9,TEXT("GRID actual right mouse deposits potion without using it"));
            Down(Cell(Bag,18));break;
        case 12:Move(Cell(Bag,18)+FVector2D(12,0));break;
        case 13:Move(Cell(Store,18));break;
        case 14:Up(Cell(Store,18));break;
        case 15:
            Check(M->FindItem(R->Gun)&&M->FindItem(R->Gun)->Container==P->ContainerKey()&&M->FindItem(R->Gun)->Magazine==17,TEXT("GRID actual cross-panel drag deposits loaded weapon"));
            Check(!H->bInventoryDragOutside&&H->InventoryPanel->IsVisible(),TEXT("GRID cross-panel drag restores backpack visibility"));
            Shot(TEXT("Incinerator_Grid_Items"));break;
        case 17:
        {
            const auto* Item=M->FindItem(R->Potion);if(Item&&Item->Place==4){const auto At=Cell(Store,Item->Cell);Down(At,EKeys::RightMouseButton);Up(At,EKeys::RightMouseButton);}break;
        }
        case 18:
            Check(M->FindItem(R->Potion)&&M->FindItem(R->Potion)->Place==0&&M->FindItem(R->Potion)->Count==9,TEXT("GRID actual right mouse retrieves potion intact"));
            Check(P->AuditDepositAmmo(R->Ammo,37)&&M->PouchCount(R->Ammo)==63,TEXT("GRID live panel deposits dedicated ammunition escrow"));
            Check(P->AuditReview(),TEXT("GRID confirmation uses actual container contents"));break;
        case 19:Shot(TEXT("Incinerator_Grid_Confirm"));break;
        case 21:
            Check(P->CancelConfirmation(),TEXT("GRID cancel confirmation leaves items stored"));
            P->RequestClose();Check(!H->IsWorkbenchOpen()&&!PC->bShowMouseCursor&&!PC->IsMoveInputIgnored()&&!PC->IsLookInputIgnored(),TEXT("GRID close restores game cursor and locks"));break;
        case 23:H->OpenWorkbench(R->Piece.Get());break;
        case 25:
            Check(M->FindItem(R->Gun)&&M->FindItem(R->Gun)->Container==P->ContainerKey()&&M->PouchCount(R->Ammo)==63,TEXT("GRID reopen restores weapon and ammunition escrow"));
            Check(!P->AuditConfirm(),TEXT("GRID reopen cannot reuse cancelled confirmation"));
            Check(!R->World->RemovePrefab(R->Piece.Get()),TEXT("GRID active station with input refuses dismantling"));
            Check(P->AuditReview(),TEXT("GRID save failure review"));M->AuditFailNextSave=true;
            Check(!P->AuditConfirm()&&M->FindItem(R->Gun)&&M->PouchCount(R->Ammo)==63,TEXT("GRID UI failed save preserves all input and awards nothing"));break;
        case 26:Shot(TEXT("Incinerator_Grid_SaveFailure"));break;
        case 28:
        {
            auto Many=M->Snapshot();int32 C=72;
            for(int32 N=0;N<25;++N){auto I=M->CreateItem(TEXT("hp_potion"),N+1);I.Place=4;I.Container=P->ContainerKey();I.Cell=C++;TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);Data->SetStringField(TEXT("name"),TEXT("测试专用超长名称：附带特殊标记的补给品与完整物品说明"));Data->SetNumberField(TEXT("audit_variant"),N);I.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Many.Items.Add(I);}
            Check(M->CommitState(Many),TEXT("GRID many unique long-name items fixture"));break;
        }
        case 30:
        {FString Why;Check(P->AuditGeometry(Why),TEXT("GRID long names and many items remain within fixed layout: ")+Why);Shot(TEXT("Incinerator_Grid_Many"));break;}
        case 32:
            Check(P->AuditRetrieve(),TEXT("GRID retrieve all uses real panel handler"));
            Check(M->PouchCount(R->Ammo)==100&&!ColdSteelIncineratorStorage::HasInputs(M->Snapshot(),P->ContainerKey()),TEXT("GRID retrieve all conserves contents and returns ammunition to pouch"));break;
        case 34:
        {
            Check(M->DefaultAction(R->Potion),TEXT("GRID reinsert temporary potion for no-output action"));
            const auto Gen=M->Snapshot().Generation;Check(P->AuditReview()&&P->AuditConfirm(),TEXT("GRID confirmed empty-rule destruction on isolated temporary input"));
            Check(!M->FindItem(R->Potion)&&M->Snapshot().Generation==Gen+1&&!P->AuditConfirm(),TEXT("GRID UI confirmation commits once with no phantom reward"));
            R->Container=P->ContainerKey();P->RequestClose();break;
        }
        case 36:
            Check(R->World->RemovePrefab(R->Piece.Get()),TEXT("GRID empty station can be dismantled"));
            Check(R->World->PlacePrefab(VoxelIncineratorId,FIntVector(-3,-3,0),0),TEXT("GRID replacement at same anchor placed"));
            for(TActorIterator<AVoxelBuildPrefabActor> It(PC->GetWorld());It;++It)if(It->PrefabId()==VoxelIncineratorId&&!It->IsFalling())R->Piece=*It;
            Check(R->World->IncineratorContainerAt(FIntVector(-3,-3,0))!=R->Container,TEXT("GRID same-position rebuild receives a different storage identity"));
            H->OpenWorkbench(R->Piece.Get());break;
        case 38:
            Check(M->DefaultAction(R->Gun)&&M->FindItem(R->Gun)->Container==P->ContainerKey(),TEXT("GRID replacement station receives owned input"));
            PC->GetPawn()->SetActorLocation(FVector(0,-1000,100));break;
        case 40:
            Check(!H->IsWorkbenchOpen()&&M->FindItem(R->Gun)&&M->FindItem(R->Gun)->Place==4,TEXT("GRID leaving range closes panel without deleting input"));
            PC->GetPawn()->SetActorLocation(FVector(0,-200,100));H->OpenWorkbench(R->Piece.Get());break;
        case 42:
            Check(P->AuditRetrieve(),TEXT("GRID retained input is recoverable after leaving"));
            P->NativeOnPreviewKeyDown(P->GetCachedGeometry(),FKeyEvent(EKeys::Tab,FModifierKeysState(),0,false,0,0));
            Check(!H->IsWorkbenchOpen(),TEXT("GRID Tab closes new panel"));break;
        case 44:
            for(const TCHAR* Name:{TEXT("Incinerator_Grid_Empty"),TEXT("Incinerator_Grid_Items"),TEXT("Incinerator_Grid_Confirm"),TEXT("Incinerator_Grid_SaveFailure"),TEXT("Incinerator_Grid_Many")})
                Check(IFileManager::Get().FileSize(*(Dir/(FString(Name)+TEXT(".png"))))>1000,TEXT("GRID screenshot saved: ")+FString(Name));
            Finish();break;
        default:break;
        }
    }),.7f,true,1.f);
}
