package com.example.photoalbums.data.local

import androidx.room.TypeConverter
import com.google.gson.Gson
import com.google.gson.JsonSyntaxException
import com.google.gson.reflect.TypeToken

class Converters {

    private val gson = Gson()

    @TypeConverter
    fun fromStringList(values: List<String>): String = gson.toJson(values)

    @TypeConverter
    fun toStringList(data: String?): List<String> {
        if (data.isNullOrBlank()) return emptyList()
        val type = object : TypeToken<List<String>>() {}.type
        return try {
            gson.fromJson<List<String>>(data, type)
                ?.map { it.trim() }
                ?.filter { it.isNotEmpty() }
                ?: emptyList()
        } catch (_: JsonSyntaxException) {
            data.split(",")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
        }
    }

    @TypeConverter
    fun fromIntList(values: List<Int>): String = gson.toJson(values)

    @TypeConverter
    fun toIntList(data: String?): List<Int> {
        if (data.isNullOrBlank()) return emptyList()
        val type = object : TypeToken<List<Int>>() {}.type
        return try {
            gson.fromJson<List<Int>>(data, type) ?: emptyList()
        } catch (_: JsonSyntaxException) {
            data.split(",")
                .mapNotNull { it.trim().toIntOrNull() }
        }
    }
}
