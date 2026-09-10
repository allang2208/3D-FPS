#include "ColdSteelHUDWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelPickupStudio.h"
#include "ColdSteelPickup.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelWarehouseWidget.h"
#include "Camera/PlayerCameraManager.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "Components/ScrollBox.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/StaticMesh.h"
#include "Rendering/SkeletalMeshRenderData.h"
#include "Serialization/JsonSerializer.h"
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

static FString PickupRecipeFingerprint(AColdSteelPickup* Pickup)
{
    auto* Asset=Cast<USkeletalMesh>(Pickup->Weapon->GetSkinnedAsset());if(!Asset)return TEXT("missing model");
    FString Result=Asset->GetPathName()+Pickup->Body->GetUnscaledBoxExtent().ToString()+Pickup->Weapon->GetRelativeTransform().ToString();
    if(const auto* Render=Asset->GetResourceForRendering())for(int32 L=0;L<Render->LODRenderData.Num();++L)
        for(const auto& S:Render->LODRenderData[L].RenderSections)Result+=Pickup->Weapon->IsMaterialSectionShown(S.MaterialIndex,L)?TEXT("1"):TEXT("0");
    TArray<UStaticMeshComponent*> Components;Pickup->GetComponents(Components);TArray<FString> Parts;
    for(auto* C:Components)if(C->IsVisible()&&C->GetStaticMesh())Parts.Add(C->GetStaticMesh()->GetPathName()+C->GetRelativeTransform().ToString());
    Parts.Sort();for(const auto& Part:Parts)Result+=Part;return Result;
}

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
        case 13:{auto State=M->Snapshot();for(auto& I:State.Items)if(I.InstanceId==R->Id){I.Place=0;I.Cell=0;}Check(M->CommitState(State),TEXT("restore item for close boundary tests"));SetInventoryOpen(true);break;}
        case 14:Board->SelectItem(R->Id);Board->OpenItemMenu(R->Start,false);break;
        case 15:Click(R->Outside);Check(!bInventoryOpen&&!PC->bShowMouseCursor,TEXT("outside click closes backpack through detached item popup"));SetInventoryOpen(true);break;
        case 16:App.ProcessMouseMoveEvent(Pointer(R->Start,R->Outside,false));App.ProcessMouseButtonDownEvent(GEngine->GameViewport->GetWindow()->GetNativeWindow(),Pointer(R->Start,R->Start,true,EKeys::LeftMouseButton));break;
        case 17:App.ProcessMouseMoveEvent(Pointer(R->Start+FVector2D(12,0),R->Start,true));break;
        case 18:App.ProcessMouseMoveEvent(Pointer(R->Outside,R->Start+FVector2D(12,0),true));Check(App.IsDragDropping(),TEXT("TAB cancellation fixture has active outside drag"));Tab();Check(!bInventoryOpen&&!App.IsDragDropping(),TEXT("TAB cancels active outside drag and closes backpack"));break;
        case 19:App.ProcessMouseButtonUpEvent(Pointer(R->Outside,R->Outside,false,EKeys::LeftMouseButton));Check(M->FindItem(R->Id)&&M->FindItem(R->Id)->Place==0,TEXT("release after TAB cancellation does not discard item"));break;
        case 20:{auto* Chest=GetWorld()->SpawnActor<AColdSteelWarehouseChest>(FVector(50145,50000,5010),FRotator::ZeroRotator);FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((Chest->GetActorLocation()+FVector(0,0,40)-Eye).Rotation());PC->PlayerCameraManager->UpdateCamera(0);OpenWarehouse(Chest);Check(bWarehouseOpen,TEXT("focused warehouse opens for close boundary tests"));break;}
        case 21:{const auto WG=WarehouseWidget->GetCachedGeometry();Click(WG.LocalToAbsolute(WG.GetLocalSize()*FVector2D(.5,.08)));Check(bWarehouseOpen&&bInventoryOpen,TEXT("click inside warehouse keeps both panels open"));break;}
        case 22:Click(R->Outside);Check(!bWarehouseOpen&&!bInventoryOpen&&!PC->IsLookInputIgnored(),TEXT("outside click closes warehouse and restores gameplay"));break;
        case 23:{auto State=M->Snapshot();State.Items.Empty();auto Potion=M->CreateItem(TEXT("hp_potion"),5);Potion.Cell=0;R->Id=Potion.InstanceId;State.Items.Add(Potion);Check(M->CommitState(State),TEXT("split popup fixture"));SetInventoryOpen(true);break;}
        case 24:Board->SelectItem(R->Id);Board->OpenItemMenu(R->Start,true);break;
        case 25:Click(R->Outside);Check(!bInventoryOpen&&M->FindItem(R->Id)&&M->FindItem(R->Id)->Count==5,TEXT("outside click closes split popup without changing quantity"));break;
        case 26:{
            auto Stock=M->CreateItem(TEXT("ue_m4a1"));auto Modified=Stock;TSharedPtr<FJsonObject> Data;
            if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Modified.Data),Data)){Check(false,TEXT("parse weapon recipe fixture"));break;}
            auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("optic"),TEXT("holographic"));Parts->SetStringField(TEXT("magazine"),TEXT("large_drum"));Parts->SetStringField(TEXT("muzzle"),TEXT("true"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Modified.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Modified.Data));
            auto Spawn=[&](const FColdSteelItem& I){auto* P=GetWorld()->SpawnActor<AColdSteelPickup>();P->InitializeItem(I);P->Body->SetSimulatePhysics(false);P->SetActorTickEnabled(false);P->SetActorHiddenInGame(true);return P;};
            auto* First=Spawn(Stock);const FString Original=PickupRecipeFingerprint(First);auto* Mod=Spawn(Modified);const FString Changed=PickupRecipeFingerprint(Mod);
            auto* Pool=GetGameInstance()->GetSubsystem<UColdSteelPickupStudio>();Check(Pool->Key(Stock)!=Pool->Key(Modified)&&Original!=Changed,TEXT("modified recipe has distinct cache and visible assembly"));
            CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);auto* Again=Spawn(Stock);
            Check(PickupRecipeFingerprint(Again)==Original,TEXT("pooled rig resets attachments and sections after modified recipe and GC"));
            Check(PickupRecipeFingerprint(First)==Original&&PickupRecipeFingerprint(Mod)==Changed,TEXT("existing ground models remain unchanged when pooled rig is reused"));
            Check(PC->GetPawn()&&PC->GetPawn()->IsActorTickEnabled(),TEXT("pooled recipe rebuild preserves active player"));
            First->Destroy();Mod->Destroy();Again->Destroy();break;
        }
        default:GetWorld()->GetTimerManager().ClearTimer(R->Timer);UE_LOG(LogTemp,Display,TEXT("DropHitchAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);PC->ConsoleCommand(TEXT("quit"));break;
        }
    }),.35f,true);
}
