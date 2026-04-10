package com.example.photoalbums.data.repository

import com.example.photoalbums.data.local.PhotoEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PhotoRepositoryTest {

    @Test
    fun buildTagAlbumDescriptors_keepsUserDefinedEmptyAlbum() {
        val photos = listOf(
            PhotoEntity(
                uri = "uri-1",
                description = "dog",
                tags = listOf("dog"),
                albumKeys = listOf("tag:Животные")
            )
        )

        val albums = PhotoRepository.buildTagAlbumDescriptors(
            photos = photos,
            requestedTags = listOf("Животные", "Машины")
        )

        assertEquals(listOf("tag:Животные", "tag:Машины"), albums.map { it.key })
        assertEquals(0, albums.first { it.key == "tag:Машины" }.photoCount)
    }

    @Test
    fun buildTagAlbumDescriptors_hidesEmptyOtherAlbum() {
        val photos = listOf(
            PhotoEntity(
                uri = "uri-1",
                description = "dog",
                tags = listOf("dog"),
                albumKeys = listOf("tag:Животные")
            )
        )

        val albums = PhotoRepository.buildTagAlbumDescriptors(
            photos = photos,
            requestedTags = listOf("Животные")
        )

        assertFalse(albums.any { it.key == "tag:Другое" })
        assertTrue(albums.any { it.key == "tag:Животные" })
    }
}
