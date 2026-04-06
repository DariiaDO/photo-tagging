package com.example.photoalbums.data.repository

import android.content.Context
import android.net.Uri
import com.example.photoalbums.data.local.PhotoDao
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.data.remote.ServerApi
import com.example.photoalbums.utils.createMultipart
import java.io.IOException

class PhotoRepository(
    private val dao: PhotoDao,
    private val api: ServerApi
) {

    suspend fun analyzeAndSave(uri: Uri, context: Context) {
        val part = createMultipart(context, uri)
        val response = api.uploadImage(part)

        if (!response.isSuccessful) {
            throw IOException("Server error: ${response.code()} ${response.message()}")
        }

        val result = response.body()
            ?: throw IOException("Empty server response")

        dao.insert(
            PhotoEntity(
                uri = uri.toString(),
                description = result.description,
                tags = result.tags
            )
        )
    }

    suspend fun getAll() = dao.getAll()

    suspend fun search(query: String) = dao.search(query)
}
