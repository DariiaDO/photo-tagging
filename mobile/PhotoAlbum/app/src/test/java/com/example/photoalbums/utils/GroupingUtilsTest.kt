package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity
import org.junit.Assert.assertEquals
import org.junit.Test

class GroupingUtilsTest {

    @Test
    fun groupByAlbums_groupsPhotosByAlbumName() {
        val first = PhotoEntity(
            uri = "uri-1",
            description = "sea",
            tags = listOf("travel"),
            albumNames = listOf("Путешествия", "Природа")
        )
        val second = PhotoEntity(
            uri = "uri-2",
            description = "dog",
            tags = listOf("dog"),
            albumNames = listOf("Животные")
        )

        val grouped = GroupingUtils.groupByAlbums(listOf(first, second))

        assertEquals(listOf(first), grouped["Путешествия"])
        assertEquals(listOf(first), grouped["Природа"])
        assertEquals(listOf(second), grouped["Животные"])
    }
}

