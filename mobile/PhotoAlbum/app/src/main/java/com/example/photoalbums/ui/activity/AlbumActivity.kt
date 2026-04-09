package com.example.photoalbums.ui.activity

import android.os.Bundle
import android.view.View
import android.widget.EditText
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.photoalbums.R
import com.example.photoalbums.data.local.AppDatabase
import com.example.photoalbums.data.local.UserPreferences
import com.example.photoalbums.data.remote.ClientApi
import com.example.photoalbums.data.repository.PhotoRepository
import com.example.photoalbums.databinding.ActivityAlbumBinding
import com.example.photoalbums.ui.adapter.AlbumAdapter
import com.example.photoalbums.ui.adapter.PhotoAdapter
import com.example.photoalbums.viewmodel.PhotoViewModel

class AlbumActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAlbumBinding
    private lateinit var photoAdapter: PhotoAdapter
    private lateinit var albumAdapter: AlbumAdapter
    private lateinit var viewModel: PhotoViewModel
    private lateinit var repo: PhotoRepository

    private lateinit var albumKey: String
    private var faceNumber: Int? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAlbumBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        albumKey = intent.getStringExtra("album_key") ?: return
        faceNumber = intent.getIntExtra("face_number", -1).takeIf { it > 0 }

        val db = AppDatabase.getInstance(this)
        repo = PhotoRepository(db.photoDao(), ClientApi.api, UserPreferences(this))

        viewModel = ViewModelProvider(
            this,
            object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return PhotoViewModel(repo) as T
                }
            }
        )[PhotoViewModel::class.java]

        photoAdapter = PhotoAdapter(::openPhoto)
        albumAdapter = AlbumAdapter(::openNestedAlbum)

        binding.recyclerView.layoutManager = GridLayoutManager(this, 2)
        binding.recyclerView.adapter = photoAdapter
        binding.albumRecyclerView.layoutManager = LinearLayoutManager(this)
        binding.albumRecyclerView.adapter = albumAdapter

        val isFacesIndex = albumKey == PhotoRepository.FACES_INDEX_KEY
        binding.albumRecyclerView.visibility = if (isFacesIndex) View.VISIBLE else View.GONE
        binding.recyclerView.visibility = if (isFacesIndex) View.GONE else View.VISIBLE
        binding.renameFaceButton.visibility = if (faceNumber != null) View.VISIBLE else View.GONE
        binding.faceHint.visibility = if (faceNumber != null) View.VISIBLE else View.GONE
        binding.renameFaceButton.setOnClickListener {
            showRenameDialog(faceNumber ?: return@setOnClickListener)
        }

        viewModel.photos.observe(this) { photos ->
            if (albumKey == PhotoRepository.FACES_INDEX_KEY) {
                val albums = repo.buildFaceAlbums(photos).map { descriptor ->
                    AlbumAdapter.AlbumItem(
                        key = descriptor.key,
                        name = descriptor.title,
                        coverUri = descriptor.coverUri,
                        photoCount = descriptor.photoCount,
                        type = descriptor.type,
                        faceNumber = descriptor.faceNumber
                    )
                }
                albumAdapter.submitList(albums)
            } else {
                photoAdapter.submitList(photos.filter { photo -> photo.albumKeys.contains(albumKey) })
            }
        }

        viewModel.faceLabels.observe(this) {
            val title = viewModel.displayAlbumTitle(albumKey)
            this.title = title
            binding.toolbar.title = title
            binding.faceHint.text = faceNumber?.let { number ->
                getString(R.string.face_album_hint, number)
            }
            if (albumKey == PhotoRepository.FACES_INDEX_KEY) {
                viewModel.loadPhotos()
            }
        }

        viewModel.loadInitialState()
    }

    private fun openNestedAlbum(album: AlbumAdapter.AlbumItem) {
        startActivity(android.content.Intent(this, AlbumActivity::class.java).apply {
            putExtra("album_key", album.key)
            putExtra("album_name", album.name)
            putExtra("album_type", album.type)
            putExtra("face_number", album.faceNumber)
        })
    }

    private fun showRenameDialog(faceNumber: Int) {
        val input = EditText(this).apply {
            setText(viewModel.faceLabels.value?.get(faceNumber).orEmpty())
            hint = getString(R.string.face_name_hint)
        }

        AlertDialog.Builder(this)
            .setTitle(getString(R.string.rename_face_title, faceNumber))
            .setView(input)
            .setPositiveButton(R.string.save_face_name_button) { _, _ ->
                viewModel.renameFace(faceNumber, input.text?.toString().orEmpty())
            }
            .setNeutralButton(R.string.reset_face_name_button) { _, _ ->
                viewModel.resetFaceName(faceNumber)
            }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }

    private fun openPhoto(photo: com.example.photoalbums.data.local.PhotoEntity) {
        startActivity(PhotoViewerActivity.createIntent(this, photo.imageUrl, photo.uri))
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}
