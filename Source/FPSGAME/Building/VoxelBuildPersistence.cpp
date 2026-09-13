#include "VoxelBuildPersistence.h"
#include "VoxelBuildWorld.h"
#include "Kismet/GameplayStatics.h"
#include "Serialization/MemoryReader.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/NameAsStringProxyArchive.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/Crc.h"
#include "HAL/FileManager.h"
#if PLATFORM_WINDOWS
#include "Windows/WindowsHWrapper.h"
#endif

static FArchive& operator<<(FArchive& Ar,FVoxelBuildKey& K){return Ar<<K.Volume<<K.Cell;}
static FArchive& operator<<(FArchive& Ar,FVoxelSavedCell& C){return Ar<<C.Position<<C.Material;}
static FArchive& operator<<(FArchive& Ar,FVoxelFreeVolume& V){return Ar<<V.Id<<V.Origin<<V.Cells;}
static FArchive& operator<<(FArchive& Ar,FVoxelBrokenBond& B){return Ar<<B.A<<B.B;}
static FArchive& operator<<(FArchive& Ar,FVoxelDebrisCell& C){return Ar<<C.Key<<C.Min<<C.Material<<C.Damage;}
static FArchive& operator<<(FArchive& Ar,FVoxelFragmentSave& F)
{return Ar<<F.Id<<F.Transform<<F.Cells<<F.BrokenBonds<<F.Velocity<<F.AngularVelocity<<F.bSleeping;}

namespace
{
    constexpr uint32 Magic=0x33584256; // VBX3, independent of USaveGame/UObject serialization.
    void Serialize(FArchive& Ar,FVoxelDiskSnapshot& S)
    {Ar<<S.Version<<S.CellSizeCm<<S.WorldKey<<S.Cells<<S.FreeVolumes<<S.Damage<<S.BrokenBonds<<S.Fragments<<S.LegacyProtected;}
    FString Path(const FString& Slot){return FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sav"));}
}

FVoxelDiskSnapshot VoxelPersistence::Take(UVoxelBuildSave* S)
{
    FVoxelDiskSnapshot D;D.Version=S->Version;D.CellSizeCm=S->CellSizeCm;D.WorldKey=MoveTemp(S->WorldKey);
    D.Cells=MoveTemp(S->Cells);D.FreeVolumes=MoveTemp(S->FreeVolumes);D.Damage=MoveTemp(S->Damage);
    D.BrokenBonds=MoveTemp(S->BrokenBonds);D.Fragments=MoveTemp(S->Fragments);D.LegacyProtected=MoveTemp(S->LegacyProtected);return D;
}

UVoxelBuildSave* VoxelPersistence::Load(const FString& Slot)
{
    TArray<uint8> Bytes;if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0))return nullptr;
    uint32 Tag=0;if(Bytes.Num()>=4)FMemory::Memcpy(&Tag,Bytes.GetData(),4);
    if(Tag!=Magic)return Cast<UVoxelBuildSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
    if(Bytes.Num()<12)return nullptr;
    FMemoryReader Reader(Bytes,true);uint32 Size=0,Crc=0;Reader<<Tag<<Size<<Crc;
    if(Size!=uint32(Bytes.Num()-12)||FCrc::MemCrc32(Bytes.GetData()+12,Size)!=Crc)return nullptr;
    FNameAsStringProxyArchive Ar(Reader);Ar.ArMaxSerializeSize=Bytes.Num();
    FVoxelDiskSnapshot Payload;Serialize(Ar,Payload);
    if(Ar.IsError()||Reader.Tell()!=Bytes.Num())return nullptr;
    auto* S=NewObject<UVoxelBuildSave>();S->Version=Payload.Version;S->CellSizeCm=Payload.CellSizeCm;S->WorldKey=MoveTemp(Payload.WorldKey);
    S->Cells=MoveTemp(Payload.Cells);S->FreeVolumes=MoveTemp(Payload.FreeVolumes);S->Damage=MoveTemp(Payload.Damage);
    S->BrokenBonds=MoveTemp(Payload.BrokenBonds);S->Fragments=MoveTemp(Payload.Fragments);S->LegacyProtected=MoveTemp(Payload.LegacyProtected);return S;
}

bool VoxelPersistence::Write(FString Slot,FVoxelDiskSnapshot Snapshot)
{
    TArray<uint8> Bytes;FMemoryWriter Writer(Bytes,true);uint32 Tag=Magic,Size=0,Crc=0;
    Writer<<Tag<<Size<<Crc;
    FNameAsStringProxyArchive Ar(Writer);Serialize(Ar,Snapshot);if(Ar.IsError())return false;
    Size=Bytes.Num()-12;Crc=FCrc::MemCrc32(Bytes.GetData()+12,Size);Writer.Seek(0);Writer<<Tag<<Size<<Crc;
    auto& Files=IFileManager::Get();const FString Target=Path(Slot),Temporary=Target+TEXT(".pending");
    if(!Files.MakeDirectory(*FPaths::GetPath(Target),true)||!FFileHelper::SaveArrayToFile(Bytes,*Temporary))return false;
    // Keep the first pre-structure file. Atomic same-directory replacement
    // leaves the previous committed save intact if the new write fails.
    const FString Original=Target+TEXT(".pre-structure");
    if(Files.FileExists(*Target)&&!Files.FileExists(*Original))
    {
        TUniquePtr<FArchive> Old(Files.CreateFileReader(*Target));uint32 OldTag=0;
        if(Old&&Old->TotalSize()>=4){*Old<<OldTag;Old.Reset();if(OldTag!=Magic&&Files.Copy(*Original,*Target,false,false)!=COPY_OK)return false;}
    }
    // FFileManagerGeneric::Move deletes the destination before renaming.
    // Win64's replacement API keeps the committed file until the swap.
#if PLATFORM_WINDOWS
    FString NativeTarget=FPaths::ConvertRelativePathToFull(Target),NativeTemporary=FPaths::ConvertRelativePathToFull(Temporary);
    FPaths::MakePlatformFilename(NativeTarget);FPaths::MakePlatformFilename(NativeTemporary);
    return !!::MoveFileExW(*NativeTemporary,*NativeTarget,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
#else
    return false;
#endif
}
