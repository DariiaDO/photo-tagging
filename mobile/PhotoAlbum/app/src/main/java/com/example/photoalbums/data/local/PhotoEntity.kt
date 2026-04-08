package com.example.photoalbums.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey val uri: String,
    val serverId: Int? = null,
    val description: String,
    val tags: List<String>,
    val albumNames: List<String> = emptyList(),
    val isUploaded: Boolean = false,
    val category: String = "unknown",
    val imageUrl: String? = null,
    val faceCount: Int = 0
)

