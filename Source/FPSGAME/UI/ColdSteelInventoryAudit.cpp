#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelDetailRow.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/NurseZombie.h"
#include "Blueprint/WidgetLayoutLibrary.h"
#include "Blueprint/WidgetTree.h"
#include "Components/ScrollBox.h"
#include "Components/ProgressBar.h"
#include "Engine/GameInstance.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"

using namespace ColdSteelInventory;
void UColdSteelHUDWidget::RunInventoryAudit()
{
    if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelDragAudit"))){RunInventoryDragAudit();return;}
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M||!M->IsAudit())return;
    struct FRun{int32 Failures=0,Checks=0,Phase=0;FTimerHandle Timer;FColdSteelProfile Original;};auto Run=MakeShared<FRun>();Run->Original=M->Snapshot();
    auto Check=[Run](bool Pass,const TCHAR* Name){++Run->Checks;if(!Pass)++Run->Failures;UE_LOG(LogTemp,Display,TEXT("ColdSteelInventory: %s %s"),Pass?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto Fingerprint=[](const FColdSteelProfile& P){FString S=FString::Printf(TEXT("%d|%lld|%d|%d"),P.Level,P.Experience,P.Points,P.Kills);TArray<FString> Rows;for(const auto& I:P.Items)Rows.Add(FString::Printf(TEXT("%s|%s|%lld|%d|%d|%d|%s"),*I.InstanceId,*I.Definition,I.Count,I.Place,I.Cell,I.Magazine,*I.Data));Rows.Sort();for(auto& R:Rows)S+=TEXT("\n")+R;for(auto& K:P.Hotbar)S+=TEXT("\nH:")+K;TArray<FName> Keys;P.Attributes.GetKeys(Keys);Keys.Sort(FNameLexicalLess());for(auto K:Keys)S+=FString::Printf(TEXT("\n%s=%d"),*K.ToString(),P.Attributes[K]);return S;};
    if(FParse::Param(FCommandLine::Get(),TEXT("ColdSteelInventoryLoadAudit"))){FString Expected;const FString File=FPaths::ProjectSavedDir()/TEXT("InventoryMigration")/(M->ProfileSlot()+TEXT(".fingerprint"));Check(FFileHelper::LoadFileToString(Expected,*File)&&Expected==Fingerprint(M->Snapshot()),TEXT("fresh process restores exact inventory identifiers ammo growth and bindings"));UE_LOG(LogTemp,Display,TEXT("ColdSteelInventory: COMPLETE checks=%d failures=%d"),Run->Checks,Run->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));return;}
    auto Same=[](const TArray<FColdSteelItem>& A,const TArray<FColdSteelItem>& B){if(A.Num()!=B.Num())return false;for(int32 N=0;N<A.Num();++N)if(A[N].InstanceId!=B[N].InstanceId||A[N].Count!=B[N].Count||A[N].Place!=B[N].Place||A[N].Cell!=B[N].Cell||A[N].Data!=B[N].Data)return false;return true;};
    Check(Run->Original.Generation>0&&M->Equipped(),TEXT("new profile saved and actual equipped instance exists"));
    auto Base=Run->Original;Base.Level=1;Base.Experience=0;Base.Points=0;Base.Kills=0;for(auto& A:Base.Attributes)A.Value=10;
    Check(M->CommitState(Base),TEXT("isolated audit profile reset"));
    Check(M->MaxExperience()==416,TEXT("source level one experience threshold 416"));
    Check(!M->GainExperience(-1),TEXT("negative XP rejected"));
    Check(M->GainExperience(416+864+17)&&M->Level==3&&M->AttributePoints==6&&M->Experience()==17,TEXT("multi-level XP preserves remainder and gives three points per level"));
    // Level two cost: (20 + 40 + 48) * 8 = 864.
    const float BeforeMax=M->Derived(TEXT("maxHp"));
    Check(M->AllocateAttribute(TEXT("con"))&&M->Derived(TEXT("maxHp"))==BeforeMax+10,TEXT("attribute allocation changes derived health"));
    const int32 Points=M->AttributePoints;Check(!M->AllocateAttribute(TEXT("unknown"))&&M->AttributePoints==Points,TEXT("invalid allocation leaves points unchanged"));
    auto* Pawn=GetOwningPlayerPawn<AFPSGAMECharacter>();auto* H=Pawn?Pawn->FindComponentByClass<UFPSCombatHealthComponent>():nullptr;
    Check(H&&H->MaxHealth==M->Derived(TEXT("maxHp")),TEXT("constitution applied to actual player maximum health"));
    auto* Victim=GetWorld()->SpawnActor<AActor>();Check(M->AwardKill(Victim,241)&&!M->AwardKill(Victim,241)&&M->Kills()==1,TEXT("death reward cannot be claimed twice"));if(Victim)Victim->Destroy();
    auto Empty=M->Snapshot();Empty.Items.Empty();Empty.Hotbar.Init(TEXT(""),4);Empty.HotbarDefinitions.Init(TEXT(""),4);
    Check(M->CommitState(Empty),TEXT("inventory fixture starts empty"));
    const int64 StackLimit=M->CreateItem(TEXT("hp_potion")).StackMax;
    Check(StackLimit==99,TEXT("loaded source catalog overrides potion stack limit to 99"));
    Check(M->AddItem(TEXT("hp_potion"),StackLimit*2+2)&&M->Items().Num()==3,TEXT("insert splits counts at source stack limit"));
    int64 Total=0;for(const auto& I:M->Items())Total+=I.Count;Check(Total==StackLimit*2+2,TEXT("insert preserves every unit"));
    FString Potion=M->Items()[0].InstanceId;Check(M->Split(Potion,2)&&M->FindItem(Potion)->Count==StackLimit-2,TEXT("stack split preserves source instance"));
    auto Before=M->Items();Check(!M->Split(Potion,100)&&Same(Before,M->Items()),TEXT("invalid split atomic"));
    Check(M->BindHotbar(0,Potion),TEXT("consumable binds to shortcut"));
    Check(M->AddItem(TEXT("ue_m4a1"),1),TEXT("long gun inserts"));
    const auto* Gun=M->Items().FindByPredicate([](const auto&I){return I.Definition==TEXT("ue_m4a1");});const FString GunId=Gun?Gun->InstanceId:TEXT("");
    Check(Gun&&Gun->Width==5&&Gun->Height==2&&!M->BindHotbar(1,GunId),TEXT("rifle footprint and consumable-only shortcut"));
    Before=M->Items();Check(!M->MoveItem(GunId,0,17)&&Same(Before,M->Items()),TEXT("explicit edge drop rejects without relocation"));
    Check(M->MoveItem(GunId,1,6)&&Locked(M->Items(),8),TEXT("two handed equip locks offhand"));
    Check(M->MoveItem(GunId,0,36),TEXT("unequip uses exact requested rectangle"));
    Check(M->MoveItem(GunId,1,9)&&M->Equipped()&&M->Equipped()->InstanceId==GunId,TEXT("equipping second weapon selects that actual instance"));
    Check(M->MoveItem(GunId,0,-1)&&M->FindItem(GunId)->Cell==36,TEXT("automatic unequip prefers remembered backpack anchor"));
    auto Proposal=M->ProposeMove(GunId,0,45);Before=M->Items();Check(Same(Before,M->Items()),TEXT("drag preview is read only"));
    M->SaveNow();Check(!M->CommitProposal(Proposal),TEXT("stale proposal rejects after revision changes"));
    M->AuditFailNextSave=true;Before=M->Items();Check(!M->MoveItem(GunId,0,45)&&Same(Before,M->Items()),TEXT("save failure rolls back the inventory operation"));
    Check(M->Sort(),TEXT("sort repacks without dropping instances"));
    // Full grid rollback fixture, including weapon equipment replacement.
    auto Full=Empty;auto Equipped=M->CreateItem(TEXT("ue_m4a1"));Equipped.Place=1;Equipped.Cell=6;Full.Items.Add(Equipped);
    for(int32 C=0;C<72;++C){auto I=M->CreateItem(TEXT("hp_potion"),StackLimit);I.Cell=C;Full.Items.Add(I);}
    Check(M->CommitState(Full),TEXT("full backpack fixture validates"));Before=M->Items();
    Check(!M->MoveItem(Equipped.InstanceId,0,-1)&&Same(Before,M->Items()),TEXT("full bag unequip keeps equipped item"));
    Check(!M->AddItem(TEXT("hp_potion"),1)&&Same(Before,M->Items()),TEXT("full-stack add fails without partial insertion"));
    Check(!M->Split(M->Items()[1].InstanceId,1)&&Same(Before,M->Items()),TEXT("full bag split fails without loss"));
    auto Invalid=Full;Invalid.Items.Last().Cell=0;FString Reason;Check(!Validate(Invalid,Reason),TEXT("overlapping save placements rejected"));Invalid=Full;Invalid.Items.Last().InstanceId=Invalid.Items[0].InstanceId;Check(!Validate(Invalid,Reason),TEXT("duplicate instance IDs rejected"));
    // Deterministic random moves exercise both rectangles and stack conservation.
    auto Fuzz=Empty;for(int32 N=0;N<4;++N)Insert(Fuzz.Items,M->CreateItem(TEXT("ue_m4a1")));for(int32 N=0;N<8;++N)Insert(Fuzz.Items,M->CreateItem(TEXT("hp_potion"),5));
    FRandomStream Random(909);bool FuzzOK=true;for(int32 N=0;N<2000;++N){auto Prev=Fuzz.Items;int32 Index=Random.RandRange(0,Fuzz.Items.Num()-1);auto R=ColdSteelInventory::Move(Fuzz.Items,Fuzz.Items[Index].InstanceId,0,Random.RandRange(-1,75));if(R.bValid){Fuzz.Items=R.Items;int64 A=0,B=0;for(auto&I:Prev)A+=I.Count;for(auto&I:Fuzz.Items)B+=I.Count;if(A!=B||!Validate(Fuzz,Reason)){FuzzOK=false;break;}}}Check(FuzzOK,TEXT("2000 random moves conserve counts and valid nonoverlapping geometry"));
    Check(M->CommitState(Base),TEXT("restore gameplay inventory fixture"));
    Check(M->AddItem(TEXT("ue_m4a1")),TEXT("explicit bag rifle fixture prevents UI tests silently skipping"));
    const auto* SecondGun=M->Items().FindByPredicate([](const auto&I){return I.Definition==TEXT("ue_m4a1")&&I.Place==0;});
    if(SecondGun){const FString SecondId=SecondGun->InstanceId;Check(M->MoveItem(SecondId,1,9)&&M->CycleWeapon()&&M->Snapshot().ActiveWeaponSlot==6,TEXT("weapon cycle selects only equipped slots and saves active pair"));M->MoveItem(SecondId,0,-1);}
    auto Test=M->Snapshot();Test.Health=80;Test.Mana=100;M->CommitState(Test);
    const auto* HP=M->Items().FindByPredicate([](const auto&I){return I.Definition==TEXT("hp_potion")&&I.Place==0;});const FString HPId=HP?HP->InstanceId:TEXT("");
    if(H)H->Health=70;
    Check(M->BindHotbar(0,HPId)&&H&&H->Health==70,TEXT("binding shortcut preserves damage since last checkpoint"));
    Check(M->UseHotbar(0)&&H&&H->Health==100,TEXT("shortcut consumes potion and heals actual player"));
    Check(M->FindItem(HPId)&&M->FindItem(HPId)->Count==4,TEXT("use decrements exactly one unit"));
    auto Reload=M->Snapshot();for(auto& I:Reload.Items)if(I.Place==1&&I.Cell==6)I.Magazine=10;M->CommitState(Reload);
    const int32 AmmoBefore=M->AmmoCount();
    Check(M->ConsumeAmmo(20)==20&&Pawn&&Pawn->GetMagazineAmmo()==30&&M->AmmoCount()==AmmoBefore-20,TEXT("reload transfers backpack ammunition into magazine exactly once"));
    auto CD=M->Snapshot();for(auto& I:CD.Items)if(I.InstanceId==HPId)I.Cooldown=5;M->CommitState(CD);Check(!M->UseItem(HPId),TEXT("cooldown prevents repeated use"));
    const auto Saved=M->Snapshot();Check(M->ReloadProfile()&&Same(Saved.Items,M->Items())&&M->Level==Saved.Level&&M->AttributePoints==Saved.Points,TEXT("save load round trip retains items progression and cooldown"));
    const FString LatestSlot=M->ProfileSlot()+(Saved.Generation%2?TEXT("_A.sav"):TEXT("_B.sav"));const FString LatestFile=FPaths::ProjectSavedDir()/TEXT("SaveGames")/LatestSlot;
    TArray<uint8> ValidBytes;if(FFileHelper::LoadFileToArray(ValidBytes,*LatestFile)){
        const TArray<uint8> BadBytes={0,1,2,3};FFileHelper::SaveArrayToFile(BadBytes,*LatestFile);
        Check(M->ReloadProfile()&&M->Snapshot().Generation<Saved.Generation,TEXT("corrupt latest slot falls back to previous valid generation"));
        FFileHelper::SaveArrayToFile(ValidBytes,*LatestFile);Check(M->ReloadProfile()&&M->Snapshot().Generation==Saved.Generation,TEXT("restored slot recovers latest generation"));
    }else Check(false,TEXT("audit save file available for isolated corruption test"));
    Check(M->Drop(HPId)&&M->FindItem(HPId)->Place==2,TEXT("drop retains world instance in save"));
    Check(M->Pickup(HPId)&&!M->Pickup(HPId),TEXT("nearby pickup commits once"));
    // Actual monster death callback, isolated actor; no shared scene actor is changed.
    if(Pawn){auto* Nurse=GetWorld()->SpawnActor<ANurseZombie>(Pawn->GetActorLocation()+FVector(5000,0,0),FRotator::ZeroRotator);if(Nurse){int32 K=M->Kills();UGameplayStatics::ApplyDamage(Nurse,10000,GetOwningPlayer(),Pawn,nullptr);Check(M->Kills()==K+1,TEXT("real nurse death grants player experience once"));Nurse->Destroy();}}
    M->GrantAttributePoints(3);RefreshCharacterSheet();Check(CharacterRows[TEXT("exp")]->GetValue()!=TEXT("—")&&ExperienceBar->GetPercent()>=0,TEXT("experience and available allocation bind to actual UI"));
    OpenStatus();
    GetWorld()->GetTimerManager().SetTimer(Run->Timer,FTimerDelegate::CreateWeakLambda(this,[this,M,Run,Check,Fingerprint]()
    {
        const FVector2D Pixels=UWidgetLayoutLibrary::GetViewportSize(this);const FString Dir=FPaths::ProjectSavedDir()/TEXT("InventoryMigration/2026-09-09");IFileManager::Get().MakeDirectory(*Dir,true);
        auto Capture=[&](const TCHAR* Name){FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%dx%d.png"),Name,int32(Pixels.X),int32(Pixels.Y)),true,false);};
        auto* Scroll=Cast<UScrollBox>(EquipmentPage);auto* Board=Scroll?Cast<UColdSteelInventoryWidget>(Scroll->GetChildAt(0)):nullptr;
        switch(Run->Phase++){
        case 0:Capture(TEXT("growth"));break;
        case 1:SetInventoryTab(false);break;
        case 2:
            Check(Board&&Board->GetCachedGeometry().GetLocalSize().X>0,TEXT("interactive inventory board has live geometry"));
            if(Board){
                Board->SetKeyboardFocus();
                const auto Geometry=Board->GetCachedGeometry();const auto Metrics=Board->Layout(Geometry);
                auto HitAt=[&](FVector2D P,int32 ExpectedPlace,int32 ExpectedCell){int32 Place=-1,Cell=-1;return Board->Hit(Geometry,Geometry.LocalToAbsolute(P/Board->Scale),Place,Cell)&&Place==ExpectedPlace&&Cell==ExpectedCell;};
                bool GearHits=true;for(int32 N=0;N<15;++N)GearHits&=HitAt(FVector2D(12+N%3*(Metrics.GearWidth+6)+Metrics.GearWidth*.5f,Metrics.GearY+N/3*Metrics.GearPitch+Metrics.GearHeight-2),1,N);
                Check(GearHits&&Metrics.GearHeight>=52,TEXT("enlarged equipment cards hit all fifteen lower edges correctly"));
                Check(HitAt(FVector2D(12+17.5f*Metrics.Cell,Metrics.BagY+3.5f*Metrics.Cell),0,71),TEXT("relocated backpack last cell remains reachable"));
                int32 GapPlace=-1,GapCell=-1;
                Check(!Board->Hit(Geometry,Geometry.LocalToAbsolute(FVector2D(20,Metrics.GearY+Metrics.GearHeight+3)/Board->Scale),GapPlace,GapCell),TEXT("equipment spacing does not activate adjacent slots"));
                const auto* Gun=M->Items().FindByPredicate([](const auto&I){return I.Definition==TEXT("ue_m4a1")&&I.Place==0;});
                if(Gun){
                    auto* Drag=NewObject<UColdSteelItemDrag>(Board);Drag->ItemId=Gun->InstanceId;Drag->SourcePlace=Gun->Place;Drag->SourceCell=Gun->Cell;
                    const FGeometry G=Board->GetCachedGeometry();const auto Layout=Board->Layout(G);
                    auto EventAt=[&](FVector2D Local){FVector2D Screen=G.LocalToAbsolute(Local/Board->Scale);FPointerEvent Pointer(0,Screen,Screen,TSet<FKey>{EKeys::LeftMouseButton},EKeys::LeftMouseButton,0,FModifierKeysState());return FDragDropEvent(Pointer,TSharedPtr<FDragDropOperation>());};
                    auto BagEvent=EventAt(FVector2D(14,Layout.BagY+2+2*Layout.Cell));
                    const int64 Revision=M->Snapshot().Generation;
                    Check(Board->NativeOnDragOver(G,BagEvent,Drag)&&M->Snapshot().Generation==Revision,TEXT("native drag preview does not commit"));
                    Check(Board->NativeOnDrop(G,BagEvent,Drag)&&M->FindItem(Drag->ItemId)->Cell==36,TEXT("native spatial drop commits target cell"));
                    Drag->SourcePlace=M->FindItem(Drag->ItemId)->Place;Drag->SourceCell=M->FindItem(Drag->ItemId)->Cell;
                    auto GearEvent=EventAt(FVector2D(16,Layout.GearY+2*Layout.GearPitch+2));
                    Check(Board->NativeOnDrop(G,GearEvent,Drag)&&M->Equipped()&&M->Equipped()->InstanceId==Drag->ItemId,TEXT("native equip drop replaces main hand atomically"));
                    const auto* Character=GetOwningPlayerPawn<AFPSGAMECharacter>();
                    Check(Character&&Character->bUseM4Infima&&Character->HasInventoryWeapon(),TEXT("equipping native M4 switches actual first person weapon"));
                }
                Board->SelectItem(M->Equipped()?M->Equipped()->InstanceId:TEXT(""));
            }
            Capture(TEXT("inventory"));break;
        case 3:if(Scroll)Scroll->ScrollToEnd();break;
        case 4:Capture(TEXT("inventory-actions"));break;
        default:SetInventoryOpen(false);Check(!GetOwningPlayer()->IsMoveInputIgnored(),TEXT("inventory closes and releases movement"));M->SaveNow();FFileHelper::SaveStringToFile(Fingerprint(M->Snapshot()),*(FPaths::ProjectSavedDir()/TEXT("InventoryMigration")/(M->ProfileSlot()+TEXT(".fingerprint"))));GetWorld()->GetTimerManager().ClearTimer(Run->Timer);UE_LOG(LogTemp,Display,TEXT("ColdSteelInventory: COMPLETE checks=%d failures=%d"),Run->Checks,Run->Failures);GetOwningPlayer()->ConsoleCommand(TEXT("quit"));
        }
    }),1.f,true);
}
