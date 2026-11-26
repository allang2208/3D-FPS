#include "VillageNetworkAudit.h"
#include "../FPSGAMECharacter.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/VillageDefenseSection.h"
#include "../WorldGeneration/HillsBlacksmith.h"
#include "../NPC/ChapelNun.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "../UI/ColdSteelStatusModel.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Misc/CommandLine.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Parse.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Serialization/JsonSerializer.h"

namespace VillageNetAudit
{
bool Enabled()
{
#if UE_BUILD_SHIPPING
    return false;
#else
    return FParse::Param(FCommandLine::Get(),TEXT("VillageNetworkAudit"));
#endif
}
FString Output(){FString P;FParse::Value(FCommandLine::Get(),TEXT("VillageNetworkOutput="),P);return P;}
void Save(const FString& Name,const TSharedRef<FJsonObject>& R)
{FString J;FJsonSerializer::Serialize(R,TJsonWriterFactory<>::Create(&J));IFileManager::Get().MakeDirectory(*Output(),true);FFileHelper::SaveStringToFile(J,*(Output()/(Name+TEXT(".json"))));}
ATemperateHillsWorld* FindHills(UWorld* W)
{for(TActorIterator<ATemperateHillsWorld> It(W);It;++It)if(It->bReady)return *It;return nullptr;}
AChapelNun* FindNun(UWorld* W)
{for(TActorIterator<AChapelNun> It(W);It;++It)return *It;return nullptr;}
UColdSteelStatusModel* Model(APlayerController* PC)
{
    if(!PC)return nullptr;
    if(PC->IsLocalController())return PC->GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();
    const auto* PS=PC->GetPlayerState<AColdSteelPlayerState>();return PS?PS->GetShadowModel():nullptr;
}
void Place(APlayerController* PC,FVector P,FVector Aim,bool Walking)
{
    auto* C=PC?Cast<AFPSGAMECharacter>(PC->GetPawn()):nullptr;if(!C)return;
    C->GetCharacterMovement()->StopMovementImmediately();
    C->GetCharacterMovement()->SetMovementMode(Walking?MOVE_Walking:MOVE_None);
    C->SetActorLocation(P,false,nullptr,ETeleportType::TeleportPhysics);C->ForceNetUpdate();
    const auto R=(Aim-C->GetPawnViewLocation()).Rotation();PC->SetControlRotation(R);
    if(PC->HasAuthority())PC->ClientSetRotation(R,true);
    if(PC->PlayerCameraManager)PC->PlayerCameraManager->UpdateCamera(0.f);
}
bool GatePose(AVillageDefenseGate* G,bool Open,FString& Detail)
{
    if(!G)return false;bool OK=FMath::IsNearlyEqual(G->GetGateAngle(),Open?88.f:0.f,.15f);int32 Leaves=0;
    TInlineComponentArray<UStaticMeshComponent*> Parts(G);
    for(auto* P:Parts)if(P->GetFName()==TEXT("Masonry")||P->GetFName()==TEXT("RightLeaf"))
    {++Leaves;const float Sign=P->GetFName()==TEXT("RightLeaf")?-1.f:1.f;
        OK&=P->GetStaticMesh()&&FMath::IsNearlyEqual(float(P->GetRelativeRotation().Yaw),Sign*G->GetGateAngle(),.15f);
        OK&=P->GetCollisionEnabled()!=ECollisionEnabled::NoCollision;}
    Detail=FString::Printf(TEXT("angle=%.2f leaves=%d aligned=%d"),G->GetGateAngle(),Leaves,OK);return OK&&Leaves==2;
}
bool ShopState(UWorld* W,FString& Detail)
{
    for(TActorIterator<AHillsBlacksmith> It(W);It;++It)
    {
        int32 Repaired=0,Ruined=0;
        for(const auto& A:It->ShopAssemblies)if(IsValid(A.Get()))
        {TInlineComponentArray<UStaticMeshComponent*> Parts(A.Get());for(auto* P:Parts)if(P->IsVisible())
            {Repaired+=P->ComponentHasTag(TEXT("VillageShop.Repaired"));Ruined+=P->ComponentHasTag(TEXT("VillageShop.Ruined"));}}
        Detail=FString::Printf(TEXT("repaired=%d ruined=%d station=%d"),Repaired,Ruined,It->IsSceneStationAvailable());
        return Repaired>0&&Ruined==0&&It->IsSceneStationAvailable();
    }
    return false;
}
bool Facing(AChapelNun* N,APlayerController* PC,FString& Detail)
{
    if(!N||!PC||!PC->GetPawn())return false;
    TInlineComponentArray<USkeletalMeshComponent*> Parts(N);
    for(auto* P:Parts)if(P->GetFName()==TEXT("KaitlinBody"))
    {
        if(!P->GetSkeletalMeshAsset()){Detail=TEXT("nun appearance still streaming");return false;}
        const float Expected=(PC->GetPawn()->GetActorLocation()-N->GetActorLocation()).Rotation().Yaw-N->GetActorRotation().Yaw-90.f;
        const float Error=FMath::Abs(FMath::FindDeltaAngleDegrees(float(P->GetRelativeRotation().Yaw),Expected));
        Detail=FString::Printf(TEXT("local=%d yaw=%.2f expected=%.2f error=%.2f"),PC->IsLocalController(),P->GetRelativeRotation().Yaw,Expected,Error);
        return Error<3.f;
    }
    return false;
}
#if !UE_BUILD_SHIPPING
FAutoConsoleCommandWithWorld Command(TEXT("fps.Test.VillageNetworkAudit"),TEXT("Opt-in isolated real UDP village audit."),
    FConsoleCommandWithWorldDelegate::CreateLambda([](UWorld* W)
{
    if(!Enabled()||!W||W->GetNetMode()!=NM_ListenServer||Output().IsEmpty())return;
    if(!FPaths::ConvertRelativePathToFull(FPaths::ProjectDir()).Contains(TEXT("VillageNetworkAudit")))return;
    for(TActorIterator<AVillageNetworkAudit> It(W);It;++It)if(It->bDirector)return;
    auto* Run=W->SpawnActor<AVillageNetworkAudit>();Run->bDirector=true;
}));
#endif
}
