#include "ColdSteelPickup.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/MaterialBillboardComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Engine/GameInstance.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "GameFramework/Character.h"
#include "TimerManager.h"
#include "UnrealClient.h"
#include "Misc/Paths.h"
#include "Camera/PlayerCameraManager.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
void RunLootGlowAudit(AFPSGAMEPlayerController* PC)
{
 auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* W=PC->GetWorld();auto* Pawn=PC->GetCharacter();if(!M||!M->IsAudit()||!Pawn)return;
 struct FRun{int32 Stage=0,Checks=0,Failures=0,Wait=0;FTimerHandle Timer;TArray<FString> Ids,Effects;TArray<FVector> Starts,Saved;TArray<FRotator> Rotations;};auto R=MakeShared<FRun>();
 auto Check=[R](bool OK,const TCHAR* Message){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("LootGlowAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Message);};
 const FVector Origin(50000,50000,5000);auto* Platform=W->SpawnActor<AActor>();auto* Ground=NewObject<UBoxComponent>(Platform);Platform->SetRootComponent(Ground);Ground->SetBoxExtent(FVector(350,350,10));Ground->SetCollisionProfileName(TEXT("BlockAll"));Ground->RegisterComponent();Platform->SetActorLocation(Origin);
 auto* V=NewObject<UStaticMeshComponent>(Platform);V->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));V->SetupAttachment(Ground);V->SetRelativeScale3D(FVector(7,7,.2));V->SetCollisionEnabled(ECollisionEnabled::NoCollision);V->RegisterComponent();
 auto Fixture=M->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);
 for(const TCHAR* Def:{TEXT("enchant_scroll_heavy"),TEXT("enchant_scroll_sharp"),TEXT("enchant_scroll_skeleton"),TEXT("enchant_scroll_tarantula"),TEXT("enhancement_stone"),TEXT("magic_dust")})
 {
  auto I=M->CreateItem(Def,99);Check(I.StackMax==(I.Definition==TEXT("enhancement_stone")||I.Definition==TEXT("magic_dust")?99999:99),TEXT("scroll stack contract remains 99"));I.Cell=R->Ids.Num()*3;R->Ids.Add(I.InstanceId);R->Effects.Add(ColdSteelInventory::Text(I,TEXT("scroll_id")));
  TSharedPtr<FJsonObject> Data;FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(I.Data),Data);Data->SetStringField(TEXT("rarity"),TEXT("common"));I.Data.Empty();FJsonSerializer::Serialize(Data.ToSharedRef(),TJsonWriterFactory<>::Create(&I.Data));Fixture.Items.Add(I);
 }
 Check(M->CommitState(Fixture)&&M->ReloadProfile(),TEXT("old scroll instances reload"));
 for(int32 I=0;I<6;++I){const auto* Item=M->FindItem(R->Ids[I]);Check(Item&&ColdSteelInventory::Text(*Item,TEXT("rarity"))==ColdSteelInventory::Text(M->CreateItem(Item->Definition),TEXT("rarity")),TEXT("old instance rarity refreshed"));Check(Item&&ColdSteelInventory::Text(*Item,TEXT("scroll_id"))==R->Effects[I]&&Item->Count==99,TEXT("scroll identity and count preserved"));}
 auto Find=[W](const FString& Id)->AColdSteelPickup*{for(TActorIterator<AColdSteelPickup> It(W);It;++It)if(It->ItemId==Id)return *It;return nullptr;};
 auto Inventory=[PC](bool Open){for(TObjectIterator<UColdSteelHUDWidget> It;It;++It)if(It->GetOwningPlayer()==PC&&It->IsInventoryOpen()!=Open)It->ToggleInventory();};Inventory(true);
 W->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(PC,[=](){
  if(R->Stage==0){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("LootGlowInventory.png"),true,false);++R->Stage;return;}
  if(R->Stage==1){Inventory(false);for(int32 I=0;I<6;++I){Pawn->TeleportTo(Origin+FVector(-40,I*40-100,110),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(-25,0,0));Check(M->Drop(R->Ids[I]),TEXT("scroll drop commits"));auto* A=Find(R->Ids[I]);Check(A&&A->Body->IsSimulatingPhysics()&&A->Body->IsGravityEnabled(),TEXT("scroll uses gravity"));if(A){R->Starts.Add(A->GetActorLocation());auto* Mesh=A->FindComponentByClass<UStaticMeshComponent>();Check(Mesh&&Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/Items/")),TEXT("generated scroll mesh loaded"));}}++R->Stage;return;}
  if(R->Stage==2){bool Settled=true;for(const auto& Id:R->Ids){auto* A=Find(Id);if(!A||A->GetActorLocation().Z>Origin.Z+35||A->Body->GetPhysicsLinearVelocity().Size()>2.f)Settled=false;}if(!Settled&&R->Wait++<20)return;
   for(int32 I=0;I<6;++I){auto* A=Find(R->Ids[I]);Check(A&&R->Starts.IsValidIndex(I)&&A->GetActorLocation().Z<R->Starts[I].Z-20&&A->GetActorLocation().Z>Origin.Z&&A->GetActorLocation().Z<Origin.Z+35,TEXT("scroll falls and rests on floor"));}
   Check(M->SaveNow(),TEXT("save landed scrolls"));for(const auto& Id:R->Ids){auto* A=Find(Id);R->Saved.Add(A?A->GetActorLocation():FVector::ZeroVector);R->Rotations.Add(A?A->GetActorRotation():FRotator::ZeroRotator);if(A)A->Destroy();}
   Check(M->ReloadProfile(),TEXT("reload landed scrolls"));for(int32 I=0;I<6;++I){auto* A=Find(R->Ids[I]);Check(A&&A->GetActorLocation().Equals(R->Saved[I],.1)&&A->GetActorRotation().Equals(R->Rotations[I],.1),TEXT("landed transform restored"));}for(int32 I=0;I<6;++I){auto* A=Find(R->Ids[I]);UStaticMeshComponent* Beam=nullptr;for(auto* C:TInlineComponentArray<UStaticMeshComponent*>(A))if(C->GetFName()==TEXT("LootBeam"))Beam=Cast<UStaticMeshComponent>(C);auto* Glow=A->FindComponentByClass<UMaterialBillboardComponent>();
    Check(Beam&&Glow&&Beam->IsVisible()&&Glow->IsVisible(),TEXT("beam and center glow survive reload"));
    Check(Beam&&Beam->GetCollisionEnabled()==ECollisionEnabled::NoCollision&&Glow&&Glow->GetCollisionEnabled()==ECollisionEnabled::NoCollision,TEXT("visuals do not intercept pickup traces"));
    Check(Beam&&FMath::Abs(Beam->GetForwardVector().Z)>.999&&FMath::IsNearlyEqual(Beam->GetComponentLocation().X,A->GetActorLocation().X,.1)&&FMath::IsNearlyEqual(Beam->GetComponentLocation().Y,A->GetActorLocation().Y,.1),TEXT("beam stays vertical and centered after physics"));
    auto* MID=Beam?Cast<UMaterialInstanceDynamic>(Beam->GetMaterial(0)):nullptr;const FLinearColor C=MID?MID->K2_GetVectorParameterValue(TEXT("LootColor")):FLinearColor::Black;
    const bool Correct=I<2?(C.R>.7&&C.G>.7&&C.B>.7):I==2?(C.B>C.R&&C.B>C.G):I==3?(C.G>C.R&&C.G>C.B):(C.B>C.G&&C.R>C.G);Check(MID&&Correct,TEXT("rarity hue matches white blue green purple"));
   }++R->Stage;return;
  }
  if(R->Stage>=3&&R->Stage<=14){const int32 I=(R->Stage-3)/2;auto* A=Find(R->Ids[I]);if(R->Stage%2==1){if(A){Pawn->TeleportTo(A->GetActorLocation()+FVector(-100,0,100),FRotator::ZeroRotator);FTimerHandle AimTimer;const FVector Target=A->GetActorLocation();W->GetTimerManager().SetTimer(AimTimer,FTimerDelegate::CreateWeakLambda(PC,[PC,Target](){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((Target-Eye).Rotation());}),.3f,false);}}else{Check(A&&M->Pickup(R->Ids[I]),TEXT("aimed scroll pickup succeeds"));const auto* Item=M->FindItem(R->Ids[I]);Check(Item&&Item->Place==0&&Item->Count==99&&!Find(R->Ids[I]),TEXT("pickup preserves stack and removes actor"));}++R->Stage;return;}
  if(R->Stage==15){Check(M->SaveNow()&&M->ReloadProfile(),TEXT("picked up scrolls persist"));UE_LOG(LogTemp,Display,TEXT("LootGlowAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);
   int32 Index=0;for(const auto& Id:R->Ids){const auto* Item=M->FindItem(Id);if(!Item)continue;auto* Display=W->SpawnActor<AColdSteelPickup>();Display->InitializeItem(*Item);Display->Body->SetSimulatePhysics(false);Display->SetActorEnableCollision(false);Display->SetActorRotation(FRotator(0,180,0));Display->SetActorLocation(Origin+FVector(0,(Index++-2.5f)*65,10+Display->Body->GetUnscaledBoxExtent().Z));}
   auto* Camera=W->SpawnActor<ACameraActor>();Camera->SetActorLocation(Origin+FVector(-430,-45,170));Camera->SetActorRotation((Origin+FVector(0,0,65)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(58.f);PC->PlayerCameraManager->UnlockFOV();PC->SetViewTarget(Camera);++R->Stage;return;
  }
  if(R->Stage++==16){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("LootGlowInGame.png"),false,false);return;}
  W->GetTimerManager().ClearTimer(R->Timer);PC->ConsoleCommand(TEXT("quit"));
 }),2.f,true);
}
