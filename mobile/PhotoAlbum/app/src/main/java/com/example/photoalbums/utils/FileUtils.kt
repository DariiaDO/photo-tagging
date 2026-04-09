package com.example.photoalbums.utils

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import androidx.exifinterface.media.ExifInterface
import java.io.ByteArrayOutputStream
import java.io.IOException
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

fun createImageMultipart(context: Context, uri: Uri): MultipartBody.Part {
    val rotationDegrees = context.contentResolver.openInputStream(uri)?.use { inputStream ->
        ExifInterface(inputStream).rotationDegrees
    } ?: 0

    val bytes = context.contentResolver.openInputStream(uri)?.use { inputStream ->
        val decodedBitmap = BitmapFactory.decodeStream(inputStream)
            ?: throw IOException("Unsupported or unreadable image format")
        decodedBitmap.rotateIfNeeded(rotationDegrees).toJpegBytes()
    } ?: throw IllegalArgumentException("Cannot open input stream")

    val requestFile = bytes.toRequestBody("image/jpeg".toMediaType())
    val filename = buildNormalizedFilename(uri)

    return MultipartBody.Part.createFormData(
        "images",
        filename,
        requestFile
    )
}

fun createTextPart(name: String, value: String): MultipartBody.Part {
    return MultipartBody.Part.createFormData(name, value)
}

private fun Bitmap.rotateIfNeeded(rotationDegrees: Int): Bitmap {
    if (rotationDegrees == 0) return this
    val matrix = Matrix().apply { postRotate(rotationDegrees.toFloat()) }
    val rotated = Bitmap.createBitmap(this, 0, 0, width, height, matrix, true)
    recycle()
    return rotated
}

private fun Bitmap.toJpegBytes(maxDimension: Int = 2048, quality: Int = 90): ByteArray {
    val normalized = scaleDownIfNeeded(maxDimension)
    return ByteArrayOutputStream().use { output ->
        normalized.compress(Bitmap.CompressFormat.JPEG, quality, output)
        if (normalized !== this) {
            normalized.recycle()
        }
        recycle()
        output.toByteArray()
    }
}

private fun Bitmap.scaleDownIfNeeded(maxDimension: Int): Bitmap {
    val largestSide = maxOf(width, height)
    if (largestSide <= maxDimension) return this

    val scale = maxDimension.toFloat() / largestSide.toFloat()
    val targetWidth = (width * scale).toInt().coerceAtLeast(1)
    val targetHeight = (height * scale).toInt().coerceAtLeast(1)
    return Bitmap.createScaledBitmap(this, targetWidth, targetHeight, true)
}

private fun buildNormalizedFilename(uri: Uri): String {
    val baseName = uri.lastPathSegment
        ?.substringAfterLast('/')
        ?.substringBeforeLast('.')
        ?.takeIf { it.isNotBlank() }
        ?: "photo"
    return "${baseName}.jpg"
}
