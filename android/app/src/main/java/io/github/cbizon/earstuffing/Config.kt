package io.github.cbizon.earstuffing

import android.content.Context

/** R2 settings typed in on the phone. The key may only write to the notes bucket. */
data class Config(val accountId: String, val bucket: String, val accessKeyId: String, val secret: String) {
    val host get() = "$accountId.r2.cloudflarestorage.com"

    companion object {
        private const val PREFS = "config"

        fun load(context: Context): Config? {
            val p = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val c = Config(
                p.getString("account_id", "")!!, p.getString("bucket", "earstuffing-notes")!!,
                p.getString("access_key_id", "")!!, p.getString("secret", "")!!,
            )
            return if (listOf(c.accountId, c.bucket, c.accessKeyId, c.secret).all { it.isNotBlank() }) c else null
        }

        fun save(context: Context, c: Config) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putString("account_id", c.accountId.trim()).putString("bucket", c.bucket.trim())
                .putString("access_key_id", c.accessKeyId.trim()).putString("secret", c.secret.trim())
                .apply()
        }

        fun raw(context: Context, key: String, default: String = "") =
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(key, default)!!
    }
}

/** Last upload outcome, shown in the phone settings screen. */
object Status {
    fun set(context: Context, message: String) =
        context.getSharedPreferences("status", Context.MODE_PRIVATE).edit().putString("last", message).apply()

    fun get(context: Context) =
        context.getSharedPreferences("status", Context.MODE_PRIVATE).getString("last", "No uploads yet")!!
}
