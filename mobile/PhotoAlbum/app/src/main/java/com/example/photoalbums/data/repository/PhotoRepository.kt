package com.example.photoalbums.data.repository

import android.content.Context
import android.net.Uri
import com.example.photoalbums.data.local.PhotoDao
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.data.local.UserPreferences
import com.example.photoalbums.data.remote.ApiErrorResponse
import com.example.photoalbums.data.remote.ServerApi
import com.example.photoalbums.data.remote.SyncResponse
import com.example.photoalbums.utils.createImageMultipart
import com.example.photoalbums.utils.createTextPart
import com.example.photoalbums.utils.LocalTextTranslator
import com.google.gson.Gson
import java.io.IOException

class PhotoRepository(
    private val dao: PhotoDao,
    private val api: ServerApi,
    private val userPreferences: UserPreferences
) {

    data class AlbumDescriptor(
        val key: String,
        val title: String,
        val photoCount: Int,
        val coverUri: String?,
        val type: String,
        val faceNumber: Int? = null
    )

    data class SyncResult(
        val uploadedCount: Int,
        val reusedCount: Int,
        val totalCount: Int,
        val syncedSelectionCount: Int
    )

    private val gson = Gson()

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
            val detail = parseApiError(response.errorBody()?.string())
                ?: response.message()
                ?: "Unknown server error"
            throw IOException("Server error: ${response.code()} $detail")
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

    fun getFaceLabels(): Map<Int, String> = userPreferences.getFaceLabels()

    fun saveFaceLabel(faceNumber: Int, label: String?) {
        userPreferences.setFaceLabel(faceNumber, label)
    }

    fun buildAlbums(photos: List<PhotoEntity>): List<AlbumDescriptor> {
        val facePhotos = mutableListOf<PhotoEntity>()

        photos.forEach { photo ->
            var hasFace = false
            photo.albumKeys.distinct().forEach { key ->
                when {
                    parseFaceNumber(key) != null -> hasFace = true
                }
            }
            if (hasFace) {
                facePhotos += photo
            }
        }

        val tagAlbums = buildTagAlbumDescriptors(photos, getTags())

        val faceAlbum = if (facePhotos.isNotEmpty()) {
            listOf(
                AlbumDescriptor(
                    key = FACES_INDEX_KEY,
                    title = FACES_INDEX_TITLE,
                    photoCount = facePhotos.size,
                    coverUri = facePhotos.firstOrNull()?.imageUrl ?: facePhotos.firstOrNull()?.uri,
                    type = TYPE_FACES_INDEX
                )
            )
        } else {
            emptyList()
        }

        return (tagAlbums + faceAlbum)
            .sortedWith(compareBy<AlbumDescriptor>({ if (it.type == TYPE_TAG) 0 else 1 }, { it.title.lowercase() }))
    }

    fun buildFaceAlbums(photos: List<PhotoEntity>): List<AlbumDescriptor> {
        val labels = getFaceLabels()
        val faceAlbumsByNumber = linkedMapOf<Int, MutableList<PhotoEntity>>()

        photos.forEach { photo ->
            photo.faceNumbers.distinct().forEach { faceNumber ->
                faceAlbumsByNumber.getOrPut(faceNumber) { mutableListOf() }.add(photo)
            }
        }

        return faceAlbumsByNumber.map { (faceNumber, albumPhotos) ->
            AlbumDescriptor(
                key = "$FACE_PREFIX$faceNumber",
                title = labels[faceNumber]?.takeIf { it.isNotBlank() } ?: "Лицо #$faceNumber",
                photoCount = albumPhotos.size,
                coverUri = albumPhotos.firstOrNull()?.imageUrl ?: albumPhotos.firstOrNull()?.uri,
                type = TYPE_FACE,
                faceNumber = faceNumber
            )
        }.sortedBy { it.title.lowercase() }
    }

    fun displayAlbumTitle(albumKey: String, labels: Map<Int, String> = getFaceLabels()): String {
        val faceNumber = parseFaceNumber(albumKey)
        return when {
            faceNumber != null -> labels[faceNumber]?.takeIf { it.isNotBlank() } ?: "Лицо #$faceNumber"
            albumKey == FACES_INDEX_KEY -> FACES_INDEX_TITLE
            albumKey.startsWith(TAG_PREFIX) -> albumKey.substringAfter(TAG_PREFIX)
            else -> albumKey
        }
    }

    fun parseFaceNumber(albumKey: String): Int? {
        return albumKey.substringAfter(FACE_PREFIX, "")
            .takeIf { it.isNotBlank() && albumKey.startsWith(FACE_PREFIX) }
            ?.toIntOrNull()
    }

    private suspend fun persistSnapshot(body: SyncResponse) {
        val requestedTags = userPreferences.getTags()
        val photos = body.photos.map { remotePhoto ->
            val translatedTags = LocalTextTranslator.translateTags(
                remotePhoto.tags.orEmpty().filter { it.isNotBlank() }
            )
            val translatedDescription = LocalTextTranslator.translateDescription(
                remotePhoto.description.orEmpty()
            )
            val translatedCategory = LocalTextTranslator.translateTag(
                remotePhoto.category?.takeIf { it.isNotBlank() } ?: "unknown"
            )
            val translatedAlbumKeys = matchRequestedAlbumKeys(
                requestedTags = requestedTags,
                translatedTags = translatedTags,
                translatedCategory = translatedCategory,
                translatedDescription = translatedDescription
            ).ifEmpty { listOf("$TAG_PREFIX$OTHER_ALBUM_TITLE") }
            val faceAlbumKeys = remotePhoto.face_numbers.orEmpty().map { "$FACE_PREFIX$it" }
            val albumKeys = (translatedAlbumKeys + faceAlbumKeys).distinct()

            PhotoEntity(
                uri = remotePhoto.client_photo_id,
                serverId = remotePhoto.id,
                description = translatedDescription,
                tags = translatedTags,
                albumNames = albumKeys,
                albumKeys = albumKeys,
                faceNumbers = remotePhoto.face_numbers.orEmpty(),
                isUploaded = true,
                category = translatedCategory,
                imageUrl = remotePhoto.image_url,
                faceCount = remotePhoto.face_count
            )
        }

        dao.insertAll(photos)
    }

    private fun parseApiError(rawBody: String?): String? {
        val body = rawBody?.trim().orEmpty()
        if (body.isEmpty()) return null
        return runCatching {
            gson.fromJson(body, ApiErrorResponse::class.java)?.message?.takeIf { it.isNotBlank() }
        }.getOrNull() ?: body
    }

    companion object {
        private const val TAG_PREFIX = "tag:"
        private const val FACE_PREFIX = "face:"
        private const val OTHER_ALBUM_TITLE = "Другое"
        const val FACES_INDEX_KEY = "faces:index"
        const val FACES_INDEX_TITLE = "Лица"
        const val TYPE_TAG = "tag"
        const val TYPE_FACE = "face"
        const val TYPE_FACES_INDEX = "faces_index"

        private fun matchRequestedAlbumKeys(
            requestedTags: List<String>,
            translatedTags: List<String>,
            translatedCategory: String,
            translatedDescription: String
        ): List<String> {
            val searchable = (translatedTags + translatedCategory + translatedDescription)
                .map { it.trim() }
                .filter { it.isNotEmpty() }

            return requestedTags
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .distinct()
                .filter { requestedTag ->
                    searchable.any { value ->
                        LocalTextTranslator.matchesTagQuery(value, requestedTag)
                    }
                }
                .map(LocalTextTranslator::albumKeyForTranslatedTag)
        }

        internal fun buildTagAlbumDescriptors(
            photos: List<PhotoEntity>,
            requestedTags: List<String>
        ): List<AlbumDescriptor> {
            val tagAlbumsByKey = linkedMapOf<String, MutableList<PhotoEntity>>()
            val requestedKeys = requestedTags
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .distinct()
                .map { "$TAG_PREFIX$it" }
                .toSet()

            requestedKeys.forEach { key ->
                tagAlbumsByKey.putIfAbsent(key, mutableListOf())
            }

            photos.forEach { photo ->
                val matchedKeys = requestedKeys.filter { key ->
                    val requestedTag = key.substringAfter(TAG_PREFIX)
                    photoMatchesRequestedTag(photo, requestedTag)
                }
                val keys = matchedKeys.ifEmpty { listOf("$TAG_PREFIX$OTHER_ALBUM_TITLE") }
                keys.forEach { key ->
                    tagAlbumsByKey.getOrPut(key) { mutableListOf() }.add(photo)
                }
            }

            return tagAlbumsByKey
                .filterNot { (key, albumPhotos) -> key == "$TAG_PREFIX$OTHER_ALBUM_TITLE" && albumPhotos.isEmpty() }
                .map { (key, albumPhotos) ->
                    AlbumDescriptor(
                        key = key,
                        title = key.substringAfter(TAG_PREFIX),
                        photoCount = albumPhotos.size,
                        coverUri = albumPhotos.firstOrNull()?.imageUrl ?: albumPhotos.firstOrNull()?.uri,
                        type = TYPE_TAG
                    )
                }
        }

        private fun photoMatchesRequestedTag(photo: PhotoEntity, requestedTag: String): Boolean {
            val searchable = photo.tags + photo.category + photo.description
            return searchable.any { value ->
                LocalTextTranslator.matchesTagQuery(value, requestedTag)
            }
        }
    }
}
