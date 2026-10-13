package io.github.cbizon.earstuffing

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import androidx.car.app.CarAppService
import androidx.car.app.versioning.CarAppApiLevels
import androidx.car.app.CarContext
import androidx.car.app.CarToast
import androidx.car.app.Screen
import androidx.car.app.Session
import androidx.car.app.model.Action
import androidx.car.app.model.MessageTemplate
import androidx.car.app.model.Template
import androidx.car.app.validation.HostValidator
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import java.time.Instant

class NotesCarAppService : CarAppService() {
    // Sideloaded personal app: accept any Android Auto host.
    override fun createHostValidator() = HostValidator.ALLOW_ALL_HOSTS_VALIDATOR

    override fun onCreateSession() = object : Session() {
        override fun onCreateScreen(intent: Intent): Screen = NoteScreen(carContext)
    }
}

/** One button: Record, then Stop. Notes auto-stop after five minutes in case you forget. */
class NoteScreen(carContext: CarContext) : Screen(carContext) {
    private val maxMs = 5 * 60 * 1000L
    private val handler = Handler(Looper.getMainLooper())
    private val autoStop = Runnable { stop() }

    private var recorder: NoteRecorder? = null
    private var id = ""
    private var startedAt = Instant.EPOCH
    private var media: NowPlaying? = null
    private var message = "Tap Record, talk, then tap Stop."

    init {
        lifecycle.addObserver(object : DefaultLifecycleObserver {
            override fun onDestroy(owner: LifecycleOwner) {
                if (recorder != null) stop()
            }
        })
    }

    override fun onGetTemplate(): Template {
        val recording = recorder != null
        val action = Action.Builder()
            .setTitle(if (recording) "Stop" else "Record")
            .setFlags(Action.FLAG_PRIMARY)
            .setOnClickListener { if (recording) stop() else start() }
            .build()
        val text = if (recording) "Recording… ${media?.title ?: ""}".trim() else message
        return MessageTemplate.Builder(text)
            .setTitle(if (recording) "Recording note" else "Earstuffing note")
            .setHeaderAction(Action.APP_ICON)
            .addAction(action)
            .build()
    }

    private fun start() {
        if (carContext.carAppApiLevel < CarAppApiLevels.LEVEL_5) {
            message = "This car's Android Auto is too old for microphone recording (level ${carContext.carAppApiLevel})."
            invalidate()
            return
        }
        if (carContext.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            carContext.requestPermissions(listOf(Manifest.permission.RECORD_AUDIO)) { granted, _ ->
                if (granted.isNotEmpty()) start() else {
                    message = "Microphone permission is needed. Grant it in the phone app."
                    invalidate()
                }
            }
            return
        }
        media = currentMedia(carContext)
        id = NoteStore.newId()
        startedAt = Instant.now()
        recorder = NoteRecorder(carContext).also { it.start(NoteStore.pcm(carContext, id)) }
        handler.postDelayed(autoStop, maxMs)
        invalidate()
    }

    private fun stop() {
        val r = recorder ?: return
        handler.removeCallbacks(autoStop)
        r.stop()
        recorder = null
        val durationMs = Instant.now().toEpochMilli() - startedAt.toEpochMilli()
        NoteStore.finish(carContext, id, startedAt, durationMs, media)
        UploadWorker.enqueue(carContext)
        message = "Saved${media?.title?.let { " for \"$it\"" } ?: ""}. Tap Record for another."
        CarToast.makeText(carContext, "Note saved", CarToast.LENGTH_SHORT).show()
        invalidate()
    }
}
