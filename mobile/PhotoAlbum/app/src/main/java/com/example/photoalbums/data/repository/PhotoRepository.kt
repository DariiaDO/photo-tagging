package com.example.photoalbums.data.repository

import android.content.Context
import android.net.Uri
import com.example.photoalbums.data.local.PhotoDao
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.data.local.UserPreferences
import com.example.photoalbums.data.remote.ServerApi
import com.example.photoalbums.data.remote.SyncResponse
import com.example.photoalbums.utils.createImageMultipart
import com.example.photoalbums.utils.createTextPart
import com.google.gson.Gson
import java.io.IOException

class PhotoRepository(
    private val dao: PhotoDao,
    private val api: ServerApi,
    private val userPreferences: UserPreferences
) {

    private val gson = Gson()

    data class SyncResult(
        val uploadedCount: Int,
        val reusedCount: Int,
        val totalCount: Int,
        val syncedSelectionCount: Int
    )

    suspend fun syncPhotos(uris: List<Uri>, context: Context): SyncResult {
        val uniqueUris = uris.distinctBy { it.toString() }
        val uploadedUris = dao.getUploadedUris().toHashSet()
        val pendingUris = uniqueUris.filterNot { uploadedUris.contains(it.toString()) }

        val parts = mutableListOf(
            createTextPart("device_id", userPreferences.getDeviceId()),
            createTextPart("tags_json", gson.toJson(userPreferences.getTags()))
        )

        pendingUris.forEach { uri ->
            parts += createImageMultipart(context, uri)
            parts += createTextPart("client_photo_ids", uri.toString())
        }

        val response = api.syncPhotos(parts)
        if (!response.isSuccessful) {
            throw IOException("Server error: ${response.code()} ${response.message()}")
        }

        val body = response.body() ?: throw IOException("Empty server response")
        persistSnapshot(body)

        return SyncResult(
            uploadedCount = body.stats.uploaded_count,
            reusedCount = body.stats.reused_count,
            totalCount = body.stats.total_count,
            syncedSelectionCount = pendingUris.size
        )
    }

    suspend fun getAll() = dao.getAll()

    suspend fun search(query: String) = dao.search(query)

    suspend fun clearUploadMarkers() {
        dao.resetUploadMarkers()
    }

    fun getTags(): List<String> = userPreferences.getTags()

    fun saveTags(tags: List<String>) {
        userPreferences.setTags(tags)
    }

    private suspend fun persistSnapshot(body: SyncResponse) {
        val photos = body.photos.map { remotePhoto ->
            PhotoEntity(
                uri = remotePhoto.client_photo_id,
                serverId = remotePhoto.id,
                description = remotePhoto.description,
                tags = remotePhoto.tags,
                albumNames = remotePhoto.album_names,
                isUploaded = true,
                category = remotePhoto.category,
                imageUrl = remotePhoto.image_url,
                faceCount = remotePhoto.face_count
            )
        }

        dao.insertAll(photos)
    }
}

