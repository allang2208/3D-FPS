    if(Guest.NetworkProfileId.IsValid())
    {
        if(BoundProfileId.IsValid()&&BoundProfileId!=Guest.NetworkProfileId)return false;
        if(!BoundProfileId.IsValid())
        {
            // One live player per durable profile. Otherwise two shadow models overwrite one save slot.
            for(TActorIterator<AColdSteelPlayerState> It(GetWorld());It;++It)
            {
                if(*It==this||It->IsActorBeingDestroyed())continue;
                const auto* OtherPC=Cast<APlayerController>(It->GetOwner());
                if(!OtherPC||OtherPC->PlayerState!=*It)continue;
                FGuid OtherId=It->BoundProfileId;
                if(OtherPC->IsLocalController())
                    if(const auto* Host=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())OtherId=Host->Snapshot().NetworkProfileId;
                if(OtherId==Guest.NetworkProfileId)
                {ClientProfileSyncRejected(TEXT("此角色档案已被房间内另一名玩家使用，请切换档案后重新加入"));return false;}
            }
            BoundProfileId=Guest.NetworkProfileId;
            if(const auto* Session=GetWorld()->GetSubsystem<UColdSteelNetWorldSubsystem>())
                for(FName Key:Session->RestoreGuestKeys(BoundProfileId))SessionDoorKeys.AddUnique(Key);
            SlotName=TEXT("ColdSteelMP_Profile_")+BoundProfileId.ToString(EGuidFormats::Digits);
            // Null-subsystem PIE player names change on reconnect. Bind durable
            // receipts to the isolated saved profile, never that temporary name.
            if(ShadowModel&&ShadowModel->Snapshot().NetworkProfileId!=BoundProfileId)ShadowModel=nullptr;
            auto* Session=GetGameInstance()->GetSubsystem<UColdSteelNetSessionSubsystem>();
            if(auto* Cached=Session?Session->RestoreGuestProfile(GetWorld(),BoundProfileId):nullptr)
            {
                // Never discard the last live state merely because logout could not write it.
                if(Cached->HasUnconfirmedTransactionSave())
                {BoundProfileId.Invalidate();ClientProfileSyncRejected(TEXT("此档案的交易保存结果待恢复，请主机保留存档并重启后再加入"));return false;}
                ShadowModel=Cached;bRestoreGuestAmmo=true;
                // Restore the saved resources before the upload merge reads the new pawn's components.
                ApplyShadowToServerPawn();
            }
            else if(UGameplayStatics::DoesSaveGameExist(SlotName,0))
            {
                auto* Stored=Cast<UColdSteelProfileSave>(UGameplayStatics::LoadGameFromSlot(SlotName,0));
                if(!Stored||Stored->Profile.NetworkProfileId!=BoundProfileId)
                {
                    // An existing unreadable/mismatched host slot is evidence, not a new guest.
                    BoundProfileId.Invalidate();ClientProfileSyncRejected(TEXT("主机已有客机档案无法读取或身份不符，已保留文件，未用上传档案覆盖"));return false;
                }
                if(!ApplyGuestProfile(Stored->Profile)){BoundProfileId.Invalidate();return false;}
                bRestoreGuestAmmo=ShadowModel!=nullptr;
            }
        }
    }
