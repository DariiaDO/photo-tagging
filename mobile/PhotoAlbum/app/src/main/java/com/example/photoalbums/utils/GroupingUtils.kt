package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity

object GroupingUtils {

    fun groupByAlbums(photos: List<PhotoEntity>): Map<String, List<PhotoEntity>> {
        val grouped = linkedMapOf<String, MutableList<PhotoEntity>>()

        photos.forEach { photo ->
            photo.albumKeys
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .distinct()
                .forEach { albumKey ->
                    grouped.getOrPut(albumKey) { mutableListOf() }.add(photo)
                }
        }

        return grouped
    }
}
