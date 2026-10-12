package io.github.cbizon.earstuffing

import org.junit.Assert.assertEquals
import org.junit.Test
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant

class SigV4Test {
    // Expected values come from botocore's S3SigV4Auth for the same request.
    @Test
    fun matchesBotocore() {
        val signed = SigV4.signPut(
            host = "acct123.r2.cloudflarestorage.com",
            path = "/earstuffing-notes/notes/20261011-081503-ab12cd.wav",
            body = "hello note".toByteArray(),
            contentType = "audio/wav",
            accessKeyId = "AKIDEXAMPLE",
            secret = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY",
            now = Instant.parse("2026-10-12T00:18:44Z"),
        )
        assertEquals(
            "AWS4-HMAC-SHA256 Credential=AKIDEXAMPLE/20261012/auto/s3/aws4_request, " +
                "SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, " +
                "Signature=72ed0d3a75166cf736e6176f00f7c80b6647ec9a9652c0c4458e1301e10a8c45",
            signed.headers["Authorization"],
        )
        assertEquals(
            "https://acct123.r2.cloudflarestorage.com/earstuffing-notes/notes/20261011-081503-ab12cd.wav",
            signed.url,
        )
    }

    @Test
    fun encodesReservedCharacters() {
        assertEquals("a%20b%2Bc~d", SigV4.uriEncode("a b+c~d"))
    }
}

class WavTest {
    @Test
    fun headerFields() {
        val h = ByteBuffer.wrap(Wav.header(dataBytes = 32000, sampleRate = 16000)).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(36 + 32000, h.getInt(4))
        assertEquals(16000, h.getInt(24))
        assertEquals(32000, h.getInt(28))
        assertEquals(32000, h.getInt(40))
    }
}
