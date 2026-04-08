package com.example.photoalbums.data.remote

import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

data class SyncPhotoResponse(
    val id: Int,
    val client_photo_id: String,
    val description: String,
    val tags: List<String>,
    val category: String = "unknown",
    val image_url: String? = null,
    val face_count: Int = 0,
    val album_names: List<String> = emptyList()
)

data class AlbumResponse(
    val name: String,
    val photo_ids: List<Int>,
    val client_photo_ids: List<String>,
    val cover_photo_id: Int?,
    val cover_client_photo_id: String?,
    val photo_count: Int
)

data class SyncStats(
    val uploaded_count: Int,
    val reused_count: Int,
    val total_count: Int
)

data class SyncResponse(
    val requested_tags: List<String>,
    val photos: List<SyncPhotoResponse>,
    val albums: List<AlbumResponse>,
    val stats: SyncStats
)

interface ServerApi {

    @Multipart
    @POST("api/upload/")
    suspend fun syncPhotos(
        @Part parts: List<MultipartBody.Part>
    ): Response<SyncResponse>
}

