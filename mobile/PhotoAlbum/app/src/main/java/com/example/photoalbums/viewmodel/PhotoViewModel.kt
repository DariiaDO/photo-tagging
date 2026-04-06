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

    data class AnalysisProgress(
        val processed: Int,
        val total: Int
    )

    private val _photos = MutableLiveData<List<PhotoEntity>>()
    val photos: LiveData<List<PhotoEntity>> = _photos

    private val _message = MutableLiveData<String?>()
    val message: LiveData<String?> = _message

    private val _isAnalyzing = MutableLiveData(false)
    val isAnalyzing: LiveData<Boolean> = _isAnalyzing

    private val _analysisCompleted = MutableLiveData(false)
    val analysisCompleted: LiveData<Boolean> = _analysisCompleted

    private val _analysisProgress = MutableLiveData(AnalysisProgress(0, 0))
    val analysisProgress: LiveData<AnalysisProgress> = _analysisProgress

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

    fun analyze(uris: List<Uri>, context: Context) {
        if (_isAnalyzing.value == true || uris.isEmpty()) return

        viewModelScope.launch {
            _isAnalyzing.value = true
            _analysisCompleted.value = false
            _analysisProgress.value = AnalysisProgress(0, uris.size)

            runCatching {
                val batchSize = 20
                var processed = 0

                uris.chunked(batchSize).forEach { batch ->
                    batch.forEach { uri ->
                        repository.analyzeAndSave(uri, context)
                        processed += 1
                        _analysisProgress.value = AnalysisProgress(processed, uris.size)
                    }
                }

                repository.getAll()
            }.onSuccess { photos ->
                _photos.value = photos
                _analysisCompleted.value = true
                _message.value = "Фото успешно обработаны"
            }.onFailure { throwable ->
                _message.value = throwable.toUserMessage()
            }

            _isAnalyzing.value = false
        }
    }

    fun consumeMessage() {
        _message.value = null
    }

    fun consumeAnalysisCompleted() {
        _analysisCompleted.value = false
        _analysisProgress.value = AnalysisProgress(0, 0)
    }

    private fun Throwable.toUserMessage(): String {
        return when (this) {
            is IOException -> "Не удалось отправить фото на сервер. Проверьте адрес и доступность API."
            else -> "Не удалось обработать фото: ${message ?: "неизвестная ошибка"}"
        }
    }
}
