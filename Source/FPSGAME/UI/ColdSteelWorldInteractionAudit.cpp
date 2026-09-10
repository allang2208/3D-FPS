#include "ColdSteelWorldInteraction.h"
#include "ColdSteelPickup.h"
#include "ColdSteelWarehouseChest.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Components/BoxComponent.h"
#include "Components/PoseableMeshComponent.h"
#include "Components/StaticMeshComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/JsonSerializer.h"
#include "TimerManager.h"
#include "InputKeyEventArgs.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"
#include "Misc/CommandLine.h"
#include "Misc/Parse.h"
using namespace ColdSteelInventory;

void RunWorldInteractionAudit(AFPSGAMEPlayerController* PC)
{
    auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* Pawn=PC->GetCharacter();if(!M||!M->IsAudit()||!Pawn)return;
    struct FRun{int32 Phase=0,Checks=0,Failures=0,Wait=0;uint64 LastFrame=MAX_uint64;FTimerHandle Timer;FString Gun,AK;FColdSteelItem Original;FColdSteelProfile Dropped;FVector Initial,SavedPosition;FRotator SavedRotation;TWeakObjectPtr<AColdSteelPickup> Pickup;TWeakObjectPtr<AColdSteelWarehouseChest> Chest;TWeakObjectPtr<AActor> Wall;};auto R=MakeShared<FRun>();
    auto Check=[R](bool OK,const TCHAR* Name){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("WorldInteractionAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Name);};
    auto* World=PC->GetWorld();const FVector Floor(50000,50000,5000);
    if(FParse::Param(FCommandLine::Get(),TEXT("WorldInteractionRestoreAudit"))){
        int32 RestoredM4=0,RestoredAK=0;
        for(TActorIterator<AColdSteelPickup> It(World);It;++It){
            const auto* I=M->FindItem(It->ItemId);
            if(I&&I->Place==2&&It->Weapon->GetSkinnedAsset()){
                RestoredM4+=I->Definition==TEXT("ue_m4a1");RestoredAK+=I->Definition==TEXT("ue_akm");
            }
        }
        Check(RestoredM4==1&&RestoredAK==1,TEXT("fresh process BeginPlay restores saved M4 and AKM models"));
        Check(PC->GetPawn()==Pawn&&Pawn->IsActorTickEnabled(),TEXT("preview construction preserves active player and gameplay tick"));
    }
    auto* Platform=World->SpawnActor<AActor>();auto* Ground=NewObject<UBoxComponent>(Platform);Platform->SetRootComponent(Ground);Ground->SetBoxExtent(FVector(500,500,10));Ground->SetCollisionProfileName(TEXT("BlockAll"));Ground->RegisterComponent();Platform->SetActorLocation(Floor);
    auto* FloorMesh=NewObject<UStaticMeshComponent>(Platform);FloorMesh->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));FloorMesh->SetupAttachment(Ground);FloorMesh->SetRelativeScale3D(FVector(10,10,.2));FloorMesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);FloorMesh->RegisterComponent();
    Pawn->TeleportTo(Floor+FVector(0,0,110),FRotator::ZeroRotator);Pawn->GetCharacterMovement()->StopMovementImmediately();PC->SetControlRotation(FRotator(-25,0,0));
    auto Fixture=M->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);
    auto Gun=M->CreateItem(TEXT("ue_m4a1"));Gun.Cell=0;Gun.Magazine=13;Gun.Reserve=27;
    TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Gun.Data),Data);auto Parts=MakeShared<FJsonObject>();Parts->SetStringField(TEXT("underbarrel"),TEXT("angled_foregrip"));Parts->SetStringField(TEXT("optic"),TEXT("holographic"));Parts->SetStringField(TEXT("magazine"),TEXT("large_drum"));Parts->SetStringField(TEXT("muzzle"),TEXT("true"));Data->SetObjectField(TEXT("gunsmith_parts"),Parts);Data->SetNumberField(TEXT("enhanceLevel"),7);Gun.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&Gun.Data));
    R->Original=Gun;R->Gun=Gun.InstanceId;Fixture.Items.Add(Gun);auto AK=M->CreateItem(TEXT("ue_akm"));AK.Cell=5;R->AK=AK.InstanceId;Fixture.Items.Add(AK);Check(M->CommitState(Fixture),TEXT("isolated processed rifle and AKM fixture"));
    World->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(PC,[PC,Pawn,M,R,Check,Floor](){
        if(R->LastFrame==GFrameCounter)return;R->LastFrame=GFrameCounter;
        auto* World=PC->GetWorld();
        auto Find=[&](const FString& Id)->AColdSteelPickup*{for(TActorIterator<AColdSteelPickup> It(World);It;++It)if(It->ItemId==Id)return *It;return nullptr;};
        auto Aim=[&](FVector At){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((At-Eye).Rotation());PC->PlayerCameraManager->UpdateCamera(0);};
        auto Use=[&](){static_cast<APlayerController*>(PC)->InputKey(FInputKeyEventArgs::CreateSimulated(EKeys::E,IE_Pressed,1.f));};
        auto Shot=[&](const TCHAR* Name){const FString Dir=FPaths::ProjectSavedDir()/TEXT("WorldInteraction");IFileManager::Get().MakeDirectory(*Dir,true);FScreenshotRequest::RequestScreenshot(Dir/(FString(Name)+TEXT(".png")),true,false);};
        switch(R->Phase++){
        case 0:Check(M->Drop(R->Gun),TEXT("dropping rifle commits world instance"));R->Pickup=Find(R->Gun);if(R->Pickup.IsValid()){R->Initial=R->Pickup->GetActorLocation();Check(R->Pickup->Weapon->GetSkinnedAsset()&&R->Pickup->Body->IsSimulatingPhysics()&&R->Pickup->Body->IsGravityEnabled(),TEXT("live model has rigid body and gravity"));Aim(Floor+FVector(120,0,25));}break;
        case 1:if(R->Pickup.IsValid()){if(R->Pickup->GetActorLocation().Z>=R->Initial.Z-5&&R->Wait++<10){--R->Phase;break;}R->Wait=0;Check(R->Pickup->GetActorLocation().Z<R->Initial.Z-5,TEXT("gravity lowers rifle after release"));Shot(TEXT("falling"));}break;
        case 2:if(R->Pickup.IsValid()){if(R->Pickup->Body->GetPhysicsLinearVelocity().Size()>3&&R->Wait++<15){--R->Phase;break;}Check(R->Pickup->GetActorLocation().Z>Floor.Z&&R->Pickup->GetActorLocation().Z<R->Initial.Z-25,TEXT("rifle lands above solid floor without tunnelling"));Check(M->FindItem(R->Gun)->Place==2,TEXT("nearby rifle never auto collects"));Aim(R->Pickup->GetActorLocation());Shot(TEXT("landed-model"));}break;
        case 3:if(R->Wait!=100){PC->SetControlRotation(FRotator(0,180,0));R->Wait=100;--R->Phase;break;}Use();Check(M->FindItem(R->Gun)->Place==2,TEXT("E looking away cannot collect nearby rifle"));if(R->Pickup.IsValid())Aim(R->Pickup->GetActorLocation());break;
        case 4:if(R->Pickup.IsValid()){
            Check(ColdSteelWorldInteraction::TraceTarget(PC)==R->Pickup.Get(),TEXT("camera center selects ground rifle"));
            R->Dropped=M->Snapshot();auto Full=R->Dropped;for(int32 C=0;C<72;++C){auto I=M->CreateItem(TEXT("hp_potion"),99);if(Fits(Full.Items,I,C)){I.Cell=C;Full.Items.Add(I);}}Check(M->CommitState(Full),TEXT("full backpack fixture"));Use();Check(Find(R->Gun)&&M->FindItem(R->Gun)->Place==2&&M->ResultMessage().Contains(TEXT("已满")),TEXT("full backpack leaves exact world item alive"));
        }break;
        case 5:Check(M->CommitState(R->Dropped),TEXT("restore available backpack space"));if(R->Pickup.IsValid())Aim(R->Pickup->GetActorLocation());M->AuditFailNextSave=true;Use();Check(Find(R->Gun)&&M->FindItem(R->Gun)->Place==2,TEXT("failed save does not destroy pickup"));break;
        case 6:if(R->Pickup.IsValid())Aim(R->Pickup->GetActorLocation());Use();{const auto* I=M->FindItem(R->Gun);Check(I&&I->Place==0&&I->Data==R->Original.Data&&I->Magazine==13&&I->Reserve==27&&!Find(R->Gun),TEXT("E collects aimed model preserving processing attachments and ammo"));}break;
        case 7:{if(!R->Chest.IsValid()){CollectGarbage(GARBAGE_COLLECTION_KEEPFLAGS);R->Chest=World->SpawnActor<AColdSteelWarehouseChest>(Floor+FVector(145,0,10),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(0,180,0));--R->Phase;break;}auto* Chest=R->Chest.Get();Use();Check(Chest->IsWithinReach(Pawn)&&!M->bWarehouseOpen,TEXT("nearby warehouse cannot open when looking away"));Aim(Chest->GetActorLocation()+FVector(0,0,40));break;}
        case 8:Use();Check(M->bWarehouseOpen,TEXT("E opens warehouse only under camera center"));R->Wait=0;break;
        case 9:if(R->Wait++==0){Check(M->bWarehouseOpen,TEXT("warehouse remains open while UI owns mouse"));Shot(TEXT("warehouse-focused"));--R->Phase;break;}for(TObjectIterator<UColdSteelHUDWidget> It;It;++It)if(It->GetOwningPlayer()==PC&&It->IsInventoryOpen())It->ToggleInventory();if(R->Chest.IsValid())Aim(R->Chest->GetActorLocation()+FVector(0,0,40));break;
        case 10:{auto* Wall=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall);Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(3,100,100));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Wall->SetActorLocation(Floor+FVector(65,0,100));R->Wall=Wall;Use();Check(!M->bWarehouseOpen&&ColdSteelWorldInteraction::TraceTarget(PC)==Wall,TEXT("wall blocks warehouse interaction"));break;}
        case 11:if(R->Wall.IsValid())R->Wall->Destroy();if(R->Chest.IsValid())R->Chest->Destroy();Check(M->Drop(R->AK),TEXT("AKM also drops as world item"));R->Pickup=Find(R->AK);Check(R->Pickup.IsValid()&&R->Pickup->Weapon->GetSkinnedAsset(),TEXT("AKM uses its own current model"));R->Wait=0;break;
        case 12:if(R->Pickup.IsValid()){if(R->Pickup->Body->GetPhysicsLinearVelocity().Size()>3&&R->Wait++<15){--R->Phase;break;}Aim(R->Pickup->GetActorLocation());Shot(TEXT("akm-landed"));Check(M->SaveNow(),TEXT("save physical world transform"));R->SavedPosition=M->FindItem(R->AK)->Position;R->SavedRotation=M->FindItem(R->AK)->WorldRotation;}break;
        case 13:if(R->Pickup.IsValid())R->Pickup->Destroy();Check(M->ReloadProfile(),TEXT("reload saved world items"));R->Pickup=Find(R->AK);Check(R->Pickup.IsValid()&&R->Pickup->GetActorLocation().Equals(R->SavedPosition,.1)&&R->Pickup->GetActorRotation().Equals(R->SavedRotation,.1),TEXT("world location rotation and model restored from save"));if(R->Pickup.IsValid())Aim(R->Pickup->GetActorLocation());break;
        case 14:Check(M->Drop(R->Gun),TEXT("save modified M4 beside AKM for fresh process restore"));if(R->Pickup.IsValid()){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);auto* Wall=World->SpawnActor<AActor>();auto* Box=NewObject<UBoxComponent>(Wall);Wall->SetRootComponent(Box);Box->SetBoxExtent(FVector(15));Box->SetCollisionProfileName(TEXT("BlockAll"));Box->RegisterComponent();Wall->SetActorLocation((Eye+R->Pickup->GetActorLocation())*.5);R->Wall=Wall;Use();Check(M->FindItem(R->AK)->Place==2&&ColdSteelWorldInteraction::TraceTarget(PC)==Wall,TEXT("wall also blocks ground item pickup"));}break;
        case 15:if(R->Wall.IsValid())R->Wall->Destroy();Pawn->TeleportTo(Floor+FVector(-350,0,110),FRotator::ZeroRotator);if(R->Pickup.IsValid())Aim(R->Pickup->GetActorLocation());break;
        case 16:Use();Check(M->FindItem(R->AK)->Place==2,TEXT("aimed item outside reach cannot be collected"));break;
        default:UE_LOG(LogTemp,Display,TEXT("WorldInteractionAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);World->GetTimerManager().ClearTimer(R->Timer);PC->ConsoleCommand(TEXT("quit"));break;
        }
    }),.3f,true);
}
