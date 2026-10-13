package io.github.cbizon.earstuffing

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** Wrap raw 16-bit little-endian PCM in a WAV header. */
object Wav {
    fun header(dataBytes: Int, sampleRate: Int, channels: Int = 1, bitsPerSample: Int = 16): ByteArray {
        val byteRate = sampleRate * channels * bitsPerSample / 8
        return ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN).apply {
            put("RIFF".toByteArray()); putInt(36 + dataBytes); put("WAVE".toByteArray())
            put("fmt ".toByteArray()); putInt(16); putShort(1); putShort(channels.toShort())
            putInt(sampleRate); putInt(byteRate); putShort((channels * bitsPerSample / 8).toShort())
            putShort(bitsPerSample.toShort())
            put("data".toByteArray()); putInt(dataBytes)
        }.array()
    }

    fun fromPcm(pcm: File, wav: File, sampleRate: Int) {
        wav.outputStream().use { out ->
            out.write(header(pcm.length().toInt(), sampleRate))
            pcm.inputStream().use { it.copyTo(out) }
        }
    }
}
