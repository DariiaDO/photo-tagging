package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity
import org.junit.Assert.assertEquals
import org.junit.Test

class GroupingUtilsTest {

    @Test
    fun groupByAlbums_groupsPhotosByAlbumKey() {
        val first = PhotoEntity(
            uri = "uri-1",
            description = "sea",
            tags = listOf("travel"),
            albumKeys = listOf("tag:Путешествия", "face:1")
        )
        val second = PhotoEntity(
            uri = "uri-2",
            description = "dog",
            tags = listOf("dog"),
            albumKeys = listOf("face:1")
        )

        val grouped = GroupingUtils.groupByAlbums(listOf(first, second))

        assertEquals(listOf(first), grouped["tag:Путешествия"])
        assertEquals(listOf(first, second), grouped["face:1"])
    }
}
