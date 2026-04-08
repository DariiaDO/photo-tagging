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

    companion object {
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_TAGS = "tags"

        val DEFAULT_TAGS = listOf(
            "Люди",
            "Природа",
            "Животные",
            "Еда",
            "Путешествия"
        )
    }
}

