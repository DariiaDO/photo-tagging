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
import com.example.photoalbums.data.remote.ClientApi
import com.example.photoalbums.data.repository.PhotoRepository
import com.example.photoalbums.databinding.ActivityMainBinding
import com.example.photoalbums.ui.adapter.AlbumAdapter
import com.example.photoalbums.utils.GroupingUtils
import com.example.photoalbums.viewmodel.PhotoViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var viewModel: PhotoViewModel
    private lateinit var albumAdapter: AlbumAdapter

    private var selectedUris: List<Uri> = emptyList()

    private val pickImages =
        registerForActivityResult(ActivityResultContracts.PickMultipleVisualMedia(20)) { uris ->
            selectedUris = uris
            updateAnalyzeButtonState()
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
        val repo = PhotoRepository(db.photoDao(), ClientApi.api)

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

        binding.btnAnalyze.setOnClickListener {
            viewModel.analyze(selectedUris, this)
        }

        binding.search.doAfterTextChanged { text ->
            viewModel.search(text?.toString().orEmpty())
        }

        viewModel.photos.observe(this) { photos ->
            renderAlbums(photos)
        }

        viewModel.message.observe(this) { message ->
            if (!message.isNullOrBlank()) {
                Toast.makeText(this, message, Toast.LENGTH_LONG).show()
                viewModel.consumeMessage()
            }
        }

        viewModel.analysisCompleted.observe(this) { completed ->
            if (completed) {
                selectedUris = emptyList()
                updateAnalyzeButtonState()
                viewModel.consumeAnalysisCompleted()
            }
        }

        viewModel.isAnalyzing.observe(this) {
            updateAnalyzeButtonState()
        }

        viewModel.analysisProgress.observe(this) { progress ->
            updateProgressUi(progress)
            updateAnalyzeButtonState()
        }

        updateProgressUi(viewModel.analysisProgress.value ?: PhotoViewModel.AnalysisProgress(0, 0))
        updateAnalyzeButtonState()
        viewModel.loadPhotos()
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
                selectedUris = uris
                updateAnalyzeButtonState()
                showToast(getString(R.string.all_photos_selected_message, uris.size))
            }
        }
    }

    private fun renderAlbums(photos: List<PhotoEntity>) {
        val albums = GroupingUtils.groupByTags(photos)
            .filterKeys { it.isNotBlank() }
            .map { (tag, groupedPhotos) ->
                AlbumAdapter.AlbumItem(
                    name = tag,
                    coverUri = groupedPhotos.firstOrNull()?.uri,
                    photoCount = groupedPhotos.size
                )
            }
            .sortedBy { it.name.lowercase() }

        albumAdapter.submitList(albums)
    }

    private fun updateAnalyzeButtonState() {
        val isAnalyzing = viewModel.isAnalyzing.value == true
        val progress = viewModel.analysisProgress.value ?: PhotoViewModel.AnalysisProgress(0, 0)
        binding.btnLoad.isEnabled = !isAnalyzing
        binding.btnLoadAll.isEnabled = !isAnalyzing
        binding.btnAnalyze.isEnabled = selectedUris.isNotEmpty() && !isAnalyzing
        binding.btnAnalyze.text = when {
            isAnalyzing -> getString(
                R.string.analyze_button_loading_with_progress,
                progress.processed,
                progress.total
            )
            selectedUris.isEmpty() -> getString(R.string.analyze_button_empty)
            else -> getString(R.string.analyze_button_with_count, selectedUris.size)
        }
    }

    private fun updateProgressUi(progress: PhotoViewModel.AnalysisProgress) {
        val visible = progress.total > 0 && viewModel.isAnalyzing.value == true
        binding.progressBar.visibility = if (visible) View.VISIBLE else View.GONE
        binding.progressText.visibility = if (visible) View.VISIBLE else View.GONE

        if (visible) {
            binding.progressBar.max = progress.total
            binding.progressBar.progress = progress.processed
            binding.progressText.text = getString(
                R.string.analysis_progress_text,
                progress.processed,
                progress.total
            )
        }
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
