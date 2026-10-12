package io.github.cbizon.earstuffing

import java.security.MessageDigest
import java.time.Instant
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

/** AWS Signature Version 4 for a single S3 PUT, which is all R2 needs from the phone. */
object SigV4 {
    private val amzFormat = DateTimeFormatter.ofPattern("yyyyMMdd'T'HHmmss'Z'").withZone(ZoneOffset.UTC)

    data class Signed(val url: String, val headers: Map<String, String>)

    fun signPut(
        host: String,
        path: String,
        body: ByteArray,
        contentType: String,
        accessKeyId: String,
        secret: String,
        now: Instant,
        region: String = "auto",
    ): Signed {
        val amzDate = amzFormat.format(now)
        val date = amzDate.substring(0, 8)
        val payloadHash = hex(sha256(body))
        val canonicalPath = path.split("/").joinToString("/") { uriEncode(it) }
        val headers = sortedMapOf(
            "content-type" to contentType,
            "host" to host,
            "x-amz-content-sha256" to payloadHash,
            "x-amz-date" to amzDate,
        )
        val canonicalHeaders = headers.entries.joinToString("") { "${it.key}:${it.value}\n" }
        val signedHeaders = headers.keys.joinToString(";")
        val canonicalRequest = listOf("PUT", canonicalPath, "", canonicalHeaders, signedHeaders, payloadHash)
            .joinToString("\n")
        val scope = "$date/$region/s3/aws4_request"
        val stringToSign = listOf("AWS4-HMAC-SHA256", amzDate, scope, hex(sha256(canonicalRequest.toByteArray())))
            .joinToString("\n")
        var key = hmac("AWS4$secret".toByteArray(), date)
        for (part in listOf(region, "s3", "aws4_request")) key = hmac(key, part)
        val signature = hex(hmac(key, stringToSign))
        val auth = "AWS4-HMAC-SHA256 Credential=$accessKeyId/$scope, " +
            "SignedHeaders=$signedHeaders, Signature=$signature"
        return Signed(
            url = "https://$host$canonicalPath",
            headers = headers.filterKeys { it != "host" } + ("Authorization" to auth),
        )
    }

    /** S3 URI encoding of one path segment: everything but unreserved characters is escaped. */
    fun uriEncode(segment: String): String = buildString {
        for (b in segment.toByteArray(Charsets.UTF_8)) {
            val c = b.toInt().toChar()
            if (c.isLetterOrDigit() && c.code < 128 || c in "-._~") append(c)
            else append("%%%02X".format(b.toInt() and 0xff))
        }
    }

    private fun sha256(data: ByteArray) = MessageDigest.getInstance("SHA-256").digest(data)

    private fun hmac(key: ByteArray, data: String): ByteArray =
        Mac.getInstance("HmacSHA256").run {
            init(SecretKeySpec(key, "HmacSHA256"))
            doFinal(data.toByteArray())
        }

    private fun hex(bytes: ByteArray) = bytes.joinToString("") { "%02x".format(it) }
}
