package io.github.cbizon.earstuffing

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts

/** Phone-side setup: R2 credentials, permissions, and upload status. */
class SettingsActivity : ComponentActivity() {
    private lateinit var status: TextView
    private val micPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { refresh() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val pad = (16 * resources.displayMetrics.density).toInt()
        val column = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(pad, pad, pad, pad)
        }

        fun field(label: String, key: String, default: String = "", secret: Boolean = false): EditText {
            column.addView(TextView(this).apply { text = label })
            return EditText(this).apply {
                setText(Config.raw(this@SettingsActivity, key, default))
                inputType = if (secret) {
                    InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
                } else InputType.TYPE_CLASS_TEXT
                column.addView(this)
            }
        }

        val account = field("R2 account ID", "account_id")
        val bucket = field("Notes bucket", "bucket", "earstuffing-notes")
        val keyId = field("Access key ID", "access_key_id")
        val secret = field("Secret access key", "secret", secret = true)

        fun button(label: String, onClick: () -> Unit) =
            column.addView(Button(this).apply { text = label; setOnClickListener { onClick() } })

        button("Save and upload pending notes") {
            Config.save(this, Config(account.text.toString(), bucket.text.toString(),
                keyId.text.toString(), secret.text.toString()))
            UploadWorker.enqueue(this)
            refresh()
        }
        button("Allow microphone") { micPermission.launch(Manifest.permission.RECORD_AUDIO) }
        button("Allow reading what's playing (notification access)") {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }
        button("Refresh status") { refresh() }

        status = TextView(this).apply { setPadding(0, pad, 0, 0) }
        column.addView(status)
        setContentView(ScrollView(this).apply { addView(column) })
    }

    override fun onResume() {
        super.onResume()
        refresh()
    }

    private fun refresh() {
        val mic = checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        status.text = listOf(
            "Settings: " + if (Config.load(this) != null) "complete" else "incomplete",
            "Microphone: " + if (mic) "allowed" else "not allowed",
            "Now-playing access: " + if (hasMediaAccess(this)) "allowed" else "not allowed",
            "Notes waiting to upload: ${NoteStore.pending(this).size}",
            "Last upload: ${Status.get(this)}",
        ).joinToString("\n")
    }
}
