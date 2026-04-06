package com.example.photoalbums.data.local

import androidx.room.TypeConverter

class Converters {

    @TypeConverter
    fun fromTags(tags: List<String>): String =
        tags.joinToString(",")

    @TypeConverter
    fun toTags(data: String): List<String> =
        if (data.isEmpty()) emptyList() else data.split(",")
}
