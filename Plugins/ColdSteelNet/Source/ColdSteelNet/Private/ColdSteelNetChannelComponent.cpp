#include "ColdSteelNetChannelComponent.h"
#include "ColdSteelNetLog.h"

#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "GameFramework/PlayerState.h"
#include "Kismet/GameplayStatics.h"
#include "Misc/Crc.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Net/UnrealNetwork.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"

#include "FPSGAMECharacter.h"
#include "UI/ColdSteelStatusModel.h"

namespace
{
    // 与 UGameplayStatics::SaveGameToSlot 相同的序列化口径：FObjectAndNameAsStringProxyArchive + ArNoDelta。
    void SaveToBlob(USaveGame* Save, TArray<uint8>& OutBlob)
    {
        OutBlob.Reset();
        FMemoryWriter Writer(OutBlob);
        FObjectAndNameAsStringProxyArchive Ar(Writer, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
    }

    UColdSteelProfileSave* BlobToSave(const TArray<uint8>& Blob)
    {
        UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
            UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
        FMemoryReader Reader(Blob);
        FObjectAndNameAsStringProxyArchive Ar(Reader, true);
        Ar.ArNoDelta = true;
        Save->Serialize(Ar);
        return Save;
    }
}

UColdSteelNetChannelComponent::UColdSteelNetChannelComponent()
{
    PrimaryComponentTick.bCanEverTick = true;
    SetIsReplicatedByDefault(true);
}

void UColdSteelNetChannelComponent::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(UColdSteelNetChannelComponent, MirrorBlob);
}

void UColdSteelNetChannelComponent::BeginPlay()
{
    Super::BeginPlay();
    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (PC && PC->IsLocalController() && GetOwnerRole() != ROLE_Authority)
    {
        // 客户端：本机档案就绪即发首帧，之后 0.8s 心跳。
        ClientHeartbeat = 0.f;
        UE_LOG(LogColdSteelNet, Log, TEXT("Channel ready on owning client"));
    }
}

void UColdSteelNetChannelComponent::TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction)
{
    Super::TickComponent(DeltaTime, TickType, ThisTickFunction);

    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC)
    {
        return;
    }

    if (GetOwnerRole() != ROLE_Authority)
    {
        // 客户端心跳上行：固定节奏全量快照（LAN 带宽可忽略；WAN 需改增量，见 perf 台账）。
        ClientHeartbeat -= DeltaTime;
        if (ClientHeartbeat <= 0.f)
        {
            ClientHeartbeat = 0.8f;
            const UGameInstance* GI = PC ? PC->GetGameInstance() : nullptr;
            if (const UColdSteelStatusModel* Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr)
            {
                if (!ScratchSave)
                {
                    ScratchSave = Cast<UColdSteelProfileSave>(
                        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
                }
                ScratchSave->Profile = Model->Snapshot();
                TArray<uint8> Blob;
                SaveToBlob(ScratchSave, Blob);
                ServerSubmitProfile(Blob);
            }
        }
        return;
    }

    // 服务端：脏档案 20s 节流落盘到主机。
    if (bServerDirty)
    {
        ServerSaveTimer -= DeltaTime;
        if (ServerSaveTimer <= 0.f)
        {
            ServerSaveTimer = 20.f;
            bServerDirty = false;
            SaveShadowToHostDisk();
        }
    }
}

void UColdSteelNetChannelComponent::ServerSubmitProfile_Implementation(const TArray<uint8>& ProfileBlob)
{
    if (GetOwnerRole() != ROLE_Authority)
    {
        return;
    }
    if (UColdSteelProfileSave* Save = BlobToSave(ProfileBlob))
    {
        ApplyGuestProfile(Save->Profile);
    }
}

void UColdSteelNetChannelComponent::ApplyGuestProfile(const FColdSteelProfile& Profile)
{
    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    const UGameInstance* GI = PC ? PC->GetGameInstance() : nullptr;
    UColdSteelStatusModel* HostModel = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    if (!HostModel)
    {
        return;
    }

    if (!ShadowModel)
    {
        ShadowModel = HostModel->CreateShadowModel(Profile);
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST shadow profile created: %s items=%d hp=%.0f"),
            *SlotName, Profile.Items.Num(), Profile.Health);
    }
    else
    {
        ShadowModel->AdoptNetMirror(Profile);
    }

    ApplyShadowToServerPawn();
    bServerDirty = true;
    ServerSaveTimer = 20.f;
}

void UColdSteelNetChannelComponent::ApplyShadowToServerPawn()
{
    APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !ShadowModel)
    {
        return;
    }
    if (AFPSGAMECharacter* Character = Cast<AFPSGAMECharacter>(PC->GetPawn()))
    {
        Character->NetShadowProfile = ShadowModel;
        Character->ApplyColdSteelProfile(ShadowModel);
        UE_LOG(LogColdSteelNet, Log, TEXT("MPTEST shadow applied to server pawn: %s"), *GetNameSafe(Character));
    }
}

void UColdSteelNetChannelComponent::OnRep_MirrorBlob()
{
    // 预留的权威回程入口（M3 伤害/服务端改档）。透传阶段服务端不写 MirrorBlob。
    const APlayerController* PC = Cast<APlayerController>(GetOwner());
    if (!PC || !PC->IsLocalController())
    {
        return;
    }
    const UGameInstance* GI = PC->GetGameInstance();
    if (UColdSteelStatusModel* Model = GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr)
    {
        if (UColdSteelProfileSave* Save = BlobToSave(MirrorBlob))
        {
            Model->AdoptNetMirror(Save->Profile);
            UE_LOG(LogColdSteelNet, Log, TEXT("MPTEST mirror adopted (client)"));
        }
    }
}

void UColdSteelNetChannelComponent::InitializeGuest(const FString& InSlotName)
{
    SlotName = InSlotName;
    if (USaveGame* Loaded = UGameplayStatics::LoadGameFromSlot(SlotName, 0))
    {
        if (UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(Loaded))
        {
            UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST guest slot found on host disk: %s"), *SlotName);
            ApplyGuestProfile(Save->Profile);
        }
    }
}

void UColdSteelNetChannelComponent::SaveShadowToHostDisk()
{
    if (!ShadowModel || SlotName.IsEmpty())
    {
        return;
    }
    UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
    Save->Profile = ShadowModel->Snapshot();
    if (UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
    {
        UE_LOG(LogColdSteelNet, Warning, TEXT("MPTEST guest profile saved to host disk: %s items=%d hp=%.0f"),
            *SlotName, Save->Profile.Items.Num(), Save->Profile.Health);
    }
}
