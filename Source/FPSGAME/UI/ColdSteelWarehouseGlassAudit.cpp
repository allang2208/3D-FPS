#include "ColdSteelHUDWidget.h"
#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelWorldInteraction.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelInventoryPopup.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "Blueprint/WidgetTree.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Components/ScrollBox.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/TextBlock.h"
#include "Components/EditableTextBox.h"
#include "Components/BoxComponent.h"
#include "Components/BackgroundBlur.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/Engine.h"
#include "EngineUtils.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

void UColdSteelHUDWidget::RunWarehouseGlassAudit()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    auto* PC=GetOwningPlayer();auto* Pawn=PC->GetCharacter();if(!Pawn)return;
    AColdSteelWarehouseChest* Chest=nullptr;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It){Chest=*It;break;}if(!Chest){UE_LOG(LogTemp,Error,TEXT("WarehouseGlass: FAIL no reachable chest fixture"));PC->ConsoleCommand(TEXT("quit"));return;}
    Pawn->GetCharacterMovement()->StopMovementImmediately();
    FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((Chest->GetActorLocation()+FVector(0,0,40)-Eye).Rotation());PC->PlayerCameraManager->UpdateCamera(0);
    struct FRun{int32 Phase=-1,Checks=0,Failures=0,Wait=0;FTimerHandle Timer;FVector2D Start,Target;FString BagGun,StoredGun,Potion;FColdSteelProfile Fixture;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto P=M->Snapshot();P.Items.Empty();P.Hotbar.Init(TEXT(""),4);P.HotbarDefinitions.Init(TEXT(""),4);P.WarehousePages=5;
    auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Cell=0;Gun.Magazine=13;R->BagGun=Gun.InstanceId;P.Items.Add(Gun);
    Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Place=4;Gun.Cell=0;Gun.Magazine=7;R->StoredGun=Gun.InstanceId;P.Items.Add(Gun);
    auto Potion=M->CreateItem(TEXT("hp_potion"),9);Potion.Place=4;Potion.Cell=8;R->Potion=Potion.InstanceId;P.Items.Add(Potion);
    auto Mana=M->CreateItem(TEXT("mp_potion"),3);Mana.Cell=8;P.Items.Add(Mana);R->Fixture=P;Check(M->CommitState(P),TEXT("isolated spatial UI fixture"));
    SetInventoryOpen(false);
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,M,R,Check,Chest](){
        auto* PC=GetOwningPlayer();auto& App=FSlateApplication::Get();auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Bag=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;auto* Store=WarehouseWidget->Board.Get();if(!Bag||!Store)return;
        auto Pointer=[](FVector2D At,FVector2D Last,bool Down,FKey Button=EKeys::Invalid,bool Shift=false){return FPointerEvent(0,At,Last,Down?TSet<FKey>{Button==EKeys::RightMouseButton?EKeys::RightMouseButton:EKeys::LeftMouseButton}:TSet<FKey>{},Button,0,FModifierKeysState(Shift,false,false,false,false,false,false,false,false));};
        auto Move=[&](FVector2D At){App.ProcessMouseMoveEvent(Pointer(At,R->Start,true));};
        auto Down=[&](FVector2D At,FKey Key=EKeys::LeftMouseButton,bool Shift=false){R->Start=At;App.ProcessMouseMoveEvent(Pointer(At,At,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(At,At,true,Key,Shift));};
        auto Up=[&](FVector2D At,FKey Key=EKeys::LeftMouseButton,bool Shift=false){App.ProcessMouseButtonUpEvent(Pointer(At,R->Start,false,Key,Shift));};
        auto Click=[&](UWidget* W){const auto G=W->GetCachedGeometry();const auto At=G.LocalToAbsolute(G.GetLocalSize()*.5);Down(At);Up(At);};
        auto ButtonNamed=[](UUserWidget* W,const TCHAR* Name)->UButton*{TArray<UWidget*> Widgets;W->WidgetTree->GetAllWidgets(Widgets);for(auto* V:Widgets)if(auto* B=Cast<UButton>(V))if(auto* T=Cast<UTextBlock>(B->GetContent()))if(T->GetText().ToString()==Name)return B;return nullptr;};
        auto Cell=[](UColdSteelInventoryWidget* B,int32 C){const auto G=B->GetCachedGeometry();const auto L=B->Layout(G);return G.LocalToAbsolute(FVector2D(12+(C%18+.5f)*L.Cell,L.BagY+(C/18+.5f)*L.Cell)/B->Scale);};
        auto Capture=[&](const TCHAR* Name){const FString Dir=FPaths::ProjectSavedDir()/TEXT("WarehouseColdGlass20260912");IFileManager::Get().MakeDirectory(*Dir,true);const auto Size=UWidgetLayoutLibrary::GetViewportSize(this);FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%d.png"),Name,int32(Size.X)),true,false);};
        auto Located=[M](const FString& Id,int32 Place,int32 C){const auto* I=M->FindItem(Id);return I&&I->Place==Place&&I->Cell==C;};
        const int32 Phase=R->Phase++;UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: phase=%d drag=%d open=%d"),Phase,App.IsDragDropping(),bWarehouseOpen);
        if(Phase==-1){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((Chest->GetActorLocation()+FVector(0,0,40)-Eye).Rotation());}
        else if(Phase==0){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: camera=%s rotation=%s pawn=%s chest=%s reach=%d cursor=%d trace=%s"),*Eye.ToString(),*View.ToString(),*PC->GetPawn()->GetActorLocation().ToString(),*Chest->GetActorLocation().ToString(),Chest->IsWithinReach(PC->GetPawn()),PC->bShowMouseCursor,*GetNameSafe(ColdSteelWorldInteraction::TraceTarget(PC,240)));Check(Chest->CanInteract(PC->GetPawn()),TEXT("real chest reachable on isolated platform"));OpenWarehouse(Chest);Check(bWarehouseOpen&&bInventoryOpen,TEXT("open both panels"));if(!bWarehouseOpen)R->Phase=31;}
        else if(Phase==1){
            const auto W=WarehouseWidget->GetCachedGeometry(),B=InventoryPanel->GetCachedGeometry();const auto V=UWidgetLayoutLibrary::GetViewportWidgetGeometry(this);
            Check(W.GetAbsoluteSize().Equals(B.GetAbsoluteSize(),2)&&W.GetAbsolutePosition().X+W.GetAbsoluteSize().X<=B.GetAbsolutePosition().X,TEXT("left warehouse matches backpack size without overlap"));
            Check(V.AbsoluteToLocal(W.GetAbsolutePosition()).X>=0&&V.AbsoluteToLocal(B.LocalToAbsolute(B.GetLocalSize())).X<=V.GetLocalSize().X+1,TEXT("both drawers fit viewport"));
            Check(WarehouseWidget->Blur->GetBlurStrength()==9&&InventoryBlur->GetBlurStrength()==9&&InventoryPanel->GetBrushColor().A>.95,TEXT("shared real blur and lower transparency"));
            bool Grid=true;for(int32 C=0;C<216;++C){int32 Place=-1,HitCell=-1;Grid&=Store->Hit(Store->GetCachedGeometry(),Cell(Store,C),Place,HitCell)&&Place==4&&HitCell==C;}Check(Grid,TEXT("all 216 spatial cell hit regions map correctly"));
            Capture(TEXT("warehouse-equipment"));Scroll->ScrollToEnd();
        }
        else if(Phase==2){Down(Cell(Bag,19));}
        else if(Phase==3){Move(R->Start+FVector2D(24,0));Check(App.IsDragDropping(),TEXT("real Slate bag drag begins"));}
        else if(Phase==4){R->Target=Cell(Store,73);Move(R->Target);Check(Store->bPreviewValid&&Store->PreviewCell==54&&Located(R->BagGun,0,0),TEXT("cross-panel hover preserves grabbed subcell and is read-only"));Check(InventoryPanel->GetRenderOpacity()>.95&&WarehouseWidget->GetRenderOpacity()>.95,TEXT("both panels stay visible during cross-panel drag"));Capture(TEXT("warehouse-drag"));}
        else if(Phase==5){Up(R->Target);Check(Located(R->BagGun,4,54)&&M->FindItem(R->BagGun)->Magazine==13,TEXT("real Slate drop stores exact anchor and ammo"));}
        else if(Phase==6){Down(Cell(Store,0));}
        else if(Phase==7){Move(R->Start+FVector2D(24,0));}
        else if(Phase==8){Check(M->SaveNow(),TEXT("save unchanged item while real drag is active"));R->Target=Cell(Bag,18);Move(R->Target);UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: withdraw preview=%d place=%d cell=%d reason=%s"),Bag->bPreviewValid,Bag->PreviewPlace,Bag->PreviewCell,*Bag->PreviewReason);Capture(TEXT("warehouse-withdraw-preview"));}
        else if(Phase==9){Up(R->Target);const auto* I=M->FindItem(R->StoredGun);UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: withdraw result place=%d cell=%d ammo=%d message=%s"),I?I->Place:-1,I?I->Cell:-1,I?I->Magazine:-1,*Bag->InteractionMessage);Check(Located(R->StoredGun,0,18)&&M->FindItem(R->StoredGun)->Magazine==7,TEXT("real Slate warehouse withdrawal reaches exact backpack rectangle"));}
        else if(Phase==10){const auto At=Cell(Store,8);Down(At,EKeys::LeftMouseButton,true);Up(At,EKeys::LeftMouseButton,true);}
        else if(Phase==11){Check(Store->ItemMenu&&Store->ItemMenu->IsInViewport()&&Store->ItemMenu->Quantity,TEXT("shift click opens warehouse split editor"));if(Store->ItemMenu&&Store->ItemMenu->Quantity){Store->ItemMenu->Quantity->SetText(FText::FromString(TEXT("4")));if(auto* B=ButtonNamed(Store->ItemMenu,TEXT("确认拆分 · Enter")))Click(B);} }
        else if(Phase==12){Check(M->FindItem(R->Potion)&&M->FindItem(R->Potion)->Count==5&&M->Items().ContainsByPredicate([&](const auto& I){return I.Place==4&&I.Definition==TEXT("hp_potion")&&I.Count==4;}),TEXT("split confirmation commits separate warehouse stack"));const auto At=Cell(Store,8);Down(At,EKeys::RightMouseButton,true);Up(At,EKeys::RightMouseButton,true);}
        else if(Phase==13){auto* B=Store->ItemMenu?ButtonNamed(Store->ItemMenu,TEXT("取出到背包")):nullptr;Check(B!=nullptr,TEXT("warehouse context menu offers retrieval"));if(B)Click(B);}
        else if(Phase==14){Check(M->FindItem(R->Potion)&&M->FindItem(R->Potion)->Place==0&&M->FindItem(R->Potion)->Count==5,TEXT("context retrieval commits correct quantity"));Click(WarehouseWidget->Next);}
        else if(Phase==15){Check(M->WarehousePage==1&&Store->StorageStart()==216,TEXT("real next page button updates grid addressing"));Click(WarehouseWidget->Previous);}
        else if(Phase==16){Check(M->WarehousePage==0,TEXT("real previous page button returns to first page"));M->CommitState(R->Fixture);}
        else if(Phase==17){Down(Cell(Bag,0));}
        else if(Phase==18){Move(R->Start+FVector2D(24,0));}
        else if(Phase==19){R->Target=Cell(Store,54);Move(R->Target);auto P=M->Snapshot();for(auto& I:P.Items)if(I.InstanceId==R->BagGun)I.Magazine=12;M->CommitState(P);}
        else if(Phase==20){Up(R->Target);Check(Located(R->BagGun,0,0)&&M->FindItem(R->BagGun)->Magazine==12&&!Store->bPreviewValid,TEXT("changed source snapshot rejects routed warehouse drop"));M->CommitState(R->Fixture);}
        else if(Phase==21){Down(Cell(Bag,0));}
        else if(Phase==22){Move(R->Start+FVector2D(24,0));}
        else if(Phase==23){R->Target=Cell(Store,54);Move(R->Target);}
        else if(Phase==24){M->AuditFailNextSave=true;Up(R->Target);Check(Located(R->BagGun,0,0)&&!App.IsDragDropping()&&!M->AuditFailNextSave,TEXT("save failure restores source and clears drag"));}
        else if(Phase==25){if(auto* B=ButtonNamed(WarehouseWidget,TEXT("全部存入")))Click(B);}
        else if(Phase==26){Check(!M->Items().ContainsByPredicate([](const auto& I){return I.Place==0;}),TEXT("real store all button empties backpack atomically"));if(auto* B=ButtonNamed(WarehouseWidget,TEXT("全部取出")))Click(B);}
        else if(Phase==27){Check(!M->Items().ContainsByPredicate([](const auto& I){return I.Place==4;}),TEXT("real retrieve all button restores backpack items"));M->CommitState(R->Fixture);Scroll->ScrollToStart();Capture(TEXT("warehouse-final"));}
        else if(Phase==28){if(auto* B=ButtonNamed(WarehouseWidget,TEXT("收起仓库")))Click(B);}
        else if(Phase==29){Check(!bWarehouseOpen&&bInventoryOpen&&WarehouseWidget->GetVisibility()==ESlateVisibility::Collapsed,TEXT("left close animation completes while backpack stays open"));SetInventoryOpen(false);OpenWarehouse(Chest);CloseWarehouse();SetInventoryOpen(false);OpenWarehouse(Chest);}
        else if(Phase==30){if(Chest->IsAnimating()&&R->Wait++<8){--R->Phase;return;}Check(bWarehouseOpen&&WarehouseMotion>.99&&Chest->IsOpen(),TEXT("rapid close reopen settles in latest state"));Capture(TEXT("warehouse-reopened"));}
        else if(Phase==31){SetInventoryOpen(false);Check(!bWarehouseOpen&&!PC->bShowMouseCursor&&!PC->IsLookInputIgnored(),TEXT("closing backpack restores gameplay input"));UE_LOG(LogTemp,Display,TEXT("WarehouseGlass: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetWorld()->GetTimerManager().ClearTimer(R->Timer);PC->ConsoleCommand(TEXT("quit"));}
    }),.7f,true);
}
