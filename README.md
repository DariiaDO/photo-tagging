# Photo App

Monorepo with two parts:

- `backend/` - Django + Django REST Framework API for photo upload and image analysis.
- `mobile/PhotoAlbum/` - Android application for browsing photos and working with analyzed results.

## Project Structure

```text
photo-app/
|-- backend/
|   |-- manage.py
|   |-- requirements.txt
|   |-- photo_tagging_api/
|   `-- photos/
`-- mobile/
    `-- PhotoAlbum/
```

## Backend

The backend:

- accepts image uploads;
- stores uploaded files in `backend/media/`;
- saves analysis results in SQLite;
- sends images to an external LLaVA endpoint and extracts tags/category/description.

### Stack

- Python
- Django
- Django REST Framework
- Pillow
- requests
- deep-translator

### Run Locally

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8080
```

API base URL in local development:

```text
http://127.0.0.1:8080/
```

Main upload endpoint:

```text
POST /api/upload/
```

Multipart fields:

- `images` - one or more image files
- `client_photo_ids` - optional repeated field to map response items to local records

### Environment Variables

The backend reads these variables:

- `LLAVA_COLAB_URL` - external endpoint for image analysis
- `LLAVA_PROMPT` - custom prompt sent to the model
- `LLAVA_TIMEOUT_SECONDS` - request timeout
- `LLAVA_AUTH_TOKEN` - bearer token for the analysis service

Example:

```powershell
$env:LLAVA_COLAB_URL="https://your-endpoint.example/analyze"
$env:LLAVA_TIMEOUT_SECONDS="120"
python manage.py runserver 0.0.0.0:8080
```

## Mobile App

Android app located in `mobile/PhotoAlbum/`.

### Stack

- Kotlin
- Android SDK
- Room
- Retrofit
- OkHttp
- Coil

### Open and Run

1. Open `mobile/PhotoAlbum` in Android Studio.
2. Sync Gradle.
3. Set the backend URL if needed.
4. Run the app on a device or emulator.

The debug backend URL is configured through Gradle property:

```text
photoAlbumsDebugApiBaseUrl
```

Default value from the project:

```text
http://172.20.10.4:8080/
```

You can override it, for example in `~/.gradle/gradle.properties`:

```properties
photoAlbumsDebugApiBaseUrl=http://10.0.2.2:8080/
```

For Android Emulator, `10.0.2.2` usually points to the host machine.

## Local Data

The repository currently contains local runtime artifacts such as:

- SQLite database files
- uploaded media
- Python cache
- Android build output

They should stay out of version control. The root `.gitignore` is configured for that.

## Useful Commands

Backend tests:

```powershell
cd backend
python manage.py test
```

Android debug build:

```powershell
cd mobile\PhotoAlbum
.\gradlew.bat assembleDebug
```
