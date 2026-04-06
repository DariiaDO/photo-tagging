package com.example.photoalbums.utils

import com.example.photoalbums.data.local.PhotoEntity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class GroupingUtilsTest {

    @Test
    fun groupByTags_groupsPhotosByNormalizedTag() {
        val first = PhotoEntity("uri-1", "sea", listOf("travel", " summer "))
        val second = PhotoEntity("uri-2", "sun", listOf("travel", ""))

        val grouped = GroupingUtils.groupByTags(listOf(first, second))

        assertEquals(listOf(first, second), grouped["travel"])
        assertEquals(listOf(first), grouped["summer"])
        assertTrue("" !in grouped.keys)
    }
}
