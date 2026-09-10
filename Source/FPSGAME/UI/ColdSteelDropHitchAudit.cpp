#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelPickupStudio.h"
#include "ColdSteelPickup.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/ScrollBox.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

void UColdSteelHUDWidget::RunDropHitchAudit()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M->IsAudit())return;
    auto* Pawn=GetOwningPlayer()->GetCharacter();if(!Pawn)return;
    auto* Platform=GetWorld()->SpawnActor<AActor>();auto* Floor=NewObject<UBoxComponent>(Platform);Platform->SetRootComponent(Floor);Floor->SetBoxExtent(FVector(500,500,10));Floor->SetCollisionProfileName(TEXT("BlockAll"));Floor->RegisterComponent();Platform->SetActorLocation(FVector(50000,50000,5000));
    auto* FloorMesh=NewObject<UStaticMeshComponent>(Platform);FloorMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));FloorMesh->SetupAttachment(Floor);FloorMesh->SetRelativeScale3D(FVector(10,10,.2));FloorMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);FloorMesh->RegisterComponent();
    Pawn->TeleportTo(FVector(50000,50000,5110),FRotator::ZeroRotator);Pawn->GetCharacterMovement()->StopMovementImmediately();GetOwningPlayer()->SetControlRotation(FRotator(-30,0,0));
    struct FRun{int32 Phase=0,Checks=0,Failures=0,Wait=0;uint64 Frame=MAX_uint64;FTimerHandle Timer;FString Id;FVector2D Start,Outside;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("DropHitchAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto State=M->Snapshot();State.Items.Empty();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Cell=0;Gun.Magazine=13;State.Items.Add(Gun);R->Id=Gun.InstanceId;Check(M->CommitState(State),TEXT("isolated rifle fixture"));
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,M,R,Check](){
        if(R->Frame==GFrameCounter)return;R->Frame=GFrameCounter;
        auto* PC=GetOwningPlayer();auto& App=FSlateApplication::Get();auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;if(!Board)return;
        auto Pointer=[](FVector2D P,FVector2D Previous,bool Down,FKey Key=EKeys::Invalid){return FPointerEvent(0,P,Previous,Down?TSet<FKey>{EKeys::LeftMouseButton}:TSet<FKey>{},Key,0,FModifierKeysState());};
        auto Click=[&](FVector2D P){App.ProcessMouseMoveEvent(Pointer(P,P,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(P,P,true,EKeys::LeftMouseButton));App.ProcessMouseButtonUpEvent(Pointer(P,P,false,EKeys::LeftMouseButton));};
        auto Tab=[&](){App.ProcessKeyDownEvent(FKeyEvent(EKeys::Tab,FModifierKeysState(),0,false,0,0));App.ProcessKeyUpEvent(FKeyEvent(EKeys::Tab,FModifierKeysState(),0,false,0,0));};
        const auto G=Board->GetCachedGeometry();const auto L=Board->Layout(G);
        switch(R->Phase++){
        case 0:SetInventoryTab(false);SetInventoryOpen(true);break;
        case 1:{auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();if((!Icons->IsIdle()||!Icons->Find(*M->FindItem(R->Id)))&&R->Wait++<100){--R->Phase;break;}Check(GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Bounds.Contains(GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>()->Key(*M->FindItem(R->Id))),TEXT("visible inventory prewarms exact weapon recipe"));Board->SetKeyboardFocus();Tab();break;}
        case 2:Check(!bInventoryOpen&&!PC->bShowMouseCursor&&!PC->IsLookInputIgnored(),TEXT("TAB closes focused backpack and restores gameplay"));OpenStatus();break;
        case 3:Tab();Check(!bInventoryOpen,TEXT("TAB also closes character page"));SetInventoryTab(false);SetInventoryOpen(true);break;
        case 4:Click(G.LocalToAbsolute(FVector2D(14,L.BagY+L.Cell*2.5)/Board->Scale));Check(bInventoryOpen,TEXT("click inside inventory keeps panel open"));Board->SelectItem(R->Id);Board->OpenItemMenu(G.LocalToAbsolute(FVector2D(30,L.BagY+20)/Board->Scale),false);break;
        case 5:Tab();Check(!bInventoryOpen&&!PC->bShowMouseCursor,TEXT("TAB closes backpack from detached item popup"));SetInventoryOpen(true);break;
        case 6:R->Outside=GetCachedGeometry().LocalToAbsolute(GetCachedGeometry().GetLocalSize()*FVector2D(.1,.4));Click(R->Outside);Check(!bInventoryOpen&&!PC->IsMoveInputIgnored(),TEXT("outside click closes panel without leaking game input"));SetInventoryOpen(true);break;
        case 7:R->Start=G.LocalToAbsolute(FVector2D(12+L.Cell*2.5,L.BagY+L.Cell*.5)/Board->Scale);App.ProcessMouseMoveEvent(Pointer(R->Start,R->Start,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(R->Start,R->Start,true,EKeys::LeftMouseButton));break;
        case 8:App.ProcessMouseMoveEvent(Pointer(R->Start+FVector2D(12,0),R->Start,true));break;
        case 9:App.ProcessMouseMoveEvent(Pointer(R->Outside,R->Start+FVector2D(12,0),true));Check(App.IsDragDropping()&&bInventoryOpen,TEXT("dragging outside does not act as an outside click"));break;
        case 10:{const double Begin=FPlatformTime::Seconds();App.ProcessMouseButtonUpEvent(Pointer(R->Outside,R->Outside,false,EKeys::LeftMouseButton));const double Ms=(FPlatformTime::Seconds()-Begin)*1000;UE_LOG(LogTemp,Display,TEXT("DropTiming: native mouse release %.3f ms"),Ms);const auto* I=M->FindItem(R->Id);Check(I&&I->Place==2&&I->Magazine==13,TEXT("real mouse release drops exact rifle and ammo"));break;}
        case 11:Click(R->Outside);Check(!bInventoryOpen&&!PC->bShowMouseCursor,TEXT("outside close still works after ending a drag"));for(TActorIterator<AColdSteelPickup> It(GetWorld());It;++It)if(It->ItemId==R->Id){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((It->GetActorLocation()-Eye).Rotation());Check(It->Body->IsSimulatingPhysics(),TEXT("dropped rifle keeps gravity physics"));}break;
        case 12:{const FString Dir=FPaths::ProjectSavedDir()/TEXT("DropHitch");IFileManager::Get().MakeDirectory(*Dir,true);FScreenshotRequest::RequestScreenshot(Dir/TEXT("native-drag-ground.png"),true,false);break;}
        default:GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("DropHitchAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);PC->ConsoleCommand(TEXT("quit"));break;
        }
    }),.35f,true);
}
