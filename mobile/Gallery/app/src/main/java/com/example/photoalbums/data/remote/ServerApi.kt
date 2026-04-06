package com.example.photoalbums.data.remote

import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

data class AnalyzeResponse(
    val description: String,
    val tags: List<String>
)

interface ServerApi {

    @Multipart
    @POST("analyze/")
    suspend fun uploadImage(
        @Part file: MultipartBody.Part
    ): Response<AnalyzeResponse>
}
