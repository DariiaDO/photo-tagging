package com.example.photoalbums.utils

import android.widget.ImageView
import coil.load

object ImageLoader {

    fun load(imageView: ImageView, uri: String?) {
        imageView.load(uri) {
            crossfade(true)
        }
    }
}
