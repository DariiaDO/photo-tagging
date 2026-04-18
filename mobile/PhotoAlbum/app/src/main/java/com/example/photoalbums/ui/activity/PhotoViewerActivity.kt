package com.example.photoalbums.ui.activity

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.photoalbums.databinding.ActivityPhotoViewerBinding
import com.example.photoalbums.utils.ImageLoader
import com.example.photoalbums.utils.ImageSourceResolver

class PhotoViewerActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val binding = ActivityPhotoViewerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val imageUrl = intent.getStringExtra(EXTRA_IMAGE_URL)
        val fallbackUri = intent.getStringExtra(EXTRA_FALLBACK_URI)
        ImageLoader.load(
            binding.fullscreenImage,
            ImageSourceResolver.resolve(imageUrl, null),
            ImageSourceResolver.resolve(null, fallbackUri)
        )

        binding.closeButton.setOnClickListener { finish() }
        binding.fullscreenImage.setOnClickListener { finish() }
    }

    companion object {
        private const val EXTRA_IMAGE_URL = "image_url"
        private const val EXTRA_FALLBACK_URI = "fallback_uri"

        fun createIntent(context: android.content.Context, imageUrl: String?, fallbackUri: String?): Intent {
            return Intent(context, PhotoViewerActivity::class.java)
                .putExtra(EXTRA_IMAGE_URL, imageUrl)
                .putExtra(EXTRA_FALLBACK_URI, fallbackUri)
        }
    }
}
