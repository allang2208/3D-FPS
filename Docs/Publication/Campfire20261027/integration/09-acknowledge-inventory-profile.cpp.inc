void AColdSteelPlayerState::AcknowledgeInventoryProfile()
{
    auto* M=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>();if(!M)return;
    if(!ScratchSave)ScratchSave=NewObject<UColdSteelProfileSave>();
    ScratchSave->Profile=M->Snapshot();ConfirmedSouls=ScratchSave->Profile.Souls;ConfirmedSoulCredits=ScratchSave->Profile.ServerSoulCredits;ConfirmedSoulDebits=ScratchSave->Profile.ServerSoulDebits;
    if(!SaveToBlob(ScratchSave,LastSentBlob))return;
    NormalizeProfileForCompare(ScratchSave->Profile);if(!SaveToBlob(ScratchSave,LastSentNormBlob))return;
    bHasLastSent=true;LastUploadAt=GetWorld()->GetRealTimeSeconds();HeartbeatTimer=2.f;
    if(!bHasUploadedAppearance||M->PlayerHeadId()!=UploadedHeadId||M->PlayerHairId()!=UploadedHairId)
    {bHasLastSent=false;HeartbeatTimer=0.f;}
}
