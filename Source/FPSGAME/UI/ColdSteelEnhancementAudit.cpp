#include "ColdSteelEnhancementAuditTarget.h"
#include "ColdSteelEnhancementWidget.h"
#include "M4GunsmithWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelWarehouseRules.h"
#include "ImageUtils.h"
#include "Engine/Texture2D.h"
#include "../FPSGAMEPlayerController.h"
#include "../FPSGAMECharacter.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/FPSBallisticsComponent.h"
#include "../Weapons/ColdSteelEnchantmentCombat.h"
#include "Components/BoxComponent.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "TimerManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"
#include "UnrealClient.h"
#include "Widgets/Input/SButton.h"
#include "Framework/Application/SlateApplication.h"
#include "Widgets/SWindow.h"

AColdSteelEnhancementAuditTarget::AColdSteelEnhancementAuditTarget(){auto* Box=CreateDefaultSubobject<UBoxComponent>(TEXT("Target"));SetRootComponent(Box);Box->SetBoxExtent(FVector(15,40,40));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Ignore);Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);SetCanBeDamaged(true);}
float AColdSteelEnhancementAuditTarget::TakeDamage(float Amount,const FDamageEvent&,AController*,AActor*){Received+=Amount;return Amount;}
void AFPSGAMEPlayerController::RunEnhancementAudit()
{
    auto* P=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!P||!P->IsAudit())return;
    auto* E=GetGameInstance()->GetSubsystem<UColdSteelEnhancementSystem>();auto* G=GetGameInstance()->GetSubsystem<UGunsmithSystem>();auto* C=Cast<AFPSGAMECharacter>(GetPawn());
#if WITH_EDITOR
    // Explicit screenshot-only route: no combat or transaction acceptance sequence.
    if(FParse::Param(FCommandLine::Get(),TEXT("EnhancementUIPreview")))
    {
        if(!P->ProfileSlot().StartsWith(TEXT("ColdSteel_EnhancementPreview_"))){UE_LOG(LogTemp,Error,TEXT("EnhancementPreview: requires its own profile"));ConsoleCommand(TEXT("quit"));return;}
        auto Fixture=P->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);Fixture.ActiveWeaponSlot=6;
        auto Gun=P->CreateItem(TEXT("ue_m4a1"));Gun.InstanceId=TEXT("enhancement-preview-m4");Gun.Place=1;Gun.Cell=6;
        TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);
        Data->SetNumberField(TEXT("enhanceLevel"),5);Gun.Data.Reset();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));Fixture.Items.Add(Gun);
        bool Ready=ColdSteelInventory::Insert(Fixture.Items,P->CreateItem(TEXT("ue_akm")));
        for(const auto& Pair:TArray<TPair<FString,int64>>{{TEXT("gold"),50000},{TEXT("enhancement_stone"),25},{TEXT("magic_dust"),1200},{TEXT("enchant_scroll_skeleton"),3},{TEXT("enchant_scroll_tarantula"),5}})
            Ready&=ColdSteelInventory::Insert(Fixture.Items,P->CreateItem(Pair.Key,Pair.Value));
        if(!Ready||!P->CommitState(Fixture)){UE_LOG(LogTemp,Error,TEXT("EnhancementPreview: fixture failed %s"),*P->ResultMessage());ConsoleCommand(TEXT("quit"));return;}
        // Set a demonstrative existing suffix from a pure quote; never press Confirm.
        const auto Existing=E->Quote(Gun.InstanceId,TEXT("tarantula"));
        if(Existing.Valid){auto Display=P->Snapshot();for(auto& Item:Display.Items)if(Item.InstanceId==Gun.InstanceId)Item=Existing.After;
            if(!P->CommitState(Display)){UE_LOG(LogTemp,Error,TEXT("EnhancementPreview: suffix fixture failed"));ConsoleCommand(TEXT("quit"));return;}}
        if(!OpenEnhancement(Gun.InstanceId)){UE_LOG(LogTemp,Error,TEXT("EnhancementPreview: open failed"));ConsoleCommand(TEXT("quit"));return;}
        const FString Directory=FPaths::ProjectSavedDir()/TEXT("EnhancementUIUpgrade20260913/preview");IFileManager::Get().MakeDirectory(*Directory,true);
        int32 Width=0,Height=0;GetViewportSize(Width,Height);
        auto Later=[this](float Seconds,TFunction<void()> Action){FTimerHandle Timer;GetWorldTimerManager().SetTimer(Timer,FTimerDelegate::CreateWeakLambda(this,[Action](){Action();}),Seconds,false);};
        Later(12.f,[Directory,Width](){FScreenshotRequest::RequestScreenshot(Directory/FString::Printf(TEXT("enhance-%d.png"),Width),true,false);});
        Later(15.f,[this](){if(EnhancementPanel){EnhancementPanel->SelectTab(true);EnhancementPanel->SelectScroll(TEXT("skeletonArcher"));}});
        Later(18.f,[Directory,Width](){FScreenshotRequest::RequestScreenshot(Directory/FString::Printf(TEXT("enchant-%d.png"),Width),true,false);});
        Later(21.f,[this](){CloseEnhancement();UE_LOG(LogTemp,Display,TEXT("EnhancementPreview: COMPLETE screenshots requested"));ConsoleCommand(TEXT("quit"));});
        return;
    }
#endif
    struct FRun{int32 Checks=0,Failures=0,Phase=0;FString Message;FTimerHandle Timer;FVector Start;FColdSteelProfile Final;TWeakObjectPtr<AActor> Wall;TArray<TWeakObjectPtr<AColdSteelEnhancementAuditTarget>> Targets;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("Enhancement: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto Level=[](FColdSteelItem& I,int32 N){TSharedPtr<FJsonObject> O;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),O);O->SetNumberField(TEXT("enhanceLevel"),N);I.Data.Reset();FJsonSerializer::Serialize(O.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));};
    auto Damage=[C](){return FindFProperty<FFloatProperty>(C->GetClass(),TEXT("DamagePerShot"))->GetPropertyValue_InContainer(C);};
    const FString Id=TEXT("enhancement-audit-gun");
    if(FParse::Param(FCommandLine::Get(),TEXT("EnhancementLoadAudit"))){
        const auto* I=P->FindItem(Id);Check(I&&ColdSteelInventory::Number(*I,TEXT("enhanceLevel"))==5&&E->Effect(*I,TEXT("poisonStacks"))==1&&E->Effect(*I,TEXT("piercingBonus"))==0,TEXT("fresh process restores level and replacement suffix"));
        if(I){Check(I->Magazine==13&&I->Place==1&&I->Cell==6,TEXT("fresh process preserves ammo and equipment location"));const auto S=G->Calculate(I->Definition,G->Installed(*I));Check(FMath::IsNearlyEqual(Damage(),float(E->ProcessedDamage(*I,S.Damage,P->Derived(TEXT("atk"))))),TEXT("fresh process reapplies exact runtime damage"));}
        UE_LOG(LogTemp,Display,TEXT("Enhancement: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);ConsoleCommand(TEXT("quit"));return;
    }
    {
        const auto Original=P->Snapshot();auto Legacy=Original;Legacy.Items.Empty();Legacy.Hotbar.Init(TEXT(""),4);Legacy.HotbarDefinitions.Init(TEXT(""),4);Legacy.EnhancementSupplyVersion=0;
        auto Old=P->CreateItem(TEXT("enhancement_stone"),7);Old.Place=4;Old.Cell=0;Old.StackMax=99;const FString OldId=Old.InstanceId;Legacy.Items.Add(Old);
        Check(P->CommitState(Legacy),TEXT("material migration fixture"));P->AuditFailNextSave=true;
        Check(!P->GrantEnhancementMaterials()&&P->CountMaterial(TEXT("enhancement_stone"))==7&&P->Snapshot().EnhancementSupplyVersion==0,TEXT("failed material grant rolls back all changes"));
        Check(P->GrantEnhancementMaterials()&&P->CountMaterial(TEXT("enhancement_stone"))==99999&&P->CountMaterial(TEXT("magic_dust"))==99999,TEXT("warehouse receives exactly 99999 of each material"));
        Check(P->FindItem(OldId)&&P->FindItem(OldId)->StackMax==99999&&ColdSteelWarehouse::Category(*P->FindItem(OldId))==5,TEXT("legacy identity preserved and enhancement category migrated"));
        for(const TCHAR* Def:{TEXT("enhancement_stone"),TEXT("magic_dust")}){
            const auto Item=P->CreateItem(Def);auto* Icon=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData")/ColdSteelInventory::Text(Item,TEXT("ue_icon")));
            Check(Icon&&Icon->GetSizeX()>0&&Item.StackMax==99999,TEXT("real material image imports and stack limit is 99999"));
        }
        Check(P->TransferWarehouse(OldId,0)&&P->Split(OldId,123)&&P->CountMaterial(TEXT("enhancement_stone"))==99999,TEXT("large material stack transfers and splits without loss"));
        Check(P->ConsumeMaterial(TEXT("enhancement_stone"),1)&&P->GrantEnhancementMaterials()&&P->CountMaterial(TEXT("enhancement_stone"))==99998,TEXT("consumed supply is never automatically refilled"));
        Check(P->ReloadProfile()&&P->Snapshot().EnhancementSupplyVersion==1&&P->GrantEnhancementMaterials()&&P->CountMaterial(TEXT("enhancement_stone"))==99998,TEXT("supply marker and remaining materials survive reload"));
        Check(P->CommitState(Original),TEXT("restore isolated fixture after material audit"));
    }
    auto Fixture=P->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);Fixture.ActiveWeaponSlot=6;
    auto Gun=P->CreateItem(TEXT("ue_m4a1"));Gun.InstanceId=Id;Gun.Place=1;Gun.Cell=6;Gun.Magazine=13;Level(Gun,3);Fixture.Items.Add(Gun);
    auto Other=P->CreateItem(TEXT("ue_akm"));Other.InstanceId=TEXT("enhancement-other");Other.Cell=0;Fixture.Items.Add(Other);
    auto Add=[&](const TCHAR* Def,int64 N,int32 Place,int32 Cell){auto I=P->CreateItem(Def,N);I.Place=Place;I.Cell=Cell;Fixture.Items.Add(I);};
    Add(TEXT("enhancement_stone"),1,0,8);Add(TEXT("enhancement_stone"),5,4,0);Add(TEXT("gold"),100000,4,1);Add(TEXT("magic_dust"),500,4,2);Add(TEXT("magic_dust"),500,4,5);Add(TEXT("enchant_scroll_skeleton"),2,4,3);Add(TEXT("enchant_scroll_tarantula"),3,4,4);
    Check(P->CommitState(Fixture),TEXT("isolated materials and two-weapon fixture"));
    if(R->Failures){UE_LOG(LogTemp,Error,TEXT("Enhancement: fixture rejected: %s"),*P->ResultMessage());ConsoleCommand(TEXT("quit"));return;}
    const auto Q=E->Quote(Id);const auto Generation=P->Snapshot().Generation;Check(Q.Valid&&Q.Costs.Num()==2&&Q.Costs[0].Have==6&&Q.Costs[1].Need==337&&P->Snapshot().Generation==Generation,TEXT("quote is pure and counts backpack plus warehouse materials"));
    Check(E->Apply(Q,R->Message)&&P->Snapshot().Generation==Generation+1&&ColdSteelInventory::Number(*P->FindItem(Id),TEXT("enhanceLevel"))==4,TEXT("upgrade applies as one saved transaction"));
    Check(P->CountMaterial(TEXT("enhancement_stone"))==5&&P->CountMaterial(TEXT("gold"))==99663&&P->FindItem(Id)->Magazine==13,TEXT("exact costs consumed once without changing ammunition"));
    Check(!E->Apply(Q,R->Message),TEXT("stale and repeated quote cannot charge twice"));
    const auto Fail=E->Quote(Id);const auto Before=P->Snapshot();P->AuditFailNextSave=true;
    Check(!E->Apply(Fail,R->Message)&&P->Snapshot().Generation==Before.Generation&&P->FindItem(Id)->Data==Fail.Before.Data&&P->CountMaterial(TEXT("enhancement_stone"))==5,TEXT("failed save rolls back level and all materials"));
    auto Max=P->Snapshot();for(auto& I:Max.Items)if(I.InstanceId==Id)Level(I,15);Check(P->CommitState(Max)&&!E->Quote(Id).Valid,TEXT("level cap rejects without charging"));P->CommitState(Before);
    auto Poor=P->Snapshot();Poor.Items.RemoveAll([](const auto& I){return I.Definition==TEXT("magic_dust");});P->CommitState(Poor);Check(!E->Quote(Id,TEXT("skeletonArcher")).Valid,TEXT("insufficient dust rejects before mutation"));P->CommitState(Before);
    Check(!E->Quote(Id,TEXT("heavy")).Valid&&!E->Quote(Id,TEXT("unknown")).Valid,TEXT("incompatible or unknown scroll rejects"));
    Check(E->Apply(E->Quote(Id,TEXT("skeletonArcher")),R->Message)&&E->Effect(*P->FindItem(Id),TEXT("piercingBonus"))==2,TEXT("real skeleton suffix costs and effects persist"));
    Check(P->CountMaterial(TEXT("magic_dust"))==600&&P->CountMaterial(TEXT("enchant_scroll_skeleton"))==1&&!E->Quote(Id,TEXT("skeletonArcher")).Valid,TEXT("exact scroll consumption and duplicate suffix rejection"));
    const auto Stats=G->Calculate(Gun.Definition,G->Installed(*P->FindItem(Id)));
    Check(FMath::IsNearlyEqual(Damage(),float(E->ProcessedDamage(*P->FindItem(Id),Stats.Damage,P->Derived(TEXT("atk"))))),TEXT("equipped runtime damage matches preview"));
    P->SaveNow();Check(FMath::IsNearlyEqual(Damage(),float(E->ProcessedDamage(*P->FindItem(Id),Stats.Damage,P->Derived(TEXT("atk"))))),TEXT("repeated publish does not compound upgrade"));
    const auto Tip=BuildColdSteelItemTooltip(*P->FindItem(Id),P,G);bool Has=false;for(const auto& Card:Tip.Cards)for(const auto& Row:Card.Rows)Has|=Row.Label==TEXT("穿透目标")&&Row.Value.Contains(TEXT("2"));Check(Has,TEXT("tooltip exposes saved enchant effect"));
    R->Start=C->GetActorLocation()+FVector(0,2500,1600);for(int32 N=0;N<4;++N){auto* Target=GetWorld()->SpawnActor<AColdSteelEnhancementAuditTarget>(R->Start+FVector(100+100*N,0,0),FRotator::ZeroRotator);R->Targets.Add(Target);}
    GetWorldTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(this,[this,P,E,G,C,R,Check,Damage,Id]()
    {
        auto Capture=[this](const TCHAR* Name){const FString Dir=FPaths::ProjectSavedDir()/TEXT("EnhancementAudit");IFileManager::Get().MakeDirectory(*Dir,true);const auto Size=GEngine->GameViewport->Viewport->GetSizeXY();FScreenshotRequest::RequestScreenshot(Dir/FString::Printf(TEXT("%s-%d.png"),Name,Size.X),true,false);};
        auto Click=[this](TSharedPtr<SButton> Button){const auto Geo=Button->GetCachedGeometry();const auto At=Geo.LocalToAbsolute(Geo.GetLocalSize()*.5f);auto& App=FSlateApplication::Get();FPointerEvent Down(0,At,At,TSet<FKey>{EKeys::LeftMouseButton},EKeys::LeftMouseButton,0,FModifierKeysState());FPointerEvent Up(0,At,At,TSet<FKey>{},EKeys::LeftMouseButton,0,FModifierKeysState());App.ProcessMouseMoveEvent(Up);App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Down);App.ProcessMouseButtonUpEvent(Up);};
        switch(R->Phase++){
        case 0:C->FindComponentByClass<UFPSBallisticsComponent>()->Launch(R->Start,FVector::ForwardVector,100000,600,10,nullptr,nullptr);break;
        case 1:
            Check(R->Targets[0]->Received==10&&R->Targets[1]->Received==10&&R->Targets[2]->Received==10&&R->Targets[3]->Received==0,TEXT("real projectile pierces two extra targets and stops at third"));
            Check(E->Apply(E->Quote(Id,TEXT("tarantula")),R->Message)&&E->Effect(*P->FindItem(Id),TEXT("poisonStacks"))==1&&E->Effect(*P->FindItem(Id),TEXT("piercingBonus"))==0,TEXT("replacement removes old suffix effect"));
            Check(P->CountMaterial(TEXT("magic_dust"))==400&&P->CountMaterial(TEXT("enchant_scroll_tarantula"))==2,TEXT("replacement charges one scroll and correct dust"));
            C->FindComponentByClass<UFPSBallisticsComponent>()->Launch(R->Start,FVector::ForwardVector,100000,600,10,nullptr,nullptr);break;
        case 2:{
            auto* Poison=R->Targets[0]->FindComponentByClass<UColdSteelPoisonComponent>();Check(Poison&&Poison->GetStacks()==1&&R->Targets[1]->Received==10,TEXT("wolf projectile poisons first target without obsolete penetration"));
            if(Poison){Poison->AddStacks(C,1);const float Before=R->Targets[0]->Received;for(int N=0;N<5;++N)Poison->Pulse();Check(Poison->GetStacks()==0&&R->Targets[0]->Received==Before+10,TEXT("stacked poison deals five ticks then expires"));}
            Check(OpenEnhancement(Id),TEXT("open actual enhancement panel"));break;}
        case 3:Capture(TEXT("enhance"));Check(EnhancementPanel&&EnhancementPanel->CurrentQuote().Valid,TEXT("live enhancement quote and confirm enabled"));break;
        case 4:Click(EnhancementPanel->ConfirmControl);Check(ColdSteelInventory::Number(*P->FindItem(Id),TEXT("enhanceLevel"))==5,TEXT("real Slate confirm click upgrades selected instance"));break;
        case 5:Click(EnhancementPanel->EnchantControl);break;
        case 6:Check(EnhancementPanel->IsEnchantTab(),TEXT("real Slate tab click selects enchant page"));Capture(TEXT("enchant"));break;
        case 7:{const auto Old=Damage();EnhancementPanel->SelectItem(TEXT("enhancement-other"));Check(P->Equipped()->InstanceId==Id&&Damage()==Old,TEXT("previewing backpack AKM does not equip it or change runtime"));Capture(TEXT("other-item"));break;}
        case 8:CloseEnhancement();Check(!EnhancementPanel&&!IsMoveInputIgnored()&&!IsLookInputIgnored(),TEXT("close restores gameplay input"));Check(P->ReloadProfile()&&ColdSteelInventory::Number(*P->FindItem(Id),TEXT("enhanceLevel"))==5&&E->Effect(*P->FindItem(Id),TEXT("poisonStacks"))==1,TEXT("reload restores all committed processing"));R->Final=P->Snapshot();break;
        case 9:{
            Check(E->Apply(E->Quote(Id,TEXT("skeletonArcher")),R->Message),TEXT("wall regression equips piercing suffix"));
            auto* Wall=GetWorld()->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall);Wall->SetRootComponent(Box);Wall->AddInstanceComponent(Box);Box->SetBoxExtent(FVector(10,60,60));Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);Box->SetCollisionResponseToAllChannels(ECR_Ignore);Box->SetCollisionResponseToChannel(ECC_Visibility,ECR_Block);Box->RegisterComponent();Wall->SetActorLocation(R->Start+FVector(250,0,0));R->Wall=Wall;
            for(auto& Target:R->Targets)Target->Received=0;break;}
        case 10:C->FindComponentByClass<UFPSBallisticsComponent>()->Launch(R->Start,FVector::ForwardVector,100000,600,10,nullptr,nullptr);break;
        case 11:Check(R->Targets[0]->Received==10&&R->Targets[1]->Received==10&&R->Targets[2]->Received==0&&R->Targets[3]->Received==0,TEXT("piercing stops at a wall and cannot damage targets behind it"));Check(P->CommitState(R->Final),TEXT("restore final isolated save for fresh-process reload"));break;
        case 12:Check(OpenEnhancement(Id),TEXT("reopen live workbench preview"));break;
        case 13:{
            auto* View=EnhancementPanel->WorkbenchPreview.Get();Check(View&&View->HasWorkbenchCapture()&&View->GetPreviewOrbit().IsNearlyZero(),TEXT("shared gunsmith capture starts at default horizontal orbit"));
            auto Surface=EnhancementPanel->PreviewSurface;auto& App=FSlateApplication::Get();auto Window=App.FindWidgetWindow(Surface.ToSharedRef());const auto Geometry=Surface->GetCachedGeometry();
            const FVector2D At=Geometry.LocalToAbsolute(Geometry.GetLocalSize()*.5f),To=At+FVector2D(100,40);const TSet<FKey> Held{EKeys::LeftMouseButton},None;
            App.ProcessMouseMoveEvent(FPointerEvent(0,At,At,None,FKey(),0,FModifierKeysState()),false);
            App.ProcessMouseButtonDownEvent(Window->GetNativeWindow(),FPointerEvent(0,At,At,Held,EKeys::LeftMouseButton,0,FModifierKeysState()));
            App.ProcessMouseMoveEvent(FPointerEvent(0,To,At,Held,FKey(),0,FModifierKeysState()),false);
            App.ProcessMouseButtonUpEvent(FPointerEvent(0,To,To,None,EKeys::LeftMouseButton,0,FModifierKeysState()));
            Check(!View->GetPreviewOrbit().IsNearlyZero(),TEXT("real mouse drag rotates enhancement rifle"));break;}
        case 14:Capture(TEXT("rotated"));break;
        case 15:Click(EnhancementPanel->ResetViewControl);Check(EnhancementPanel->WorkbenchPreview->GetPreviewOrbit().IsNearlyZero(),TEXT("reset button restores gunsmith default orbit"));break;
        case 16:Click(EnhancementPanel->AimViewControl);Check(EnhancementPanel->WorkbenchPreview->IsAimPreview(),TEXT("aim preview button changes camera mode"));break;
        case 17:Capture(TEXT("aim"));break;
        case 18:{const float Old=Damage();EnhancementPanel->SelectItem(TEXT("enhancement-other"));Check(P->Equipped()->InstanceId==Id&&Damage()==Old&&EnhancementPanel->WorkbenchPreview->HasWorkbenchCapture(),TEXT("backpack weapon has independent live studio without equipping"));break;}
        case 19:Capture(TEXT("backpack-live"));break;
        case 20:{auto View=EnhancementPanel->WorkbenchPreview;CloseEnhancement();Check(!View->HasWorkbenchCapture()&&!IsMoveInputIgnored(),TEXT("close releases studio and restores gameplay input"));break;}
        default:
            for(auto& T:R->Targets)if(T.IsValid())T->Destroy();if(R->Wall.IsValid())R->Wall->Destroy();GetWorldTimerManager().ClearTimer(R->Timer);
            UE_LOG(LogTemp,Display,TEXT("Enhancement: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);ConsoleCommand(TEXT("quit"));break;
        }
    }),1.f,true);
}
