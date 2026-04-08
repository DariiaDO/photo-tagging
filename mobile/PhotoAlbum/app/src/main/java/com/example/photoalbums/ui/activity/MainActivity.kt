package com.example.photoalbums.ui.activity

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.MediaStore
import android.view.View
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.core.widget.doAfterTextChanged
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.photoalbums.R
import com.example.photoalbums.data.local.AppDatabase
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.data.local.UserPreferences
import com.example.photoalbums.data.remote.ClientApi
import com.example.photoalbums.data.repository.PhotoRepository
import com.example.photoalbums.databinding.ActivityMainBinding
import com.example.photoalbums.ui.adapter.AlbumAdapter
import com.example.photoalbums.utils.GroupingUtils
import com.example.photoalbums.viewmodel.PhotoViewModel
import com.google.android.material.chip.Chip
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var viewModel: PhotoViewModel
    private lateinit var albumAdapter: AlbumAdapter

    private var selectedUris: List<Uri> = emptyList()

    private val pickImages =
        registerForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(50)) { uris ->
            selectedUris = uris.distinctBy { it.toString() }
            updateSyncButtonState()
            updateSelectedSummary()
        }

    private val requestImagesPermission =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                loadAllDevicePhotos()
            } else {
                showToast(R.string.permission_required_message)
            }
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val db = AppDatabase.getInstance(this)
        val repo = PhotoRepository(db.photoDao(), ClientApi.api, UserPreferences(this))

        viewModel = ViewModelProvider(
            this,
            object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return PhotoViewModel(repo) as T
                }
            }
        )[PhotoViewModel::class.java]

        albumAdapter = AlbumAdapter(::openAlbum)
        binding.recycler.layoutManager = LinearLayoutManager(this)
        binding.recycler.adapter = albumAdapter

        binding.btnLoad.setOnClickListener {
            pickImages.launch(
                PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
            )
        }

        binding.btnLoadAll.setOnClickListener {
            requestAccessAndLoadAllPhotos()
        }

        binding.btnSync.setOnClickListener {
            viewModel.sync(selectedUris, this)
        }

        binding.btnClearMarkers.setOnClickListener {
            viewModel.resetUploadMarkers()
        }

        binding.btnAddTag.setOnClickListener {
            viewModel.addTag(binding.tagInput.text?.toString().orEmpty())
            binding.tagInput.text?.clear()
        }

        binding.search.doAfterTextChanged { text ->
            viewModel.search(text?.toString().orEmpty())
        }

        viewModel.photos.observe(this) { photos ->
            renderAlbums(photos)
        }

        viewModel.tags.observe(this) { tags ->
            renderTags(tags)
            updateSyncButtonState()
        }

        viewModel.message.observe(this) { message ->
            if (!message.isNullOrBlank()) {
                Toast.makeText(this, message, Toast.LENGTH_LONG).show()
                viewModel.consumeMessage()
            }
        }

        viewModel.syncCompleted.observe(this) { completed ->
            if (completed) {
                selectedUris = emptyList()
                updateSelectedSummary()
                updateSyncButtonState()
                viewModel.consumeSyncCompleted()
            }
        }

        viewModel.isSyncing.observe(this) {
            updateSyncButtonState()
            updateProgressUi()
        }

        updateSelectedSummary()
        updateProgressUi()
        updateSyncButtonState()
        viewModel.loadInitialState()
    }

    private fun requestAccessAndLoadAllPhotos() {
        val permission = mediaReadPermission()
        if (permission == null || hasPermission(permission)) {
            loadAllDevicePhotos()
        } else {
            requestImagesPermission.launch(permission)
        }
    }

    private fun loadAllDevicePhotos() {
        lifecycleScope.launch {
            binding.btnLoadAll.isEnabled = false

            val uris = withContext(Dispatchers.IO) {
                val imageUris = mutableListOf<Uri>()
                val projection = arrayOf(MediaStore.Images.Media._ID)
                val sortOrder = "${MediaStore.Images.Media.DATE_ADDED} DESC"

                contentResolver.query(
                    MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                    projection,
                    null,
                    null,
                    sortOrder
                )?.use { cursor ->
                    val idColumn = cursor.getColumnIndexOrThrow(MediaStore.Images.Media._ID)
                    while (cursor.moveToNext()) {
                        val id = cursor.getLong(idColumn)
                        imageUris += Uri.withAppendedPath(
                            MediaStore.Images.Media.EXTERNAL_CONTENT_URI,
                            id.toString()
                        )
                    }
                }

                imageUris
            }

            binding.btnLoadAll.isEnabled = true

            if (uris.isEmpty()) {
                showToast(R.string.no_photos_found_message)
            } else {
                selectedUris = uris.distinctBy { it.toString() }
                updateSyncButtonState()
                updateSelectedSummary()
                showToast(getString(R.string.all_photos_selected_message, selectedUris.size))
            }
        }
    }

    private fun renderTags(tags: List<String>) {
        binding.tagChipGroup.removeAllViews()

        tags.forEach { tag ->
            val chip = Chip(this).apply {
                text = tag
                isCloseIconVisible = true
                setOnCloseIconClickListener { viewModel.removeTag(tag) }
            }
            binding.tagChipGroup.addView(chip)
        }
    }

    private fun renderAlbums(photos: List<PhotoEntity>) {
        val albums = GroupingUtils.groupByAlbums(photos)
            .filterKeys { it.isNotBlank() }
            .map { (albumName, groupedPhotos) ->
                AlbumAdapter.AlbumItem(
                    name = albumName,
                    coverUri = groupedPhotos.firstOrNull()?.uri,
                    photoCount = groupedPhotos.size
                )
            }
            .sortedBy { it.name.lowercase() }

        albumAdapter.submitList(albums)
        binding.emptyState.visibility = if (albums.isEmpty()) View.VISIBLE else View.GONE
    }

    private fun updateSelectedSummary() {
        binding.selectedSummary.text = getString(R.string.selected_photos_summary, selectedUris.size)
    }

    private fun updateSyncButtonState() {
        val isSyncing = viewModel.isSyncing.value == true
        binding.btnLoad.isEnabled = !isSyncing
        binding.btnLoadAll.isEnabled = !isSyncing
        binding.btnAddTag.isEnabled = !isSyncing
        binding.btnClearMarkers.isEnabled = !isSyncing
        binding.btnSync.isEnabled = !isSyncing
        binding.btnSync.text = when {
            isSyncing -> getString(R.string.sync_button_loading)
            selectedUris.isEmpty() -> getString(R.string.sync_button_refresh)
            else -> getString(R.string.sync_button_with_count, selectedUris.size)
        }
    }

    private fun updateProgressUi() {
        val visible = viewModel.isSyncing.value == true
        binding.progressBar.visibility = if (visible) View.VISIBLE else View.GONE
        binding.progressText.visibility = if (visible) View.VISIBLE else View.GONE
        binding.progressText.text = getString(R.string.sync_in_progress_message)
    }

    private fun openAlbum(album: AlbumAdapter.AlbumItem) {
        val intent = Intent(this, AlbumActivity::class.java)
            .putExtra("album_name", album.name)
        startActivity(intent)
    }

    private fun mediaReadPermission(): String? {
        return when {
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU -> Manifest.permission.READ_MEDIA_IMAGES
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.M -> Manifest.permission.READ_EXTERNAL_STORAGE
            else -> null
        }
    }

    private fun hasPermission(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(this, permission) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun showToast(messageRes: Int) {
        Toast.makeText(this, messageRes, Toast.LENGTH_LONG).show()
    }

    private fun showToast(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
}

