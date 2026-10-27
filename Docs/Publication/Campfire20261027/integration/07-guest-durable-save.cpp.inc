bool AColdSteelPlayerState::SaveShadowToHostDisk()
{
    if (!ShadowModel || SlotName.IsEmpty() || ShadowModel->HasUnconfirmedTransactionSave()) return false;
    ShadowModel->SyncRuntime();
    UColdSteelProfileSave* Save = Cast<UColdSteelProfileSave>(
        UGameplayStatics::CreateSaveGameObject(UColdSteelProfileSave::StaticClass()));
    Save->Profile = ShadowModel->Snapshot();
    if (UGameplayStatics::SaveGameToSlot(Save, SlotName, 0))
    {
        UE_LOG(LogTemp, Warning, TEXT("MPTEST guest profile saved to host disk: %s items=%d hp=%.0f"),
            *SlotName, Save->Profile.Items.Num(), Save->Profile.Health);
        return true;
    }
    UE_LOG(LogTemp,Error,TEXT("Guest profile save failed: %s"),*SlotName);
    return false;
}
