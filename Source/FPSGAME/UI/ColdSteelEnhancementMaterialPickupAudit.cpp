#include "ColdSteelPickup.h"
#include "ColdSteelStatusModel.h"
#include "../FPSGAMEPlayerController.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
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
void RunEnhancementMaterialPickupAudit(AFPSGAMEPlayerController* PC)
{
 auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* W=PC->GetWorld();auto* Pawn=PC->GetCharacter();if(!M||!M->IsAudit()||!Pawn)return;
 struct FRun{int32 Stage=0,Checks=0,Failures=0,SettleWait=0;FTimerHandle Timer;TArray<FString> Ids;TArray<FVector> Starts,Saved;TArray<FRotator> Rotations;};auto R=MakeShared<FRun>();
 auto Check=[R](bool OK,const TCHAR* Message){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("EnhancementMaterialAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Message);};
 const FVector Origin(50000,50000,5000);auto* Platform=W->SpawnActor<AActor>();auto* Ground=NewObject<UBoxComponent>(Platform);Platform->SetRootComponent(Ground);Ground->SetBoxExtent(FVector(350,350,10));Ground->SetCollisionProfileName(TEXT("BlockAll"));Ground->RegisterComponent();Platform->SetActorLocation(Origin);
 auto* V=NewObject<UStaticMeshComponent>(Platform);V->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));V->SetupAttachment(Ground);V->SetRelativeScale3D(FVector(7,7,.2));V->SetCollisionEnabled(ECollisionEnabled::NoCollision);V->RegisterComponent();
 auto Fixture=M->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);
 for(const TCHAR* Def:{TEXT("enhancement_stone"),TEXT("magic_dust")}){auto I=M->CreateItem(Def,99999);Check(I.StackMax==99999,TEXT("material maximum stack is 99999"));I.Cell=R->Ids.Num()*5;R->Ids.Add(I.InstanceId);Fixture.Items.Add(I);}
 Check(M->CommitState(Fixture),TEXT("isolated two material fixture"));
 for(int32 I=0;I<2;++I){Pawn->TeleportTo(Origin+FVector(-40,I*32-16,110),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(-25,0,0));Check(M->Drop(R->Ids[I]),TEXT("inventory drop commits"));}
 auto Find=[W](const FString& Id)->AColdSteelPickup*{for(TActorIterator<AColdSteelPickup> It(W);It;++It)if(It->ItemId==Id)return *It;return nullptr;};
 for(const FString& Id:R->Ids){auto* A=Find(Id);Check(A&&A->Body->IsSimulatingPhysics()&&A->Body->IsGravityEnabled(),TEXT("drop has gravity and rigid body"));if(A){auto* Mesh=A->FindComponentByClass<UStaticMeshComponent>();Check(Mesh&&Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/Items/EnhancementMaterials/")),TEXT("drop uses imported item model"));R->Starts.Add(A->GetActorLocation());}}
 Pawn->TeleportTo(Origin+FVector(-65,0,110),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(-58,0,0));
 W->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(PC,[=](){
  if(R->Stage==0&&R->SettleWait++<15){
   bool Settled=true;for(const auto& Id:R->Ids){auto* A=Find(Id);if(!A||A->GetActorLocation().Z>Origin.Z+35||A->Body->GetPhysicsLinearVelocity().Size()>2.f)Settled=false;}
   if(!Settled)return;
  }
  if(R->Stage++==0){
   for(int32 I=0;I<2;++I){auto* A=Find(R->Ids[I]);Check(A&&R->Starts.IsValidIndex(I)&&A->GetActorLocation().Z<R->Starts[I].Z-20,TEXT("gravity lowers model"));Check(A&&A->GetActorLocation().Z>Origin.Z&&A->GetActorLocation().Z<Origin.Z+35,TEXT("model rests on solid floor"));Check(M->FindItem(R->Ids[I])&&M->FindItem(R->Ids[I])->Place==2&&M->FindItem(R->Ids[I])->Count==99999,TEXT("world stack remains intact"));}
   Check(M->SaveNow(),TEXT("save landed model transforms"));for(const auto& Id:R->Ids){auto* A=Find(Id);R->Saved.Add(A?A->GetActorLocation():FVector::ZeroVector);R->Rotations.Add(A?A->GetActorRotation():FRotator::ZeroRotator);if(A)A->Destroy();}
   Check(M->ReloadProfile(),TEXT("reload world items"));for(int32 I=0;I<2;++I){auto* A=Find(R->Ids[I]);Check(A&&A->GetActorLocation().Equals(R->Saved[I],.1)&&A->GetActorRotation().Equals(R->Rotations[I],.1),TEXT("model transform restored"));}
   FVector Center=FVector::ZeroVector;for(const FVector& Position:R->Saved)Center+=Position;Center/=R->Saved.Num();
   FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);PC->SetControlRotation((Center-Eye).Rotation());PC->PlayerCameraManager->SetFOV(30.f);
   FTimerHandle ScreenshotTimer;W->GetTimerManager().SetTimer(ScreenshotTimer,FTimerDelegate::CreateWeakLambda(PC,[](){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("EnhancementMaterialsInGame.png"),false,false);}),.5f,false);
  }else if(R->Stage<=5){const int32 I=(R->Stage-2)/2;auto* A=Find(R->Ids[I]);Check(A!=nullptr,TEXT("pickup target still exists"));if(A){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);if(R->Stage%2==0){PC->SetControlRotation((A->GetActorLocation()-Eye).Rotation());return;}Check(M->Pickup(R->Ids[I]),TEXT("aimed model can be picked up"));Check(M->FindItem(R->Ids[I])&&M->FindItem(R->Ids[I])->Count==99999&&!Find(R->Ids[I]),TEXT("pickup preserves count and removes actor"));}}
  else if(R->Stage==6){
   UE_LOG(LogTemp,Display,TEXT("EnhancementMaterialAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);
   int32 Index=0;for(const TCHAR* Def:{TEXT("enhancement_stone"),TEXT("magic_dust")}){
    auto* Display=W->SpawnActor<AColdSteelPickup>();Display->InitializeItem(M->CreateItem(Def));Display->Body->SetSimulatePhysics(false);Display->SetActorEnableCollision(false);Display->SetActorRotation(FRotator::ZeroRotator);Display->SetActorLocation(Origin+FVector(0,Index++*36-18,10+Display->Body->GetUnscaledBoxExtent().Z));
   }
   auto* Camera=W->SpawnActor<ACameraActor>();Camera->SetActorLocation(Origin+FVector(-95,-45,48));Camera->SetActorRotation((Origin+FVector(0,0,18)-Camera->GetActorLocation()).Rotation());Camera->GetCameraComponent()->SetFieldOfView(43.f);PC->PlayerCameraManager->UnlockFOV();PC->SetViewTarget(Camera);
  }else if(R->Stage==7){FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("EnhancementMaterialsUprightInGame.png"),false,false);}
  else{W->GetTimerManager().ClearTimer(R->Timer);PC->ConsoleCommand(TEXT("quit"));}
 }),2.f,true);
}
