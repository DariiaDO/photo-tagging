plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.ksp)
}

android {
    namespace = "com.example.photoalbums"
    compileSdk = 36

    val debugApiBaseUrl = providers.gradleProperty("photoAlbumsDebugApiBaseUrl")
        .orElse("http://185.182.108.239/")
        .get()
    val releaseApiBaseUrl = providers.gradleProperty("photoAlbumsReleaseApiBaseUrl")
        .orElse("https://example.com/")
        .get()
    val debugApiAuthToken = providers.gradleProperty("photoAlbumsDebugApiAuthToken")
        .orElse("")
        .get()
    val releaseApiAuthToken = providers.gradleProperty("photoAlbumsReleaseApiAuthToken")
        .orElse("")
        .get()

    defaultConfig {
        applicationId = "com.example.photoalbums"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        debug {
            buildConfigField("String", "API_BASE_URL", "\"$debugApiBaseUrl\"")
            buildConfigField("String", "PHOTO_API_AUTH_TOKEN", "\"$debugApiAuthToken\"")
        }
        release {
            buildConfigField("String", "API_BASE_URL", "\"$releaseApiBaseUrl\"")
            buildConfigField("String", "PHOTO_API_AUTH_TOKEN", "\"$releaseApiAuthToken\"")
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    buildFeatures {
        buildConfig = true
        viewBinding = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
}

dependencies {
    val room_version = "2.6.1"
    implementation("androidx.room:room-runtime:$room_version")
    implementation("androidx.room:room-ktx:$room_version")
    ksp("androidx.room:room-compiler:$room_version")
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation(libs.material)
    implementation("io.coil-kt:coil:2.6.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.0")
    implementation("com.google.ai.client.generativeai:generativeai:0.7.0")
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.recyclerview)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.google.mlkit:translate:17.0.3")
}
