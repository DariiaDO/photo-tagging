package com.example.photoalbums.data.local

import org.junit.Assert.assertEquals
import org.junit.Test

class ConvertersTest {

    private val converters = Converters()

    @Test
    fun stringListRoundTrip_preservesItems() {
        val items = listOf("travel", "summer", "sea")

        val serialized = converters.fromStringList(items)

        assertEquals(items, converters.toStringList(serialized))
    }

    @Test
    fun toStringList_returnsEmptyListForEmptyString() {
        assertEquals(emptyList<String>(), converters.toStringList(""))
    }

    @Test
    fun toStringList_supportsLegacyCommaSeparatedFormat() {
        assertEquals(
            listOf("travel", "summer", "sea"),
            converters.toStringList("travel,summer,sea")
        )
    }

    @Test
    fun intListRoundTrip_preservesItems() {
        val items = listOf(1, 4, 8)

        val serialized = converters.fromIntList(items)

        assertEquals(items, converters.toIntList(serialized))
    }
}
