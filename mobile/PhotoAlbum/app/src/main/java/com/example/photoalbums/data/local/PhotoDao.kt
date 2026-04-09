package com.example.photoalbums.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Dao
interface PhotoDao {

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(photo: PhotoEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(photos: List<PhotoEntity>)

    @Query("SELECT * FROM photos ORDER BY uri ASC")
    suspend fun getAll(): List<PhotoEntity>

    @Query(
        """
        SELECT * FROM photos
        WHERE description LIKE '%' || :query || '%'
        OR tags LIKE '%' || :query || '%'
        OR faceNumbers LIKE '%' || :query || '%'
        ORDER BY uri ASC
        """
    )
    suspend fun search(query: String): List<PhotoEntity>

    @Query("SELECT uri FROM photos WHERE isUploaded = 1")
    suspend fun getUploadedUris(): List<String>

    @Query(
        """
        UPDATE photos
        SET isUploaded = 0,
            serverId = NULL,
            albumNames = '[]',
            albumKeys = '[]',
            faceNumbers = '[]'
        """
    )
    suspend fun resetUploadMarkers()
}
