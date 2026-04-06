package com.example.photoalbums.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey val uri: String,
    val description: String,
    val tags: List<String>
)
