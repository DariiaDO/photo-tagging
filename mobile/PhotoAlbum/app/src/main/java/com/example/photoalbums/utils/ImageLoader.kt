package com.example.photoalbums.utils

import android.net.Uri
import android.widget.ImageView
import coil.load

object ImageLoader {

    fun load(imageView: ImageView, primarySource: String?, fallbackSource: String? = null) {
        val primary = primarySource.toCoilData()
        val fallback = fallbackSource
            ?.takeIf { it.trim() != primarySource?.trim() }
            .toCoilData()

        imageView.load(primary) {
            crossfade(true)
            if (fallback != null) {
                listener(
                    onError = { _, _ ->
                        imageView.load(fallback) {
                            crossfade(true)
                        }
                    }
                )
            }
        }
    }

    private fun String?.toCoilData(): Any? {
        val value = this?.trim().takeIf { !it.isNullOrEmpty() } ?: return null
        return if (
            value.startsWith("content://") ||
            value.startsWith("file://")
        ) {
            Uri.parse(value)
        } else {
            value
        }
    }
}
