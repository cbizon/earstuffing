package io.github.cbizon.earstuffing

import android.content.Context
import org.json.JSONObject
import java.io.File
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.UUID

/**
 * Notes waiting to upload, kept in app storage so nothing is lost without signal.
 * Each note is <id>.wav plus <id>.json; the sidecar is written last.
 */
object NoteStore {
    private val idFormat = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss").withZone(ZoneOffset.UTC)

    fun dir(context: Context) = File(context.filesDir, "pending").apply { mkdirs() }

    fun newId(now: Instant = Instant.now()) = "${idFormat.format(now)}-${UUID.randomUUID().toString().take(6)}"

    fun pcm(context: Context, id: String) = File(dir(context), "$id.pcm")

    fun finish(context: Context, id: String, recordedAt: Instant, durationMs: Long, media: NowPlaying?) {
        val pcm = pcm(context, id)
        Wav.fromPcm(pcm, File(dir(context), "$id.wav"), CarAudio.SAMPLE_RATE)
        pcm.delete()
        val sidecar = JSONObject()
            .put("id", id)
            .put("recorded_at", recordedAt.toString())
            .put("duration_ms", durationMs)
            .put("audio", "$id.wav")
            .put("media_title", media?.title ?: JSONObject.NULL)
            .put("media_artist", media?.artist ?: JSONObject.NULL)
            .put("media_package", media?.packageName ?: JSONObject.NULL)
            .put("position_ms", media?.positionMs ?: JSONObject.NULL)
        File(dir(context), "$id.json").writeText(sidecar.toString(2))
    }

    fun discard(context: Context, id: String) {
        pcm(context, id).delete()
    }

    /** Complete notes (sidecar present), oldest first. */
    fun pending(context: Context): List<String> =
        dir(context).listFiles { f -> f.name.endsWith(".json") }!!.map { it.name.removeSuffix(".json") }.sorted()
}
