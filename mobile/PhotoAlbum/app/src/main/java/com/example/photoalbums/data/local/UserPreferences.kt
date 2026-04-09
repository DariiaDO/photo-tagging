package com.example.photoalbums.data.local

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.util.UUID

class UserPreferences(context: Context) {

    private val prefs = context.getSharedPreferences("photo_albums_prefs", Context.MODE_PRIVATE)
    private val gson = Gson()

    fun getDeviceId(): String {
        val existing = prefs.getString(KEY_DEVICE_ID, null)
        if (!existing.isNullOrBlank()) return existing

        val generated = UUID.randomUUID().toString()
        prefs.edit().putString(KEY_DEVICE_ID, generated).apply()
        return generated
    }

    fun getTags(): List<String> {
        val raw = prefs.getString(KEY_TAGS, null)
        if (raw == null) {
            setTags(DEFAULT_TAGS)
            return DEFAULT_TAGS
        }

        val type = object : TypeToken<List<String>>() {}.type
        return gson.fromJson<List<String>>(raw, type)
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
    }

    fun setTags(tags: List<String>) {
        val normalized = tags
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
        prefs.edit().putString(KEY_TAGS, gson.toJson(normalized)).apply()
    }

    fun getFaceLabels(): Map<Int, String> {
        val raw = prefs.getString(KEY_FACE_LABELS, null) ?: return emptyMap()
        val type = object : TypeToken<Map<String, String>>() {}.type
        val stored = gson.fromJson<Map<String, String>>(raw, type) ?: return emptyMap()
        return stored.mapNotNull { (key, value) ->
            key.toIntOrNull()?.let { number -> number to value.trim() }
        }.filter { it.second.isNotEmpty() }.toMap()
    }

    fun setFaceLabel(faceNumber: Int, label: String?) {
        val current = getFaceLabels().toMutableMap()
        val normalized = label?.trim().orEmpty()
        if (normalized.isEmpty()) {
            current.remove(faceNumber)
        } else {
            current[faceNumber] = normalized
        }
        val serialized = current.mapKeys { it.key.toString() }
        prefs.edit().putString(KEY_FACE_LABELS, gson.toJson(serialized)).apply()
    }

    companion object {
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_TAGS = "tags"
        private const val KEY_FACE_LABELS = "face_labels"

        val DEFAULT_TAGS = listOf(
            "Люди",
            "Природа",
            "Животные",
            "Еда",
            "Путешествия"
        )
    }
}
