#include "ColdSteelHUDWidget.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelWarehouseWidget.h"
#include "ColdSteelWarehouseRules.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryWidget.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/Border.h"
#include "Components/ScrollBox.h"
#include "Camera/CameraActor.h"
#include "Blueprint/WidgetTree.h"
#include "Misc/Paths.h"
#include "Misc/FileHelper.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "InputKeyEventArgs.h"
using namespace ColdSteelInventory;
void UColdSteelHUDWidget::RunWarehouseAudit()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    // Synthetic one-handed fixture keeps spatial transfer coverage independent of retired art.
    auto SmallWeapon=[M](){auto I=M->CreateItem(TEXT("ue_m4a1"));I.Definition=TEXT("audit_small_weapon");
        I.Data=TEXT("{\"category\":\"weapon\",\"weaponType\":\"pistol\",\"isTwoHanded\":false,\"name\":\"Audit small weapon\"}");
        I.Width=3;I.Height=2;return I;};
    struct FRun{int32 Checks=0,Failures=0,Phase=0;FTimerHandle Timer;FColdSteelProfile Original;FString Output;};auto R=MakeShared<FRun>();R->Original=M->Snapshot();
    R->Output=FPaths::ProjectSavedDir()/TEXT("WarehouseMigration");IFileManager::Get().MakeDirectory(*R->Output,true);
    if(FParse::Param(FCommandLine::Get(),TEXT("WarehouseChestPreview"))){
        AColdSteelWarehouseChest* C=nullptr;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It){C=*It;break;}
        if(!C){GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
        FVector Target=C->GetActorLocation()+FVector(0,0,65),Location=C->GetActorLocation()+FVector(230,230,180);
        auto* Camera=GetWorld()->SpawnActor<ACameraActor>(Location,(Target-Location).Rotation());GetOwningPlayer()->SetViewTarget(Camera);
        GetWorld()->GetTimerManager().SetTimer(R->Timer,[this,R,C](){
            if(R->Phase==0){FScreenshotRequest::RequestScreenshot(R->Output/TEXT("chest-closed.png"),false,false);}
            if(R->Phase==1)C->SetOpen(true);
            if(R->Phase==2)FScreenshotRequest::RequestScreenshot(R->Output/TEXT("chest-open.png"),false,false);
            if(R->Phase==3){UE_LOG(LogTemp,Display,TEXT("WarehousePreview: COMPLETE bounds=%s"),*C->Mesh->Bounds.BoxExtent.ToString());GetWorld()->GetTimerManager().ClearTimer(R->Timer);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));}
            ++R->Phase;
        },1.2f,true);return;
    }
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("WarehouseAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto Signature=[](const TArray<FColdSteelItem>& Items){TArray<FString> Rows;for(const auto& I:Items)Rows.Add(FString::Printf(TEXT("%s|%s|%lld|%d|%d|%d|%s"),*I.InstanceId,*I.Definition,I.Count,I.Place,I.Cell,I.Magazine,*I.Data));Rows.Sort();return FString::Join(Rows,TEXT("\n"));};
    if(FParse::Param(FCommandLine::Get(),TEXT("WarehouseLoadAudit"))){FString Expected;Check(FFileHelper::LoadFileToString(Expected,*(R->Output/M->ProfileSlot()+TEXT(".txt")))&&Expected==Signature(M->Items()),TEXT("new process exact item id data ammo place restoration"));UE_LOG(LogTemp,Display,TEXT("WarehouseAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    Check(M->WarehouseCapacity()==100,TEXT("five pages twenty slots"));
    int32 Guns=0;for(const auto& I:M->Items())if(I.Place==4&&I.Definition.StartsWith(TEXT("fps_")))++Guns;
    Check(Guns==0&&M->Snapshot().ArmoryReceived.IsEmpty(),TEXT("retired weapons are no longer granted"));
    FString Before=Signature(M->Items());Check(M->GrantStartingArmory()&&Signature(M->Items())==Before,TEXT("armory grant idempotent"));
    auto Empty=M->Snapshot();Empty.Items.Empty();Empty.Hotbar.Init(TEXT(""),4);Empty.HotbarDefinitions.Init(TEXT(""),4);
    auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Place=1;Gun.Cell=6;Gun.Magazine=7;
    auto Full=Empty;Full.Items.Add(Gun);auto Potion=M->CreateItem(TEXT("hp_potion"));
    for(int32 C=0;C<72;++C){auto I=M->CreateItem(TEXT("hp_potion"),Potion.StackMax);I.Cell=C;Full.Items.Add(I);}
    Check(M->CommitState(Full),TEXT("full backpack fixture"));
    Check(M->TransferWarehouse(Gun.InstanceId,4,99)&&!M->Equipped()&&M->FindItem(Gun.InstanceId)->Magazine==7,TEXT("equipped direct store despite full backpack preserves ammo"));
    Before=Signature(M->Items());Check(!M->TransferWarehouse(Gun.InstanceId,0)&&Before==Signature(M->Items()),TEXT("full backpack withdrawal atomic rollback"));
    Check(M->TransferWarehouse(Gun.InstanceId,4,0)&&M->FindItem(Gun.InstanceId)->Cell==0,TEXT("cross-page warehouse move"));
    Check(M->CommitState(Empty),TEXT("clear test layout"));
    auto P=Empty;auto A=M->CreateItem(TEXT("ue_m4a1"));A.Cell=0;auto B=SmallWeapon();B.Place=4;B.Cell=0;P.Items={A,B};Check(M->CommitState(P),TEXT("different footprint fixture"));
    Before=Signature(M->Items());Check(M->ProposeWarehouse(B.InstanceId,0,1).bValid&&Before==Signature(M->Items()),TEXT("hover proposal read-only"));
    Check(M->TransferWarehouse(B.InstanceId,0,1)&&M->FindItem(A.InstanceId)->Place==4&&M->FindItem(B.InstanceId)->Cell==1,TEXT("withdrawal swaps exact anchor retains both identities"));
    Before=Signature(M->Items());Check(!M->TransferWarehouse(A.InstanceId,0,17)&&Signature(M->Items())==Before,TEXT("explicit edge target cannot silently relocate"));
    auto Invalid=M->Snapshot();Invalid.Items[0].Place=4;Invalid.Items[0].Cell=100;FString Reason;Check(!Validate(Invalid,Reason),TEXT("out of bounds warehouse save rejected"));
    Check(M->CommitState(P),TEXT("save failure fixture"));Before=Signature(M->Items());M->AuditFailNextSave=true;
    Check(!M->TransferWarehouse(A.InstanceId,4,3)&&Before==Signature(M->Items()),TEXT("disk failure preserves both containers"));
    auto Stale=M->ProposeWarehouse(A.InstanceId,4,3);Check(M->SaveNow()&&!M->CommitProposal(Stale),TEXT("stale generation proposal rejected"));
    auto Stack=Empty;auto One=M->CreateItem(TEXT("hp_potion"),Potion.StackMax-1);One.Place=4;One.Cell=8;auto Two=M->CreateItem(TEXT("hp_potion"),5);Two.Cell=0;Stack.Items={One,Two};M->CommitState(Stack);
    Check(M->TransferWarehouse(Two.InstanceId,4,8)&&M->Items().Num()==2&&M->FindItem(One.InstanceId)->Count==Potion.StackMax,TEXT("explicit stack overflow fills selected stack and spills atomically"));
    M->CommitState(Stack);Check(M->TransferWarehouse(Two.InstanceId,4,9)&&M->FindItem(Two.InstanceId)->Cell==9&&M->FindItem(One.InstanceId)->Count==Potion.StackMax-1,TEXT("explicit empty warehouse target does not merge into a different cell"));
    auto Packed=Empty;for(int32 C=0;C<100;++C){auto I=M->CreateItem(TEXT("hp_potion"),Potion.StackMax);I.Place=4;I.Cell=C;Packed.Items.Add(I);}Packed.Items.Add(A);M->CommitState(Packed);Before=Signature(M->Items());
    Check(!M->TransferWarehouse(A.InstanceId,4)&&Signature(M->Items())==Before,TEXT("full warehouse atomic rejection"));
    Packed.Items[0].Count-=1;auto Extra=M->CreateItem(TEXT("hp_potion"),2);Extra.Cell=36;Packed.Items.Add(Extra);Check(M->CommitState(Packed),TEXT("partial stack fixture does not overlap five by two weapon"));Before=Signature(M->Items());
    Check(!M->TransferWarehouse(Extra.InstanceId,4,0)&&Signature(M->Items())==Before,TEXT("partial merge must roll back when remainder has no slot"));
    auto Equip=Full;auto Stored=SmallWeapon();Stored.Place=4;Stored.Cell=0;Equip.Items.Add(Stored);M->CommitState(Equip);Before=Signature(M->Items());
    Check(!M->TransferWarehouse(Gun.InstanceId,4,0)&&Signature(M->Items())==Before,TEXT("equipment displaced target needs backpack space"));
    M->CommitState(Stack);Check(M->CountMaterial(TEXT("hp_potion"))==Potion.StackMax+4,TEXT("material counts both containers"));
    Check(M->ConsumeMaterial(TEXT("hp_potion"),6)&&M->CountMaterial(TEXT("hp_potion"))==Potion.StackMax-2,TEXT("material consumption backpack before warehouse"));
    Before=Signature(M->Items());Check(!M->ConsumeMaterial(TEXT("hp_potion"),Potion.StackMax+1)&&Before==Signature(M->Items()),TEXT("material shortage rollback"));
    M->CommitState(Packed);auto Deposit=M->CreateItem(TEXT("hp_potion"),5);Check(M->WarehouseRemainingCapacity(Deposit)==1,TEXT("remaining warehouse capacity includes partial compatible stacks"));
    Check(M->DepositWarehouseAmount(Deposit)==1&&M->WarehouseRemainingCapacity(Deposit)==0,TEXT("partial deposit returns exactly accepted amount"));
    auto IsPotion=[](const FColdSteelItem& I){return I.Definition==TEXT("hp_potion");};
    Check(M->CountWarehouseMaterial(IsPotion)==100*Potion.StackMax,TEXT("predicate material count excludes backpack"));
    Before=Signature(M->Items());M->AuditFailNextSave=true;Check(M->ConsumeWarehouseMaterial(IsPotion,3)==0&&Before==Signature(M->Items()),TEXT("predicate consumption save failure rolls back"));
    Check(M->ConsumeWarehouseMaterial(IsPotion,100*Potion.StackMax+1)==100*Potion.StackMax&&M->CountWarehouseMaterial(IsPotion)==0,TEXT("predicate consumption reports partial amount without underflow"));
    M->CommitState(Empty);M->WarehousePage=4;Check(M->AddWarehouseItem(SmallWeapon())&&Owner(M->Items(),4,80)>=0,TEXT("external reward uses current page empty slot"));
    Check(M->RetrieveAllFromWarehouse()&&M->CountWarehouseMaterial([](const auto&){return true;})==0,TEXT("retrieve all preserves spatial backpack insertion"));M->WarehousePage=0;
    M->CommitState(P);Check(M->WarehouseBatch(false),TEXT("store all action"));Check(M->SortWarehouse(TEXT("price")),TEXT("price sort"));Check(M->SortWarehouse(TEXT("rarity")),TEXT("rarity sort"));Check(M->SortWarehouse(TEXT("category"),1),TEXT("category sort"));
    auto Matching=Empty;auto Small=M->CreateItem(TEXT("hp_potion"),2);auto Big=M->CreateItem(TEXT("hp_potion"),3);Big.Place=4;Big.Cell=5;Matching.Items={Small,Big,B};B.Cell=8;Matching.Items[2].Cell=8;M->CommitState(Matching);
    Check(M->WarehouseBatch(true)&&M->FindItem(Small.InstanceId)->Count==5&&M->FindItem(B.InstanceId)->Place==4,TEXT("matching withdrawal uses names and preserves unrelated items"));
    // Random transfer states must conserve all quantities and the complete per-definition metadata.
    auto Fuzz=Empty;for(int32 N=0;N<4;++N)Insert(Fuzz.Items,M->CreateItem(TEXT("ue_m4a1")));for(int32 N=0;N<12;++N){auto I=M->CreateItem(TEXT("hp_potion"),5);I.Place=4;I.Cell=N;Fuzz.Items.Add(I);}
    bool OK=true;FRandomStream Random(90921);for(int32 N=0;N<3000;++N){int32 Index=Random.RandRange(0,Fuzz.Items.Num()-1);const auto& I=Fuzz.Items[Index];int32 Dest=I.Place==4?(Random.RandRange(0,1)?4:0):4;auto Proposal=ColdSteelWarehouse::Transfer(Fuzz.Items,I.InstanceId,Dest,Random.RandRange(-1,Dest==4?102:75),100);if(Proposal.bValid){int64 Old=0,New=0;for(const auto& V:Fuzz.Items)Old+=V.Count;for(const auto& V:Proposal.Items)New+=V.Count;Fuzz.Items=Proposal.Items;if(Old!=New||!Validate(Fuzz,Reason)){OK=false;break;}}}Check(OK,TEXT("3000 randomized transfers conserve quantities and nonoverlap"));
    Check(M->CommitState(R->Original)&&M->ReloadProfile(),TEXT("restore player fixture and reload save"));
    // Visual/native drag fixtures are confined to the explicit audit save slot.
    Check(M->AddWarehouseItem(M->CreateItem(TEXT("ue_m4a1")),0),TEXT("current M4 placed in isolated warehouse preview fixture"));
    AColdSteelWarehouseChest* Chest=nullptr;for(TActorIterator<AColdSteelWarehouseChest> It(GetWorld());It;++It){Chest=*It;break;}
    Check(Chest&&Chest->ChestAsset&&Chest->OpenClip&&Chest->CloseClip,TEXT("real chest and original animation assets loaded"));
    if(!Chest){UE_LOG(LogTemp,Error,TEXT("WarehouseAudit: no chest"));GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    Check(Chest->CanInteract(GetOwningPlayerPawn()),TEXT("spawned chest reachable in source interaction radius"));GetOwningPlayer()->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1.f));
    Check(bWarehouseOpen&&bInventoryOpen&&M->WarehousePage==0&&M->bWarehouseOpen,TEXT("open real full backpack and first warehouse page"));
    Check(GetOwningPlayer()->bShowMouseCursor&&GetOwningPlayer()->IsLookInputIgnored(),TEXT("panel owns focus cursor and blocks gameplay look"));
    TWeakObjectPtr<AColdSteelWarehouseChest> WeakChest=Chest;
    GetWorld()->GetTimerManager().SetTimer(R->Timer,[this,R,M,Check,Signature,WeakChest]() mutable {
        auto* C=WeakChest.Get();if(!C){GetWorld()->GetTimerManager().ClearTimer(R->Timer);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
        if(R->Phase==0){
            Check(C->IsOpen()&&!C->IsAnimating(),TEXT("original open clip completes and holds"));
            auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;
            if(Board&&WarehouseWidget->Cells.Num()>0){
                auto* Cell=WarehouseWidget->Cells[0].Get();UDragDropOperation* Operation=nullptr;FPointerEvent Pointer(0,FVector2D::ZeroVector,FVector2D::ZeroVector,TSet<FKey>{EKeys::LeftMouseButton},EKeys::LeftMouseButton,0,FModifierKeysState());
                Cell->NativeOnDragDetected(Cell->GetCachedGeometry(),Pointer,Operation);auto* Drag=Cast<UColdSteelItemDrag>(Operation);
                if(Drag){const FString Id=Drag->ItemId;const auto Geometry=Board->GetCachedGeometry();const auto Layout=Board->Layout(Geometry);const FVector2D Screen=Geometry.LocalToAbsolute(FVector2D(14,Layout.BagY+2+2*Layout.Cell)/Board->Scale);
                    FPointerEvent P(0,Screen,Screen,TSet<FKey>{EKeys::LeftMouseButton},EKeys::LeftMouseButton,0,FModifierKeysState());FDragDropEvent E(P,TSharedPtr<FDragDropOperation>());FString Original=Signature(M->Items());
                    Check(Board->NativeOnDragOver(Geometry,E,Drag)&&Original==Signature(M->Items()),TEXT("native warehouse to backpack hover read-only"));
                    Check(Board->NativeOnDrop(Geometry,E,Drag)&&M->FindItem(Id)&&M->FindItem(Id)->Place==0&&M->FindItem(Id)->Cell==36,TEXT("native warehouse drag drops at precise spatial anchor"));
                    Drag->Drop(P);Check(Cell->GetRenderOpacity()==1,TEXT("successful drag restores source opacity"));
                    const auto* I=M->FindItem(Id);if(I){Drag->SourcePlace=I->Place;Drag->SourceCell=I->Cell;}
                    Check(Cell->NativeOnDrop(Cell->GetCachedGeometry(),E,Drag)&&M->FindItem(Id)->Place==4,TEXT("native backpack drop restores original warehouse instance"));
                    const FString BeforeStale=Signature(M->Items());const int64 StaleGeneration=M->Snapshot().Generation;
                    Board->NativeOnDrop(Geometry,E,Drag);
                    Check(Signature(M->Items())==BeforeStale&&M->Snapshot().Generation==StaleGeneration&&!Board->bPreviewValid&&Board->InteractionMessage.Contains(TEXT("重新")),TEXT("stale drag source rejected after source changes"));
                }else Check(false,TEXT("warehouse starts native drag operation"));
            }else Check(false,TEXT("live warehouse and backpack widgets available"));
            const auto W=WarehouseWidget->GetCachedGeometry(),B=InventoryPanel->GetCachedGeometry();Check(FMath::Abs(W.GetAbsolutePosition().X+W.GetAbsoluteSize().X-B.GetAbsolutePosition().X)<3,TEXT("warehouse abuts backpack without gap"));
            FScreenshotRequest::RequestScreenshot(R->Output/(M->ProfileSlot()+TEXT("-open.png")),true,false);FTimerHandle CloseLater;GetWorld()->GetTimerManager().SetTimer(CloseLater,[this,Check](){CloseWarehouse();Check(!bWarehouseOpen&&bInventoryOpen,TEXT("close warehouse retains full backpack"));},.2f,false);
        }else if(R->Phase==1){Check(!C->IsOpen()&&!C->IsAnimating(),TEXT("close motion finishes before chest settles"));OpenWarehouse(C);CloseWarehouse();OpenWarehouse(C);}
        else if(R->Phase==2){Check(C->IsOpen()&&bWarehouseOpen,TEXT("rapid open close open uses latest requested state"));M->WarehousePage=4;CloseWarehouse();OpenWarehouse(C);Check(M->WarehousePage==0,TEXT("every reopen starts on page one"));
            GetOwningPlayerPawn()->SetActorLocation(GetOwningPlayerPawn()->GetActorLocation()+FVector(1000,0,0));}
        else if(R->Phase==3){Check(!bWarehouseOpen&&bInventoryOpen,TEXT("leaving radius closes only warehouse"));SetInventoryOpen(false);Check(!GetOwningPlayer()->bShowMouseCursor&&!GetOwningPlayer()->IsLookInputIgnored(),TEXT("closing backpack restores gameplay input"));
            auto P=M->Snapshot();for(auto& I:P.Items)if(I.Place==4){I.Magazine=11;break;}M->CommitState(P);FFileHelper::SaveStringToFile(Signature(M->Items()),*(R->Output/M->ProfileSlot()+TEXT(".txt")));
            FString Summary=FString::Printf(TEXT("checks=%d failures=%d"),R->Checks,R->Failures);FFileHelper::SaveStringToFile(Summary,*(R->Output/(M->ProfileSlot()+TEXT("-result.txt"))));UE_LOG(LogTemp,Display,TEXT("WarehouseAudit: COMPLETE %s"),*Summary);
            GetWorld()->GetTimerManager().ClearTimer(R->Timer);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));}
        ++R->Phase;
    },1.5f,true);
}
