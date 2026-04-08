package com.example.photoalbums.viewmodel

import android.content.Context
import android.net.Uri
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.photoalbums.data.local.PhotoEntity
import com.example.photoalbums.data.repository.PhotoRepository
import kotlinx.coroutines.launch
import java.io.IOException

class PhotoViewModel(
    private val repository: PhotoRepository
) : ViewModel() {

    data class SyncProgress(
        val selected: Int,
        val pending: Int
    )

    private val _photos = MutableLiveData<List<PhotoEntity>>()
    val photos: LiveData<List<PhotoEntity>> = _photos

    private val _tags = MutableLiveData<List<String>>()
    val tags: LiveData<List<String>> = _tags

    private val _message = MutableLiveData<String?>()
    val message: LiveData<String?> = _message

    private val _isSyncing = MutableLiveData(false)
    val isSyncing: LiveData<Boolean> = _isSyncing

    private val _syncCompleted = MutableLiveData(false)
    val syncCompleted: LiveData<Boolean> = _syncCompleted

    private val _syncProgress = MutableLiveData(SyncProgress(0, 0))
    val syncProgress: LiveData<SyncProgress> = _syncProgress

    fun loadInitialState() {
        _tags.value = repository.getTags()
        loadPhotos()
    }

    fun loadPhotos() {
        viewModelScope.launch {
            _photos.value = repository.getAll()
        }
    }

    fun search(query: String) {
        viewModelScope.launch {
            _photos.value = repository.search(query)
        }
    }

    fun sync(uris: List<Uri>, context: Context) {
        if (_isSyncing.value == true) return

        viewModelScope.launch {
            _isSyncing.value = true
            _syncCompleted.value = false
            _syncProgress.value = SyncProgress(selected = uris.distinctBy { it.toString() }.size, pending = 0)

            runCatching {
                val result = repository.syncPhotos(uris, context)
                _syncProgress.value = SyncProgress(
                    selected = uris.distinctBy { it.toString() }.size,
                    pending = result.syncedSelectionCount
                )
                repository.getAll() to result
            }.onSuccess { (photos, result) ->
                _photos.value = photos
                _syncCompleted.value = true
                _message.value = buildSuccessMessage(result)
            }.onFailure { throwable ->
                _message.value = throwable.toUserMessage()
            }

            _isSyncing.value = false
        }
    }

    fun addTag(rawTag: String) {
        val tag = rawTag.trim()
        if (tag.isEmpty()) return

        val current = _tags.value.orEmpty()
        if (current.any { it.equals(tag, ignoreCase = true) }) {
            _message.value = "Тег уже существует"
            return
        }

        val updated = current + tag
        repository.saveTags(updated)
        _tags.value = updated
    }

    fun removeTag(tag: String) {
        val updated = _tags.value.orEmpty().filterNot { it == tag }
        repository.saveTags(updated)
        _tags.value = updated
    }

    fun resetUploadMarkers() {
        viewModelScope.launch {
            repository.clearUploadMarkers()
            _photos.value = repository.getAll()
            _message.value = "Метки отправки очищены"
        }
    }

    fun consumeMessage() {
        _message.value = null
    }

    fun consumeSyncCompleted() {
        _syncCompleted.value = false
    }

    private fun buildSuccessMessage(result: PhotoRepository.SyncResult): String {
        return "Синхронизация завершена. Новых: ${result.uploadedCount}, пропущено: ${result.reusedCount}, всего на сервере: ${result.totalCount}"
    }

    private fun Throwable.toUserMessage(): String {
        return when (this) {
            is IOException -> "Не удалось синхронизировать фото. Проверьте адрес сервера и доступность API."
            else -> "Не удалось обработать фото: ${message ?: "неизвестная ошибка"}"
        }
    }
}

