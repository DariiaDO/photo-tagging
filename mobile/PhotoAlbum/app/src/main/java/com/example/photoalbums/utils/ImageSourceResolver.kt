package com.example.photoalbums.utils

import com.example.photoalbums.BuildConfig

object ImageSourceResolver {

    fun resolve(imageUrl: String?, fallbackUri: String?): String? {
        val normalizedImageUrl = imageUrl?.trim().orEmpty()
        if (normalizedImageUrl.isNotEmpty()) {
            return if (
                normalizedImageUrl.startsWith("http://") ||
                normalizedImageUrl.startsWith("https://") ||
                normalizedImageUrl.startsWith("content://") ||
                normalizedImageUrl.startsWith("file://")
            ) {
                normalizedImageUrl
            } else {
                BuildConfig.API_BASE_URL.trimEnd('/') + "/" + normalizedImageUrl.trimStart('/')
            }
        }
        return fallbackUri?.trim().takeIf { !it.isNullOrEmpty() }
    }
}
