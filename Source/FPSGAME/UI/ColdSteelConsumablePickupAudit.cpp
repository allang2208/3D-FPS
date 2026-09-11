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
void RunConsumablePickupAudit(AFPSGAMEPlayerController* PC)
{
 auto* M=PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();auto* W=PC->GetWorld();auto* Pawn=PC->GetCharacter();if(!M||!M->IsAudit()||!Pawn)return;
 struct FRun{int32 Stage=0,Checks=0,Failures=0;FTimerHandle Timer;TArray<FString> Ids;TArray<FVector> Starts,Saved;TArray<FRotator> Rotations;};auto R=MakeShared<FRun>();
 auto Check=[R](bool OK,const TCHAR* Message){++R->Checks;if(!OK)++R->Failures;UE_LOG(LogTemp,Display,TEXT("ConsumableAudit: %s %s"),OK?TEXT("PASS"):TEXT("FAIL"),Message);};
 const FVector Origin(50000,50000,5000);auto* Platform=W->SpawnActor<AActor>();auto* Ground=NewObject<UBoxComponent>(Platform);Platform->SetRootComponent(Ground);Ground->SetBoxExtent(FVector(350,350,10));Ground->SetCollisionProfileName(TEXT("BlockAll"));Ground->RegisterComponent();Platform->SetActorLocation(Origin);
 auto* V=NewObject<UStaticMeshComponent>(Platform);V->SetStaticMesh(LoadObject<UStaticMesh>(nullptr,TEXT("/Engine/BasicShapes/Cube.Cube")));V->SetupAttachment(Ground);V->SetRelativeScale3D(FVector(7,7,.2));V->SetCollisionEnabled(ECollisionEnabled::NoCollision);V->RegisterComponent();
 auto Fixture=M->Snapshot();Fixture.Items.Empty();Fixture.Hotbar.Init(TEXT(""),4);Fixture.HotbarDefinitions.Init(TEXT(""),4);
 for(const TCHAR* Def:{TEXT("hp_potion"),TEXT("mp_potion"),TEXT("ammo_556"),TEXT("ammo_762")}){auto I=M->CreateItem(Def,7);I.Cell=R->Ids.Num()*5;R->Ids.Add(I.InstanceId);Fixture.Items.Add(I);}
 Check(M->CommitState(Fixture),TEXT("isolated four item fixture"));
 for(int32 I=0;I<4;++I){Pawn->TeleportTo(Origin+FVector(-40,I*32-48,110),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(-25,0,0));Check(M->Drop(R->Ids[I]),TEXT("inventory drop commits"));}
 auto Find=[W](const FString& Id)->AColdSteelPickup*{for(TActorIterator<AColdSteelPickup> It(W);It;++It)if(It->ItemId==Id)return *It;return nullptr;};
 for(const FString& Id:R->Ids){auto* A=Find(Id);Check(A&&A->Body->IsSimulatingPhysics()&&A->Body->IsGravityEnabled(),TEXT("drop has gravity and rigid body"));if(A){auto* Mesh=A->FindComponentByClass<UStaticMeshComponent>();Check(Mesh&&Mesh->GetStaticMesh()&&Mesh->GetStaticMesh()->GetPathName().StartsWith(TEXT("/Game/Items/Consumables/")),TEXT("drop uses imported item model"));R->Starts.Add(A->GetActorLocation());}}
 Pawn->TeleportTo(Origin+FVector(-65,0,110),FRotator::ZeroRotator);PC->SetControlRotation(FRotator(-58,0,0));
 W->GetTimerManager().SetTimer(R->Timer,FTimerDelegate::CreateWeakLambda(PC,[=](){
  if(R->Stage++==0){
   for(int32 I=0;I<4;++I){auto* A=Find(R->Ids[I]);Check(A&&R->Starts.IsValidIndex(I)&&A->GetActorLocation().Z<R->Starts[I].Z-20,TEXT("gravity lowers model"));Check(A&&A->GetActorLocation().Z>Origin.Z&&A->GetActorLocation().Z<Origin.Z+35,TEXT("model rests on solid floor"));Check(M->FindItem(R->Ids[I])->Place==2&&M->FindItem(R->Ids[I])->Count==7,TEXT("world stack remains intact"));}
   Check(M->SaveNow(),TEXT("save landed model transforms"));for(const auto& Id:R->Ids){auto* A=Find(Id);R->Saved.Add(A?A->GetActorLocation():FVector::ZeroVector);R->Rotations.Add(A?A->GetActorRotation():FRotator::ZeroRotator);if(A)A->Destroy();}
   Check(M->ReloadProfile(),TEXT("reload world items"));for(int32 I=0;I<4;++I){auto* A=Find(R->Ids[I]);Check(A&&A->GetActorLocation().Equals(R->Saved[I],.1)&&A->GetActorRotation().Equals(R->Rotations[I],.1),TEXT("model transform restored"));}
   FScreenshotRequest::RequestScreenshot(FPaths::ProjectSavedDir()/TEXT("ConsumablesInGame.png"),false,false);
  }else if(R->Stage<=9){const int32 I=(R->Stage-2)/2;auto* A=Find(R->Ids[I]);if(A){FVector Eye;FRotator View;PC->GetPlayerViewPoint(Eye,View);if(R->Stage%2==0){PC->SetControlRotation((A->GetActorLocation()-Eye).Rotation());return;}Check(M->Pickup(R->Ids[I]),TEXT("aimed model can be picked up"));Check(M->FindItem(R->Ids[I])->Count==7&&!Find(R->Ids[I]),TEXT("pickup preserves count and removes actor"));}}
  else{UE_LOG(LogTemp,Display,TEXT("ConsumableAudit: COMPLETE checks=%d failures=%d"),R->Checks,R->Failures);W->GetTimerManager().ClearTimer(R->Timer);PC->ConsoleCommand(TEXT("quit"));}
 }),2.f,true);
}
