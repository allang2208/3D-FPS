#include "VoxelBuildWorld.h"
#include "VoxelBuildPrefabActor.h"
#include "GameFramework/PlayerState.h"

FVoxelBuildUndoHistory::FStack& FVoxelBuildUndoHistory::For(APlayerState* Player)
{
    return Player?Players.FindOrAdd(Player):Local;
}

void FVoxelBuildUndoHistory::Remember(APlayerState* Player,FVoxelBuildUndoEntry Entry)
{
    FStack& Stack=For(Player);
    if(Stack.Num()>=32)Stack.RemoveAt(0);
    Stack.Add(MoveTemp(Entry));
}

void FVoxelBuildUndoHistory::InvalidateCells(const TArray<FVoxelEditCell>& Edits)
{
    TSet<FVoxelBuildKey> Touched;
    for(const auto& E:Edits)Touched.Add({E.Volume,E.Position});
    if(Touched.IsEmpty())return;
    const auto WasTouched=[&](const FVoxelEditCell& E){return Touched.Contains({E.Volume,E.Position});};
    const auto Invalidate=[&](FStack& Stack)
    {
        for(int32 I=Stack.Num()-1;I>=0;--I)
        {
            auto& Cells=Stack[I].Blocks;
            if(!Cells||!Cells->ContainsByPredicate(WasTouched))continue;
            auto Remaining=Cells->FilterByPredicate([&](const auto& E){return !WasTouched(E);});
            if(Remaining.IsEmpty())Stack.RemoveAt(I);
            else Cells=MakeShared<TArray<FVoxelEditCell>>(MoveTemp(Remaining));
        }
    };
    Invalidate(Local);
    for(auto& Player:Players)Invalidate(Player.Value);
}

void FVoxelBuildUndoHistory::ClearVoxelBatches(APlayerState* Player)
{
    For(Player).RemoveAll([](const auto& Entry){return Entry.Blocks.IsValid();});
}

void FVoxelBuildUndoHistory::ForgetDisconnected()
{
    for(auto It=Players.CreateIterator();It;++It)if(!It.Key().IsValid())It.RemoveCurrent();
}

bool AVoxelBuildWorld::Undo()
{
    return Undo(nullptr);
}

bool AVoxelBuildWorld::Undo(TMap<FName,int32>* OutRemovedBlocks)
{
    if(OutRemovedBlocks)OutRemovedBlocks->Reset();
    if(!bReady||!HasAuthority())return false;
    auto& Stack=UndoHistory.For(UndoPlayer);
    while(!Stack.IsEmpty())
    {
        // Pop before the edit. Removing blocks may also invalidate older batches.
        FVoxelBuildUndoEntry Entry=Stack.Pop(EAllowShrinking::No);
        if(Entry.PrefabInstance.IsValid())
        {
            auto* Piece=PrefabActorAt(Entry.Anchor);
            if(!Piece||Piece->IsFalling()||PrefabInstanceIdentity(Entry.Anchor)!=Entry.PrefabInstance)continue;
            if(!DismantlePrefab(Piece,false))
            {
                Stack.Add(MoveTemp(Entry)); // A busy station can be retried after its contents are collected.
                return false;
            }
            Message=TEXT("已撤销最近放置的构件");
            return true;
        }
        TArray<FVoxelEditCell> Reverse;
        TMap<FName,int32> Removed;
        for(const FVoxelEditCell& E:*Entry.Blocks)
        {
            if(VolumeMaterialAt(E.Volume,E.Position)!=E.After)continue;
            Removed.FindOrAdd(E.After)++;
            Reverse.Add({E.Position,E.After,NAME_None,E.Volume});
        }
        if(Reverse.IsEmpty())continue;
        if(!Commit(Reverse,false))
        {
            Stack.Add(MoveTemp(Entry));
            return false;
        }
        if(OutRemovedBlocks)*OutRemovedBlocks=MoveTemp(Removed);
        const int32 Missing=Entry.Blocks->Num()-Reverse.Num();
        Message=FString::Printf(TEXT("已拆除最近一批建造 · %d 格"),Reverse.Num());
        if(Missing>0)Message+=FString::Printf(TEXT(" · 其中 %d 格已不存在"),Missing);
        return true;
    }
    Message=TEXT("没有可撤销的建造");return false;
}
