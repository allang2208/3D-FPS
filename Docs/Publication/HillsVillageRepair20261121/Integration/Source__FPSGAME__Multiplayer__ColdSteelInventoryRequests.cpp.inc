// Source/FPSGAME/Multiplayer/ColdSteelInventoryRequests.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 408-409 | void AColdSteelPlayerState::QueueInventoryReply(const FColdSteelInventoryRequest& Request,bool Success,
         if(!Success||Request.Action!=EColdSteelInventoryAction::ContainerOpen||Request.Count!=-1)
             Model->PostNotice(Request.Action==EColdSteelInventoryAction::Building?TEXT("建造"):TEXT("物品操作"),Reason);}

// Lines 504-505 | void AColdSteelPlayerState::ClientInventoryReplyChunk_Implementation(uint32 Sequence,int32 Index,int32 Total,const TArray<uint8>& Chunk)
            Model->PostNotice(PendingInventoryRequest.Action==EColdSteelInventoryAction::Building?TEXT("建造"):TEXT("联机物品操作"),
                Applied?Reply->Message:TEXT("结果正在重新同步"));
