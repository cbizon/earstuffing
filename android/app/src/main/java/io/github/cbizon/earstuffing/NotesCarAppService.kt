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

/**
 * Opening the app starts recording; Stop saves and returns to the dashboard, Discard drops it.
 * There is deliberately no silence detection, so thoughtful pauses never end a note. The only
 * automatic stop is a ten-minute cap for a forgotten recording.
 */
class NoteScreen(carContext: CarContext) : Screen(carContext) {
    private val maxMs = 10 * 60 * 1000L
    private val handler = Handler(Looper.getMainLooper())
    private val autoStop = Runnable { finishNote(save = true) }

    private var recorder: NoteRecorder? = null
    private var autoStarted = false
    private var id = ""
    private var startedAt = Instant.EPOCH
    private var media: NowPlaying? = null
    private var message = ""

    init {
        lifecycle.addObserver(object : DefaultLifecycleObserver {
            override fun onStart(owner: LifecycleOwner) {
                if (!autoStarted) {
                    autoStarted = true
                    start()
                }
            }

            // Leaving mid-note (e.g. the session ends) keeps what was said.
            override fun onDestroy(owner: LifecycleOwner) {
                if (recorder != null) finishNote(save = true, close = false)
            }
        })
    }

    override fun onGetTemplate(): Template {
        if (recorder != null) {
            val stop = Action.Builder()
                .setTitle("Stop")
                .setFlags(Action.FLAG_PRIMARY)
                .setOnClickListener { finishNote(save = true) }
                .build()
            val discard = Action.Builder()
                .setTitle("Discard")
                .setOnClickListener { finishNote(save = false) }
                .build()
            return MessageTemplate.Builder("Recording… ${media?.title ?: ""}".trim())
                .setTitle("Recording note")
                .setHeaderAction(Action.APP_ICON)
                .addAction(stop)
                .addAction(discard)
                .build()
        }
        // Only reached when recording could not start.
        val retry = Action.Builder()
            .setTitle("Record")
            .setFlags(Action.FLAG_PRIMARY)
            .setOnClickListener { start() }
            .build()
        return MessageTemplate.Builder(message.ifEmpty { "Starting…" })
            .setTitle("Earstuffing note")
            .setHeaderAction(Action.APP_ICON)
            .addAction(retry)
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

    private fun finishNote(save: Boolean, close: Boolean = true) {
        val r = recorder ?: return
        handler.removeCallbacks(autoStop)
        r.stop()
        recorder = null
        if (save) {
            val durationMs = Instant.now().toEpochMilli() - startedAt.toEpochMilli()
            NoteStore.finish(carContext, id, startedAt, durationMs, media)
            UploadWorker.enqueue(carContext)
        } else {
            NoteStore.discard(carContext, id)
        }
        if (close) {
            CarToast.makeText(carContext, if (save) "Note saved" else "Note discarded", CarToast.LENGTH_SHORT).show()
            // Back to the map and media dashboard.
            carContext.finishCarApp()
        }
    }
}
