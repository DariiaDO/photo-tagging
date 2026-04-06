package com.example.photoalbums.ui.activity

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.recyclerview.widget.GridLayoutManager
import com.example.photoalbums.data.local.AppDatabase
import com.example.photoalbums.data.remote.ClientApi
import com.example.photoalbums.data.repository.PhotoRepository
import com.example.photoalbums.databinding.ActivityAlbumBinding
import com.example.photoalbums.ui.adapter.PhotoAdapter
import com.example.photoalbums.viewmodel.PhotoViewModel

class AlbumActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAlbumBinding
    private lateinit var adapter: PhotoAdapter
    private lateinit var viewModel: PhotoViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAlbumBinding.inflate(layoutInflater)
        setContentView(binding.root)

        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)

        val albumName = intent.getStringExtra("album_name") ?: return
        title = albumName

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

        adapter = PhotoAdapter()
        binding.recyclerView.layoutManager = GridLayoutManager(this, 3)
        binding.recyclerView.adapter = adapter

        viewModel.photos.observe(this) { photos ->
            adapter.submitList(photos.filter { photo -> photo.tags.contains(albumName) })
        }

        viewModel.loadPhotos()
    }

    override fun onSupportNavigateUp(): Boolean {
        finish()
        return true
    }
}
