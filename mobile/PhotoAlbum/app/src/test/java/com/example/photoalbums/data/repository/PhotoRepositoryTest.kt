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
                tags = listOf("Животные"),
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
                tags = listOf("Животные"),
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

    @Test
    fun buildTagAlbumDescriptors_ignoresUnselectedTagAlbums() {
        val photos = listOf(
            PhotoEntity(
                uri = "uri-1",
                description = "sunset",
                tags = listOf("Природа", "Закат"),
                albumKeys = listOf("tag:Природа", "tag:Закат")
            ),
            PhotoEntity(
                uri = "uri-2",
                description = "unknown object",
                tags = emptyList(),
                albumKeys = listOf("tag:Другое")
            )
        )

        val albums = PhotoRepository.buildTagAlbumDescriptors(
            photos = photos,
            requestedTags = listOf("Природа")
        )

        assertEquals(listOf("tag:Природа", "tag:Другое"), albums.map { it.key })
        assertFalse(albums.any { it.key == "tag:Закат" })
    }

    @Test
    fun buildTagAlbumDescriptors_matchesCurrentUserTagByRussianDescription() {
        val photos = listOf(
            PhotoEntity(
                uri = "uri-1",
                description = "Штрих-код на белой упаковке",
                tags = listOf("Документы"),
                albumKeys = listOf("tag:Другое")
            )
        )

        val albums = PhotoRepository.buildTagAlbumDescriptors(
            photos = photos,
            requestedTags = listOf("штрих-ко")
        )

        assertEquals(listOf("tag:штрих-ко"), albums.map { it.key })
        assertEquals(1, albums.first().photoCount)
        assertEquals("uri-1", albums.first().coverUri)
    }
}
