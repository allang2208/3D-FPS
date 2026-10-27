    // Settle against the authority clock before comparing upload receipts. An
    // upload captured before expiry must not resurrect the consumed raw item.
    if(ShadowModel&&ShadowModel->RuntimePawn()&&ShadowModel->RuntimePawn()->HasAuthority())
        ShadowModel->SettleFoodSpoilage(true);
    if(ShadowModel&&ShadowModel->HasUnconfirmedTransactionSave())
    {ClientProfileSyncRejected(TEXT("交易保存结果待恢复，已停止覆盖主机档案"));return false;}
