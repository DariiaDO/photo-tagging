package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity

object GroupingUtils {

    fun groupByTags(
        photos: List<PhotoEntity>
    ): Map<String, List<PhotoEntity>> {

        val map = mutableMapOf<String, MutableList<PhotoEntity>>()

        photos.forEach { photo ->
            photo.tags.forEach { tag ->
                val normalizedTag = tag.trim()
                if (normalizedTag.isNotEmpty()) {
                    map.getOrPut(normalizedTag) { mutableListOf() }.add(photo)
                }
            }
        }

        return map
    }
}
