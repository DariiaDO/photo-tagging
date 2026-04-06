# LLaVA Colab Endpoint

This folder contains the notebook `llava_endpoint.ipynb`.

The notebook is used to run an image analysis endpoint in Google Colab for the backend. It loads `llava-hf/llava-1.5-7b-hf`, starts a FastAPI server, and exposes the API through a Cloudflare tunnel.

## What The Notebook Does

- installs the required Python packages in Colab;
- loads the LLaVA model in 4-bit mode to reduce memory usage;
- starts a FastAPI app;
- provides `GET /health`;
- provides `POST /analyze`;
- creates a public `trycloudflare` URL for external access;
- allows the Django backend to call the Colab endpoint through `LLAVA_COLAB_URL`.

## API Endpoints

Local endpoint inside Colab:

- `http://127.0.0.1:8000`

Available routes:

- `GET /health`
- `POST /analyze`

The `POST /analyze` request expects:

- multipart field `image`
- multipart field `prompt`
- optional `Authorization: Bearer <token>` header if token check is enabled in the notebook

Authentication setup in Colab:

- store the API token in Colab secrets as `API_AUTH_TOKEN`
- the notebook reads this value through `userdata.get("API_AUTH_TOKEN")`
- if the secret is missing, the endpoint starts without bearer-token protection

Expected response shape:

```json
{
  "description": "..."
}
```

## How It Connects To The Backend

The Django backend sends images to the external endpoint from:

- `backend/photos/services/vision_api.py`

Relevant backend environment variable:

- `LLAVA_COLAB_URL`

After starting the tunnel in Colab, copy the public `/analyze` URL and set it in the backend before running Django.

Example:

```powershell
$env:LLAVA_COLAB_URL="https://your-subdomain.trycloudflare.com/analyze"
python manage.py runserver 0.0.0.0:8080
```

## Notebook Flow

Recommended order in Colab:

1. Run the main server cell.
2. Wait until `/health` responds successfully.
3. Run the `cloudflared` installation cell.
4. Run the tunnel cell and copy the public URL.
5. Test `/analyze` with `curl` or through the Django backend.

## Notes

- the FastAPI server in the notebook runs on port `8000`;
- the Django app runs separately in `backend/`;
- the public Cloudflare URL changes when the tunnel is restarted;
- do not hardcode API tokens directly inside the notebook;
- large datasets and generated artifacts should not be committed here.
