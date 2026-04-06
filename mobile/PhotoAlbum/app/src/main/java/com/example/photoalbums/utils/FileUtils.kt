package com.example.photoalbums.utils

import android.content.Context
import android.net.Uri
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody

fun createMultipart(context: Context, uri: Uri): MultipartBody.Part {

    val bytes = context.contentResolver.openInputStream(uri)?.use { inputStream ->
        inputStream.readBytes()
    } ?: throw IllegalArgumentException("Cannot open input stream")

    val requestFile = bytes.toRequestBody("image/*".toMediaType())

    return MultipartBody.Part.createFormData(
        "file",
        "photo.jpg",
        requestFile
    )
}
