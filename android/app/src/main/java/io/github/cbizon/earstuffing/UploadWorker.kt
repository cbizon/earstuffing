package io.github.cbizon.earstuffing

import android.content.Context
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.util.concurrent.TimeUnit

class HttpError(val code: Int, message: String) : IOException("HTTP $code: $message")

/** Uploads pending notes to R2, audio before sidecar, retrying with backoff when offline. */
class UploadWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val config = Config.load(applicationContext)
        if (config == null) {
            Status.set(applicationContext, "Not uploaded: R2 settings are incomplete")
            return@withContext Result.failure()
        }
        val dir = NoteStore.dir(applicationContext)
        for (id in NoteStore.pending(applicationContext)) {
            val wav = File(dir, "$id.wav")
            val json = File(dir, "$id.json")
            try {
                put(config, "notes/$id.wav", wav.readBytes(), "audio/wav")
                put(config, "notes/$id.json", json.readBytes(), "application/json")
            } catch (e: HttpError) {
                Status.set(applicationContext, "Upload of $id failed: ${e.message}")
                // Auth and permission errors will not fix themselves; server errors might.
                return@withContext if (e.code >= 500) Result.retry() else Result.failure()
            } catch (e: IOException) {
                Status.set(applicationContext, "Upload of $id waiting for network: ${e.message}")
                return@withContext Result.retry()
            }
            wav.delete()
            json.delete()
            Status.set(applicationContext, "Uploaded $id at ${Instant.now()}")
        }
        Result.success()
    }

    private fun put(config: Config, key: String, body: ByteArray, contentType: String) {
        val signed = SigV4.signPut(
            config.host, "/${config.bucket}/$key", body, contentType,
            config.accessKeyId, config.secret, Instant.now(),
        )
        val conn = URL(signed.url).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "PUT"
            conn.doOutput = true
            conn.setFixedLengthStreamingMode(body.size)
            signed.headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
            conn.outputStream.use { it.write(body) }
            val code = conn.responseCode
            if (code !in 200..299) {
                throw HttpError(code, conn.errorStream?.bufferedReader()?.readText()?.take(300) ?: "")
            }
        } finally {
            conn.disconnect()
        }
    }

    companion object {
        fun enqueue(context: Context) {
            val request = OneTimeWorkRequestBuilder<UploadWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork("upload-notes", ExistingWorkPolicy.APPEND_OR_REPLACE, request)
        }
    }
}
