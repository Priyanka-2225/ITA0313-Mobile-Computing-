class UploadWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result {
        val id = inputData.getLong("recordId", -1)
        val repo = RecordRepository.get(applicationContext)          // Room + Keystore encrypted store
        if (!SessionManager.isLoggedIn() || !Permissions.granted(applicationContext)) {
            repo.cleanupTemp(id); return Result.failure()           // CANCEL + undo
        }
        val rec = repo.load(id)
        if (rec.sensitive && !rec.encrypted) repo.encrypt(rec)       // security precondition
        return try {
            Api.upload(rec)                                          // TLS; returns on success
            repo.markSynced(id); Result.success()
        } catch (e: IOException) {
            repo.cleanupTemp(id)                                     // UNDO partial chunk
            if (runAttemptCount > 5) Result.failure() else Result.retry()   // backoff handled by WorkManager
        }
    }
}

fun enqueue(ctx: Context, id: Long, critical: Boolean) {
    val constraints = Constraints.Builder()
        .setRequiredNetworkType(NetworkType.CONNECTED)
        .setRequiresBatteryNotLow(!critical)                         // critical work is exempt
        .build()
    val req = OneTimeWorkRequestBuilder<UploadWorker>()
        .setConstraints(constraints)
        .setInputData(workDataOf("recordId" to id))
        .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
        .addTag("upload")                                            // cancelAllWorkByTag("upload") on logout
        .apply { if (critical) setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST) }
        .build()
    WorkManager.getInstance(ctx).enqueueUniqueWork("rec-$id", ExistingWorkPolicy.KEEP, req)
}
