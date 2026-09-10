#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelDragVisual.h"
#include "Framework/Application/SlateApplication.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Widgets/SWindow.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelUIStyle.h"
#include "Components/ScrollBox.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "UnrealClient.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
using namespace ColdSteelInventory;
void UColdSteelHUDWidget::RunInventoryVisualAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!P->IsAudit())return;
    auto* Icons=GetGameInstance()->GetSubsystem<UColdSteelWeaponIcons>();
    struct FRun{int32 Phase=0,Checks=0,Failures=0,Frame=0;FColdSteelProfile Fixture;FTimerHandle Timer,AnimationTimer;FString Gun,Potion;FVector2D Start,Last,Anchor,VisualSize;TWeakObjectPtr<UColdSteelItemDrag> Drag;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("InventoryVisualAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto State=P->Snapshot();State.Items.Empty();State.Hotbar.Init(TEXT(""),4);State.HotbarDefinitions.Init(TEXT(""),4);
    const TCHAR* Rarities[]={TEXT("common"),TEXT("uncommon"),TEXT("rare"),TEXT("epic"),TEXT("mythic"),TEXT("legendary")};
    for(int32 N=0;N<6;++N){auto I=P->CreateItem(TEXT("ue_m4a1"));I.Place=N<2?1:0;I.Cell=N<2?6+N*3:N==5?36:(N-2)*5;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);Data->SetStringField(TEXT("rarity"),Rarities[N]);
        if(N%2){auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("optic"),TEXT("holographic"));Parts->SetStringField(TEXT("magazine"),TEXT("large_drum"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);}
        if(N==1||N==5){Data->SetNumberField(TEXT("enhanceLevel"),10);auto Enchant=MakeShared<FJsonObject>();auto Prefix=MakeShared<FJsonObject>();Prefix->SetStringField(TEXT("name"),TEXT("沉重"));Enchant->SetObjectField(TEXT("prefix"),Prefix);Data->SetObjectField(TEXT("_enchantData"),Enchant);}
        I.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));State.Items.Add(I);if(N==2)R->Gun=I.InstanceId;
    }
    auto Potion=P->CreateItem(TEXT("hp_potion"),99);Potion.Cell=46;State.Items.Add(Potion);R->Potion=Potion.InstanceId;State.Hotbar[0]=Potion.InstanceId;State.HotbarDefinitions[0]=Potion.Definition;
    Check(P->CommitState(State),TEXT("isolated rarity processing stack and equipment fixture"));R->Fixture=P->Snapshot();SetInventoryOpen(true);SetInventoryTab(false);GetOwningPlayer()->SetMouseLocation(1,1);
    GetWorld()->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,P,Icons,R,Check](){
        if(!Icons->IsIdle())return;auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;if(!Board)return;
        const auto G=Board->GetCachedGeometry();const auto L=Board->Layout(G);const int32 Width=UWidgetLayoutLibrary::GetViewportSize(this).X;
        auto Shot=[&](const TCHAR* Name){HideItemTooltip(true);const FString Dir=FPaths::ProjectSavedDir()/TEXT("InventoryVisual");IFileManager::Get().MakeDirectory(*Dir,true);FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%d.png"),Name,Width),true,false);};
        if(FParse::Param(FCommandLine::Get(),TEXT("InventoryDragVisualAudit"))&&R->Phase>=5&&R->Phase<18){
            auto& App=FSlateApplication::Get();
            auto Pointer=[](FVector2D At,FVector2D Last,bool Down,FKey Key=EKeys::Invalid){return FPointerEvent(0,At,Last,Down?TSet<FKey>{EKeys::LeftMouseButton}:TSet<FKey>{},Key,0,FModifierKeysState());};
            auto Move=[&](FVector2D At){App.ProcessMouseMoveEvent(Pointer(At,R->Last,true));R->Last=At;};
            auto Press=[&](FVector2D At){R->Start=R->Last=At;App.ProcessMouseMoveEvent(Pointer(At,At,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(At,At,true,EKeys::LeftMouseButton));};
            auto Release=[&](){App.ProcessMouseButtonUpEvent(Pointer(R->Last,R->Last,false,EKeys::LeftMouseButton));};
            auto Gear=G.LocalToAbsolute(FVector2D(12+L.GearWidth*.46,L.GearY+2*L.GearPitch+L.GearHeight*.65)/Board->Scale);
            auto Bag=G.LocalToAbsolute(FVector2D(12+14.5*L.Cell,L.BagY+3.5*L.Cell)/Board->Scale);
            const FString Equipped=R->Fixture.Items[0].InstanceId;
            switch(R->Phase++-5){
            case 0:Board->PreviewPlace=-1;Scroll->ScrollToEnd();HideItemTooltip(true);break;
            case 1:Press(Gear);break;
            case 2:{
                Move(R->Start+FVector2D(12,0));R->Drag=Board->ActivePointerDrag;
                auto* D=R->Drag.Get();Check(App.IsDragDropping()&&D&&D->PointerVisual&&D->PointerVisual->IsInViewport(),TEXT("real equipment drag creates pointer overlay immediately"));
                if(D&&D->PointerVisual){R->Anchor=R->Last-D->PointerVisual->ScreenOrigin();R->VisualSize=D->PointerVisual->ScreenSize();
                    bool Follows=true;for(const FVector2D Delta:{FVector2D(23,7),FVector2D(-9,11),FVector2D(5,-13)}){Move(R->Last+Delta);Follows&=(D->PointerVisual->ScreenOrigin()+R->Anchor-R->Last).Size()<.01;}
                    Check(Follows,TEXT("first 150ms pointer moves have zero interpolation or accumulated lag"));}
                Shot(TEXT("drag-start"));break;}
            case 3:Move(Bag);Check(Board->bPreviewValid&&Board->PreviewCell==48,TEXT("equipment center grab resolves legal bag footprint"));Shot(TEXT("drag-to-bag"));break;
            case 4:{auto* D=R->Drag.Get();Check(D&&D->PointerVisual&&(D->PointerVisual->ScreenOrigin()+R->Anchor-R->Last).Size()<.01&&D->PointerVisual->ScreenSize().Equals(R->VisualSize)&&D->Offset.IsZero(),TEXT("crossing gear to bag keeps exact anchor size and zero snap offset"));Check(D&&D->PointerVisual&&D->PointerVisual->GetCachedGeometry().GetLocalSize().X>500,TEXT("drag overlay has full viewport paint geometry"));Release();break;}
            case 5:Check(P->FindItem(Equipped)->Place==0&&P->FindItem(Equipped)->Cell==48&&!App.IsDragDropping()&&(!R->Drag.IsValid()||!R->Drag->PointerVisual),TEXT("release commits once and removes overlay"));Shot(TEXT("drag-dropped"));break;
            case 6:Press(Bag);break;
            case 7:Move(Bag+FVector2D(12,0));R->Drag=Board->ActivePointerDrag;Move(Gear);Shot(TEXT("drag-to-gear"));break;
            case 8:Release();Check(P->FindItem(Equipped)->Place==1&&P->FindItem(Equipped)->Cell==6,TEXT("reverse drag equips original instance"));break;
            case 9:Press(Gear);break;
            case 10:Move(Gear+FVector2D(12,0));R->Drag=Board->ActivePointerDrag;App.CancelDragDrop();Release();Check(!App.IsDragDropping()&&(!R->Drag.IsValid()||!R->Drag->PointerVisual)&&P->FindItem(Equipped)->Place==1,TEXT("cancellation removes overlay and preserves source"));break;
            case 11:Press(Gear);break;
            case 12:Move(Gear+FVector2D(12,0));R->Drag=Board->ActivePointerDrag;SetInventoryOpen(false);App.CancelDragDrop();Release();Check(!R->Drag.IsValid()||!R->Drag->PointerVisual,TEXT("closing inventory cleans up active visual"));break;
            }
            return;
        }
        switch(R->Phase++){
        case 0:{
            bool Hits=true;for(int32 N=0;N<72;++N){int32 Place,Cell;Hits&=Board->Hit(G,G.LocalToAbsolute(FVector2D(12+(N%18+.5f)*L.Cell,L.BagY+(N/18+.5f)*L.Cell)/Board->Scale),Place,Cell)&&Place==0&&Cell==N;}
            Check(Hits,TEXT("all 72 painted bag cells match interaction coordinates"));
            Check(Board->Presentation.Num()==P->Items().Num(),TEXT("presentation cache reflects all current instances"));
            bool Badges=true;for(const auto& I:P->Items()){const auto* A=Board->Presentation.Find(I.InstanceId);if(I.Definition==TEXT("ue_m4a1"))Badges&=A&&!ColdSteelUI::RarityLabel(A->Rarity).IsEmpty();if(I.Cell==36)Badges&=A&&A->Crafted&&A->Enchanted&&A->Enhancement==10;}
            Check(Badges,TEXT("six rarity labels and saved processing badges present"));Check(L.HotY+85<=L.Height,TEXT("feedback and key hints inside scroll content"));Shot(TEXT("overview"));break;}
        case 1:Board->Selected=R->Gun;Board->HoverPlace=0;Board->PointerCell=0;Scroll->ScrollToEnd();Shot(TEXT("selected"));break;
        case 2:{const auto Proposal=P->ProposeMove(R->Gun,0,71);Check(!Proposal.bValid,TEXT("edge rejection preview uses real inventory proposal"));Board->HoverPreview=R->Gun;Board->PreviewPlace=0;Board->PreviewCell=71;Board->bPreviewValid=Proposal.bValid;Board->PreviewReason=Proposal.Reason;Shot(TEXT("rejected"));break;}
        case 3:{const auto Proposal=P->ProposeMove(R->Gun,0,48);Check(Proposal.bValid,TEXT("free destination preview uses real inventory proposal"));Board->PreviewCell=48;Board->bPreviewValid=Proposal.bValid;Board->PreviewReason=Proposal.bValid?TEXT("松开放置 / 交换物品"):Proposal.Reason;Shot(TEXT("allowed"));break;}
        case 4:
            if(FParse::Param(FCommandLine::Get(),TEXT("InventoryCornerGlintAudit"))){
                Board->PreviewPlace=-1;Board->Selected.Empty();Board->HoverPlace=-1;Scroll->ScrollToEnd();
                if(R->Frame==0){R->Frame=1;GetWorld()->GetTimerManager().SetTimer(R->AnimationTimer,FTimerDelegate::CreateWeakLambda(this,[this,R,Width](){
                    const FString Name=FPaths::ProjectSavedDir()/TEXT("InventoryVisual")/FString::Printf(TEXT("glint-%d-%02d.png"),Width,R->Frame-1);
                    HideItemTooltip(true);FScreenshotRequest::RequestScreenshot(Name,true,false);
                    if(++R->Frame>32)GetWorld()->GetTimerManager().ClearTimer(R->AnimationTimer);
                }),.12f,true);}
                if(R->Frame<=32)--R->Phase;
            }
            break;
        default:{
            const auto Current=P->Snapshot();bool Same=Current.Items.Num()==R->Fixture.Items.Num()&&Current.Hotbar==R->Fixture.Hotbar&&Current.ActiveWeaponSlot==R->Fixture.ActiveWeaponSlot;
            for(const auto& Before:R->Fixture.Items){const auto* After=P->FindItem(Before.InstanceId);Same&=After&&After->Data==Before.Data&&After->Count==Before.Count&&After->Place==Before.Place&&After->Cell==Before.Cell&&After->Magazine==Before.Magazine&&After->Reserve==Before.Reserve;}
            // The normal five-second autosave advances Generation even without user writes.
            Check(Same,TEXT("visual browsing preserves exact item data positions counts ammo and hotbar"));Board->CancelInteraction();SetInventoryOpen(false);GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("InventoryVisualAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));break;}
        }
    }),1.f,true);
}
