package com.example.photoalbums.data.local

import org.junit.Assert.assertEquals
import org.junit.Test

class ConvertersTest {

    private val converters = Converters()

    @Test
    fun tagsRoundTrip_preservesItems() {
        val tags = listOf("travel", "summer", "sea")

        val serialized = converters.fromTags(tags)

        assertEquals(tags, converters.toTags(serialized))
    }

    @Test
    fun toTags_returnsEmptyListForEmptyString() {
        assertEquals(emptyList<String>(), converters.toTags(""))
    }
}
