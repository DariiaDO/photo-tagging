package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity

object GroupingUtils {

    fun groupByAlbums(photos: List<PhotoEntity>): Map<String, List<PhotoEntity>> {
        val grouped = linkedMapOf<String, MutableList<PhotoEntity>>()

        photos.forEach { photo ->
            photo.albumNames
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .distinct()
                .forEach { albumName ->
                    grouped.getOrPut(albumName) { mutableListOf() }.add(photo)
                }
        }

        return grouped
    }
}

