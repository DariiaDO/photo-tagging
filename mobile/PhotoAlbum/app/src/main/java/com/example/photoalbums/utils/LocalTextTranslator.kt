package com.example.photoalbums.utils

import com.google.android.gms.tasks.Task
import com.google.mlkit.common.model.DownloadConditions
import com.google.mlkit.nl.translate.TranslateLanguage
import com.google.mlkit.nl.translate.Translation
import com.google.mlkit.nl.translate.TranslatorOptions
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.suspendCancellableCoroutine

object LocalTextTranslator {

    private val modelMutex = Mutex()
    private var modelReady = false

    private val translator by lazy {
        val options = TranslatorOptions.Builder()
            .setSourceLanguage(TranslateLanguage.ENGLISH)
            .setTargetLanguage(TranslateLanguage.RUSSIAN)
            .build()
        Translation.getClient(options)
    }

    suspend fun translateDescription(text: String): String {
        val normalized = text.trim()
        if (normalized.isBlank() || normalized.hasCyrillic()) {
            return text
        }

        return translateWithModel(normalized) ?: text
    }

    suspend fun translateTags(tags: List<String>): List<String> {
        val translated = mutableListOf<String>()
        tags.forEach { tag ->
            if (!shouldKeepSourceTag(tag)) {
                return@forEach
            }
            val value = translateTag(tag)
            if (
                shouldKeepTranslatedTag(value) &&
                translated.none { it.equals(value, ignoreCase = true) }
            ) {
                translated += value
            }
        }
        return translated
    }

    suspend fun translateTag(tag: String): String {
        val normalized = tag.trim()
        if (normalized.isBlank() || normalized.hasCyrillic()) {
            return normalized
        }

        return TAG_TRANSLATIONS[normalized.lowercase()]
            ?: translateWithModel(normalized)?.replaceFirstChar { it.uppercase() }
            ?: "Другое"
    }

    fun albumKeyForTranslatedTag(tag: String): String = "$TAG_PREFIX${tag.trim()}"

    fun matchesTagQuery(value: String, query: String): Boolean {
        val normalizedValue = normalizeForMatch(value)
        val normalizedQuery = normalizeForMatch(query)
        return normalizedQuery.isNotEmpty() &&
            (normalizedValue == normalizedQuery || normalizedValue.contains(normalizedQuery))
    }

    private suspend fun ensureModelReady() {
        if (modelReady) return

        modelMutex.withLock {
            if (modelReady) return
            val conditions = DownloadConditions.Builder().build()
            translator.downloadModelIfNeeded(conditions).awaitTask()
            modelReady = true
        }
    }

    private suspend fun translateWithModel(text: String): String? =
        runCatching {
            ensureModelReady()
            translator.translate(text).awaitTask().trim().takeIf { it.isNotBlank() }
        }.getOrNull()

    private fun String.hasCyrillic(): Boolean = any { it in '\u0400'..'\u04FF' }

    private fun shouldKeepSourceTag(tag: String): Boolean {
        val normalized = tag.trim().lowercase()
        if (normalized.isBlank()) return false
        if (normalized.hasCyrillic()) return true
        if (normalized in TAG_TRANSLATIONS) return true
        if (normalized in ENGLISH_TAG_STOP_WORDS) return false
        if (normalized.endsWith("ing") || normalized.endsWith("ed") || normalized.endsWith("ly")) {
            return false
        }
        return normalized.length >= 3
    }

    private fun shouldKeepTranslatedTag(tag: String): Boolean {
        val normalized = tag.trim().lowercase()
        if (normalized.isBlank() || normalized == "другое") return false
        if (normalized in RUSSIAN_TAG_STOP_WORDS) return false
        if (
            normalized.endsWith("ть") ||
            normalized.endsWith("ться") ||
            normalized.endsWith("лся") ||
            normalized.endsWith("лась") ||
            normalized.endsWith("лись") ||
            normalized.endsWith("ет") ||
            normalized.endsWith("ют") ||
            normalized.endsWith("ит")
        ) {
            return false
        }
        return true
    }

    private fun normalizeForMatch(value: String): String =
        value.trim()
            .lowercase()
            .replace('ё', 'е')
            .replace('-', ' ')
            .filter { it.isLetterOrDigit() || it.isWhitespace() }
            .replace(Regex("\\s+"), " ")
            .trim()

    private suspend fun <T> Task<T>.awaitTask(): T =
        suspendCancellableCoroutine { continuation ->
            addOnSuccessListener { result ->
                continuation.resume(result)
            }
            addOnFailureListener { exception ->
                continuation.resumeWithException(exception)
            }
        }

    private const val TAG_PREFIX = "tag:"

    private val ENGLISH_TAG_STOP_WORDS = setOf(
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "with",
        "from", "near", "into", "over", "under", "very", "clearly"
    )

    private val RUSSIAN_TAG_STOP_WORDS = setOf(
        "и", "или", "в", "на", "под", "над", "около", "рядом", "очень",
        "явно", "сильно", "быстро", "медленно"
    )

    private val TAG_TRANSLATIONS = mapOf(
        "people" to "Люди",
        "person" to "Люди",
        "portrait" to "Люди",
        "face" to "Люди",
        "man" to "Люди",
        "woman" to "Люди",
        "child" to "Люди",
        "animals" to "Животные",
        "animal" to "Животные",
        "dog" to "Животные",
        "cat" to "Животные",
        "bird" to "Животные",
        "horse" to "Животные",
        "pet" to "Животные",
        "food" to "Еда",
        "meal" to "Еда",
        "dish" to "Еда",
        "drink" to "Еда",
        "fruit" to "Еда",
        "restaurant" to "Еда",
        "dessert" to "Еда",
        "travel" to "Путешествия",
        "trip" to "Путешествия",
        "vacation" to "Путешествия",
        "tourism" to "Путешествия",
        "journey" to "Путешествия",
        "landmark" to "Путешествия",
        "transport" to "Транспорт",
        "car" to "Транспорт",
        "vehicle" to "Транспорт",
        "train" to "Транспорт",
        "bus" to "Транспорт",
        "bike" to "Транспорт",
        "bicycle" to "Транспорт",
        "nature" to "Природа",
        "outdoor" to "Природа",
        "landscape" to "Природа",
        "forest" to "Природа",
        "tree" to "Природа",
        "sky" to "Природа",
        "sea" to "Природа",
        "beach" to "Природа",
        "mountain" to "Природа",
        "interior" to "Интерьер",
        "room" to "Интерьер",
        "office" to "Интерьер",
        "kitchen" to "Интерьер",
        "bedroom" to "Интерьер",
        "city" to "Город",
        "street" to "Город",
        "building" to "Город",
        "architecture" to "Архитектура",
        "clothing" to "Одежда",
        "fashion" to "Одежда",
        "sports" to "Спорт",
        "sport" to "Спорт",
        "technology" to "Техника",
        "device" to "Техника",
        "computer" to "Техника",
        "phone" to "Техника",
        "documents" to "Документы",
        "document" to "Документы",
        "text" to "Документы",
        "art" to "Искусство",
        "painting" to "Искусство",
        "night" to "Ночь",
        "unknown" to "Другое"
    )
}
