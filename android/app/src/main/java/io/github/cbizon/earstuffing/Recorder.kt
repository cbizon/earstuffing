package io.github.cbizon.earstuffing

import android.Manifest
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager
import androidx.car.app.CarContext
import androidx.car.app.media.CarAudioRecord
import java.io.File

object CarAudio {
    const val SAMPLE_RATE = CarAudioRecord.AUDIO_CONTENT_SAMPLING_RATE
}

/**
 * Records from the car microphone to a PCM file. Taking transient exclusive audio focus
 * pauses the podcast while you talk; it resumes when focus is released.
 */
class NoteRecorder(private val carContext: CarContext) {
    private val audioManager = carContext.getSystemService(AudioManager::class.java)
    private val focus = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_EXCLUSIVE)
        .setAudioAttributes(
            AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ASSISTANT)
                .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                .build()
        )
        .setOnAudioFocusChangeListener { }
        .build()
    private var record: CarAudioRecord? = null
    private var thread: Thread? = null
    @Volatile private var running = false

    fun start(out: File) {
        if (carContext.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            throw SecurityException("Microphone permission not granted")
        }
        audioManager.requestAudioFocus(focus)
        val r = CarAudioRecord.create(carContext)
        record = r
        r.startRecording()
        running = true
        thread = Thread {
            out.outputStream().use { stream ->
                val buffer = ByteArray(CarAudioRecord.AUDIO_CONTENT_BUFFER_SIZE)
                while (running) {
                    val n = r.read(buffer, 0, buffer.size)
                    if (n < 0) break
                    if (n > 0) stream.write(buffer, 0, n)
                }
            }
        }.apply { start() }
    }

    fun stop() {
        running = false
        record?.stopRecording()
        thread?.join(3000)
        audioManager.abandonAudioFocusRequest(focus)
    }
}
