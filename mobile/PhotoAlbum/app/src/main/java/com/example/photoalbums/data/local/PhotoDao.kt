package com.example.photoalbums.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PhotoDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(photo: PhotoEntity)

    @Query("SELECT * FROM photos")
    suspend fun getAll(): List<PhotoEntity>

    @Query(
        """
        SELECT * FROM photos
        WHERE description LIKE '%' || :query || '%'
        OR tags LIKE '%' || :query || '%'
        """
    )
    suspend fun search(query: String): List<PhotoEntity>
}
