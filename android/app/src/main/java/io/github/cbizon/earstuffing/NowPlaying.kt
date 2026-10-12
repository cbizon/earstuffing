package io.github.cbizon.earstuffing

import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.SystemClock
import android.service.notification.NotificationListenerService
import androidx.core.app.NotificationManagerCompat

/** Exists only so the app can be granted notification access, which unlocks media session info. */
class MediaListener : NotificationListenerService()

data class NowPlaying(val title: String?, val artist: String?, val packageName: String, val positionMs: Long?)

fun hasMediaAccess(context: Context) =
    NotificationManagerCompat.getEnabledListenerPackages(context).contains(context.packageName)

/** What is playing right now, preferring a session that is actively playing. */
fun currentMedia(context: Context): NowPlaying? {
    if (!hasMediaAccess(context)) return null
    val manager = context.getSystemService(MediaSessionManager::class.java)
    val sessions = manager.getActiveSessions(ComponentName(context, MediaListener::class.java))
    val controller = sessions.firstOrNull { it.playbackState?.state == PlaybackState.STATE_PLAYING }
        ?: sessions.firstOrNull() ?: return null
    val state = controller.playbackState
    val position = state?.let {
        if (it.state == PlaybackState.STATE_PLAYING) {
            it.position + ((SystemClock.elapsedRealtime() - it.lastPositionUpdateTime) * it.playbackSpeed).toLong()
        } else it.position
    }
    return NowPlaying(
        controller.metadata?.getString(MediaMetadata.METADATA_KEY_TITLE),
        controller.metadata?.getString(MediaMetadata.METADATA_KEY_ARTIST),
        controller.packageName,
        position,
    )
}
