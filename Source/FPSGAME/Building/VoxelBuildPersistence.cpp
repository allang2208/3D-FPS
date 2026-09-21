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
static FArchive& operator<<(FArchive& Ar,FVoxelBuildPrefabInstance& P){return Ar<<P.Id<<P.Cell<<P.Yaw<<P.Footprint;}

namespace
{
    constexpr uint32 Magic=0x33584256; // VBX3, independent of USaveGame/UObject serialization.
    // Version 4 appends placed prefab pieces; older files stop before that field.
    void Serialize(FArchive& Ar,FVoxelDiskSnapshot& S)
    {
        Ar<<S.Version<<S.CellSizeCm<<S.WorldKey<<S.Cells<<S.FreeVolumes<<S.Damage<<S.BrokenBonds<<S.Fragments<<S.LegacyProtected;
        if(S.Version>=4)Ar<<S.Prefabs;
    }
    FString Path(const FString& Slot){return FPaths::ProjectSavedDir()/TEXT("SaveGames")/(Slot+TEXT(".sav"));}
    // 审计 C6：Write 在首次覆盖前保留的备份路径（原来只在 Write 内部拼一次字符串）。
    FString BackupPath(const FString& Slot){return Path(Slot)+TEXT(".pre-structure");}
}

const TCHAR* VoxelPersistence::Describe(ELoadResult Result)
{
    switch(Result)
    {
    case ELoadResult::Ok:           return TEXT("存档读取成功");
    case ELoadResult::Missing:      return TEXT("尚无存档（首次进入该世界）");
    case ELoadResult::Corrupt:      return TEXT("存档校验失败（CRC 或长度不符，文件已损坏）");
    case ELoadResult::ParseFailed:  return TEXT("存档解析失败（内容与版本不符）");
    case ELoadResult::LegacyFormat: return TEXT("旧版存档格式");
    case ELoadResult::ReadFailed:   return TEXT("存档文件无法读取（IO 失败）");
    }
    return TEXT("未知的存档读取结果");
}

FString VoxelPersistence::PreStructurePath(const FString& Slot){return BackupPath(Slot);}

namespace
{
    /**
     * 审计 C6：把"字节 → 快照"的解析从入口拆出来，供槽位读取（Load）与
     * 完整路径读取（LoadFromFile，用于 `.pre-structure` 备份）共用，避免两处逻辑分叉。
     */
    UVoxelBuildSave* LoadBytes(TArray<uint8>& Bytes,VoxelPersistence::ELoadResult& OutResult,bool bAllowLegacy)
    {
        OutResult=VoxelPersistence::ELoadResult::Missing;
        if(Bytes.IsEmpty())return nullptr;
        uint32 Tag=0;if(Bytes.Num()>=4)FMemory::Memcpy(&Tag,Bytes.GetData(),4);
        if(Tag!=Magic)
        {
            // 旧版 USaveGame 反射格式。不支持的格式单独报告，不混进"解析失败"。
            if(!bAllowLegacy){OutResult=VoxelPersistence::ELoadResult::LegacyFormat;return nullptr;}
            UVoxelBuildSave* Legacy=Cast<UVoxelBuildSave>(UGameplayStatics::LoadGameFromMemory(Bytes));
            OutResult=Legacy?VoxelPersistence::ELoadResult::Ok:VoxelPersistence::ELoadResult::ParseFailed;
            return Legacy;
        }
        if(Bytes.Num()<12){OutResult=VoxelPersistence::ELoadResult::Corrupt;return nullptr;}
        FMemoryReader Reader(Bytes,true);uint32 Size=0,Crc=0;Reader<<Tag<<Size<<Crc;
        // CRC/长度不符单独归类为 Corrupt（原来与"解析失败"一起静默返回 nullptr，
        // 调用方只能笼统报"版本不兼容"）。
        if(Size!=uint32(Bytes.Num()-12)||FCrc::MemCrc32(Bytes.GetData()+12,Size)!=Crc)
        {OutResult=VoxelPersistence::ELoadResult::Corrupt;return nullptr;}
        FNameAsStringProxyArchive Ar(Reader);Ar.ArMaxSerializeSize=Bytes.Num();
        FVoxelDiskSnapshot Payload;Serialize(Ar,Payload);
        if(Ar.IsError()||Reader.Tell()!=Bytes.Num()){OutResult=VoxelPersistence::ELoadResult::ParseFailed;return nullptr;}
        auto* S=NewObject<UVoxelBuildSave>();S->Version=Payload.Version;S->CellSizeCm=Payload.CellSizeCm;S->WorldKey=MoveTemp(Payload.WorldKey);
        S->Cells=MoveTemp(Payload.Cells);S->FreeVolumes=MoveTemp(Payload.FreeVolumes);S->Damage=MoveTemp(Payload.Damage);
        S->BrokenBonds=MoveTemp(Payload.BrokenBonds);S->Fragments=MoveTemp(Payload.Fragments);S->LegacyProtected=MoveTemp(Payload.LegacyProtected);
        S->Prefabs=MoveTemp(Payload.Prefabs);OutResult=VoxelPersistence::ELoadResult::Ok;return S;
    }
}

FVoxelDiskSnapshot VoxelPersistence::Take(UVoxelBuildSave* S)
{
    // 审计 C6 附带加固：本函数原来直接解引用 S。当前唯一调用方是
    // VoxelBuildWorldSave.cpp 的 MakeSnapshot()（必非空），但 C6 之后加载路径引入了
    // "可能为空的 LoadedData"，所以这里补一个空指针保护，避免未来误用直接崩。
    FVoxelDiskSnapshot D;
    if(!S)return D;
    D.Version=S->Version;D.CellSizeCm=S->CellSizeCm;D.WorldKey=MoveTemp(S->WorldKey);
    D.Cells=MoveTemp(S->Cells);D.FreeVolumes=MoveTemp(S->FreeVolumes);D.Damage=MoveTemp(S->Damage);
    D.BrokenBonds=MoveTemp(S->BrokenBonds);D.Fragments=MoveTemp(S->Fragments);D.LegacyProtected=MoveTemp(S->LegacyProtected);
    D.Prefabs=MoveTemp(S->Prefabs);return D;
}

UVoxelBuildSave* VoxelPersistence::Load(const FString& Slot,ELoadResult& OutResult,bool bAllowLegacy)
{
    OutResult=ELoadResult::Missing;
    TArray<uint8> Bytes;
    if(!UGameplayStatics::LoadDataFromSlot(Bytes,Slot,0))
    {
        // 审计 C6：区分"文件不存在"（正常）与"存在但读不出来"（IO 失败）。
        OutResult=IFileManager::Get().FileExists(*Path(Slot))?ELoadResult::ReadFailed:ELoadResult::Missing;
        return nullptr;
    }
    return LoadBytes(Bytes,OutResult,bAllowLegacy);
}

UVoxelBuildSave* VoxelPersistence::LoadFromFile(const FString& FullPath,ELoadResult& OutResult,bool bAllowLegacy)
{
    OutResult=ELoadResult::Missing;
    TArray<uint8> Bytes;
    // 审计 C6：备份文件（如 `X.sav.pre-structure`）不在槽位命名规则内，
    // 不能走 Load（那会把 `.sav` 再拼一次）。这里直接按完整路径读原始字节。
    if(!FFileHelper::LoadFileToArray(Bytes,*FullPath))
    {
        OutResult=IFileManager::Get().FileExists(*FullPath)?ELoadResult::ReadFailed:ELoadResult::Missing;
        return nullptr;
    }
    return LoadBytes(Bytes,OutResult,bAllowLegacy);
}

bool VoxelPersistence::Write(FString Slot,FVoxelDiskSnapshot Snapshot)
{
    TArray<uint8> Bytes;FMemoryWriter Writer(Bytes,true);uint32 Tag=Magic,Size=0,Crc=0;
    Writer<<Tag<<Size<<Crc;
    FNameAsStringProxyArchive Ar(Writer);Serialize(Ar,Snapshot);if(Ar.IsError())return false;
    Size=Bytes.Num()-12;Crc=FCrc::MemCrc32(Bytes.GetData()+12,Size);Writer.Seek(0);Writer<<Tag<<Size<<Crc;
    auto& Files=IFileManager::Get();const FString Target=Path(Slot),Temporary=Target+TEXT(".pending");
    // 审计 C7：失败时清掉 .pending。原来初次写入失败会直接 return，把临时文件留在磁盘上；
    // 之后每次存档失败都会再留一个同名文件（同名覆盖，但残留本身会让"存档目录里有东西"
    // 看起来像已保存）。这里让两条失败路径都做清理。
    if(!Files.MakeDirectory(*FPaths::GetPath(Target),true))
    {Files.Delete(*Temporary,false);return false;}
    if(!FFileHelper::SaveArrayToFile(Bytes,*Temporary,&Files))
    {Files.Delete(*Temporary,false);return false;}
    // Keep the first pre-structure file. Atomic same-directory replacement
    // leaves the previous committed save intact if the new write fails.
    // 审计 C6：路径改用 BackupPath(Slot)，与 PreStructurePath() 对外暴露的路径保持同一来源。
    const FString Original=BackupPath(Slot);
    if(Files.FileExists(*Target)&&!Files.FileExists(*Original))
    {
        TUniquePtr<FArchive> Old(Files.CreateFileReader(*Target));uint32 OldTag=0;
        // 审计 C7：保留原有逻辑（读旧档头，非 VBX3 才备份），只是在失败分支上补 .pending 清理。
        if(Old&&Old->TotalSize()>=4)
        {
            *Old<<OldTag;Old.Reset();
            if(OldTag!=Magic&&Files.Copy(*Original,*Target,false,false)!=COPY_OK){Files.Delete(*Temporary,false);return false;}
        }
    }
    // FFileManagerGeneric::Move deletes the destination before renaming
    // (FileManagerGeneric.cpp:303 — `if(FileExists(Dest) && Replace && !DeleteFile(Dest))`),
    // so using it here would trade "atomic replace" for "delete then move" and could leave the
    // player with no save at all if the rename then failed. Win64's replacement API keeps the
    // committed file until the swap, which is why this path is deliberately Windows-only.
    //
    // 审计 C7 复核更正：本文件原先的建议是"改用 IFileManager::Move 做跨平台写盘"。核对引擎源码后
    // 确认那条建议**是错的**——Move(Replace=true) 会先删目标再改名，反而会在失败时丢掉旧存档。
    // 要真正跨平台原子替换需要「先把旧档改名成 .bak → 移入新档 → 失败时回滚」，那会改变存档目录
    // 布局与恢复语义，属于需要单独设计与验收的改动，不在本次性能/健壮性批次内。
    // 当前实际影响：非 Windows 构建无法存档（项目构建脚本只出 Win64，尚无其它目标平台），
    // 保持现状并在 VoxelBuildFixPlan 中登记为"独立立项"。
#if PLATFORM_WINDOWS
    FString NativeTarget=FPaths::ConvertRelativePathToFull(Target),NativeTemporary=FPaths::ConvertRelativePathToFull(Temporary);
    FPaths::MakePlatformFilename(NativeTarget);FPaths::MakePlatformFilename(NativeTemporary);
    const bool bMoved=!!::MoveFileExW(*NativeTemporary,*NativeTarget,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH);
    if(!bMoved)Files.Delete(*Temporary,false);   // 审计 C7：换名失败同样不留 .pending
    return bMoved;
#else
    Files.Delete(*Temporary,false);
    return false;
#endif
}
