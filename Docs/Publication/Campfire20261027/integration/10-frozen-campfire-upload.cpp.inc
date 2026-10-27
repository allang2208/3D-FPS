    if(bInventoryRequestPending&&!bInventoryWaitingUpload)return;
    if(bCampfirePending&&!bCampfireWaitingUpload)return;

    // 调试豁免：双进程回归时 -MPNoHeartbeat 只传首包不重传。
    static const bool bNoHeartbeat = FParse::Param(FCommandLine::Get(), TEXT("MPNoHeartbeat"));
    if (bNoHeartbeat && bHasLastSent) { HeartbeatTimer = 60.f; }

    HeartbeatTimer -= DeltaSeconds;
    if (HeartbeatTimer <= 0.f&&!bCampfirePending&&!bInventoryRequestPending&&PendingUpload.IsEmpty())
    {
