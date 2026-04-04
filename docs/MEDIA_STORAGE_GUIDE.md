# Media Storage Guide

## Overview

The media storage system provides a complete solution for managing multimedia files with support for both S3/MinIO (cloud storage) and local filesystem storage. The system automatically switches between backends based on configuration, making it easy to develop locally and deploy to production with S3.

## Features

- Automatic backend selection (S3/MinIO or local filesystem)
- File upload with metadata tracking
- File download and streaming
- Pre-signed URLs for direct S3 access
- Automatic file organization by date (YYYY/MM/DD structure)
- File type detection (image, video, audio, document, other)
- WebSocket real-time notifications on file changes
- Advanced filtering and pagination
- User-specific media queries
- Public/private file access control

## Configuration

### Environment Variables

Add to your `.env` file:

```env
# Storage Configuration (S3/MinIO)
USE_S3=False
S3_ENDPOINT_URL=http://localhost:9000  # MinIO endpoint (leave empty for AWS S3)
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET_NAME=media
S3_REGION=us-east-1

# Local storage (used when USE_S3=False)
MEDIA_FOLDER=./media
MAX_FILE_SIZE=10485760  # 10MB in bytes
```

### Local Storage (Development)

**Default configuration** - no additional setup required:

```env
USE_S3=False
MEDIA_FOLDER=./media
MAX_FILE_SIZE=10485760
```

Files will be stored in the `./media` folder with automatic date-based organization.

### AWS S3 (Production)

Configure for AWS S3:

```env
USE_S3=True
S3_ENDPOINT_URL=  # Leave empty for AWS S3
S3_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE
S3_SECRET_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
S3_BUCKET_NAME=my-app-media
S3_REGION=us-east-1
```

### MinIO (Self-hosted S3-compatible)

Configure for MinIO:

```env
USE_S3=True
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=media
S3_REGION=us-east-1
```

## API Endpoints

### Upload File

**POST /media/upload**

Upload a file with metadata.

**Request** (multipart/form-data):
- `file`: The file to upload (required)
- `description`: File description (optional)
- `alt_text`: Alt text for accessibility (optional)
- `user_id`: Owner user ID (optional)
- `is_public`: Public access flag (optional, default: false)

**Example with curl**:

```bash
curl -X POST "http://localhost:8000/media/upload" \
  -F "file=@image.jpg" \
  -F "description=Profile picture" \
  -F "alt_text=User profile photo" \
  -F "user_id=1" \
  -F "is_public=true"
```

**Response**:

```json
{
  "id": 1,
  "filename": "image.jpg",
  "file_size": 245678,
  "file_type": "image",
  "url": "http://localhost:8000/media/1/download",
  "download_url": "http://localhost:8000/media/1/download",
  "message": "File uploaded successfully"
}
```

### Get All Media

**GET /media/**

Get all media files with URLs.

**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)

```bash
curl http://localhost:8000/media/
```

### Get Media by ID

**GET /media/{media_id}**

Get specific media file with URLs.

```bash
curl http://localhost:8000/media/1
```

### Download File

**GET /media/{media_id}/download**

Download the actual file content.

```bash
curl http://localhost:8000/media/1/download --output downloaded_file.jpg
```

### Update Media Metadata

**PATCH /media/{media_id}**

Update media metadata (not the file itself).

```bash
curl -X PATCH "http://localhost:8000/media/1" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description",
    "alt_text": "Updated alt text",
    "is_public": true
  }'
```

### Delete Media

**DELETE /media/{media_id}**

Delete media file and metadata from both database and storage.

```bash
curl -X DELETE "http://localhost:8000/media/1"
```

### Get Media by User

**GET /media/user/{user_id}**

Get all media files for a specific user.

```bash
curl http://localhost:8000/media/user/1
```

### Get Media by Type

**GET /media/type/{file_type}**

Get all media files of a specific type.

**Types**: `image`, `video`, `audio`, `document`, `other`

```bash
curl http://localhost:8000/media/type/image
```

### Get Public Media

**GET /media/public/list**

Get all public media files.

```bash
curl http://localhost:8000/media/public/list
```

### Filter Media

**POST /media/filter**

Filter media with advanced queries.

```bash
curl -X POST "http://localhost:8000/media/filter" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "file_type", "operator": "eq", "value": "image"},
      {"field": "is_public", "operator": "eq", "value": true}
    ],
    "operator": "and",
    "order_by": "created_at",
    "order_direction": "desc",
    "limit": 10
  }'
```

### Filter Media (Paginated)

**POST /media/filter/paginated**

Filter with pagination metadata.

```bash
curl -X POST "http://localhost:8000/media/filter/paginated" \
  -H "Content-Type: application/json" \
  -d '{
    "conditions": [
      {"field": "user_id", "operator": "eq", "value": 1}
    ],
    "limit": 20,
    "offset": 0
  }'
```

### Storage Info

**GET /media/stats/info**

Get storage backend information.

```bash
curl http://localhost:8000/media/stats/info
```

**Response**:

```json
{
  "backend": "local",
  "bucket_name": null,
  "media_folder": "C:\\path\\to\\media",
  "endpoint_url": null
}
```

## WebSocket Real-time Updates

Connect to the media channel to receive real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/media');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Media update:', data);

    switch(data.type) {
        case 'created':
            console.log('New file uploaded:', data.data);
            break;
        case 'updated':
            console.log('File metadata updated:', data.data);
            break;
        case 'deleted':
            console.log('File deleted:', data.data.id);
            break;
    }
};
```

## Frontend Integration

### JavaScript Example

```javascript
async function uploadFile(file, metadata = {}) {
    const formData = new FormData();
    formData.append('file', file);

    if (metadata.description) formData.append('description', metadata.description);
    if (metadata.alt_text) formData.append('alt_text', metadata.alt_text);
    if (metadata.user_id) formData.append('user_id', metadata.user_id);
    if (metadata.is_public !== undefined) formData.append('is_public', metadata.is_public);

    const response = await fetch('http://localhost:8000/media/upload', {
        method: 'POST',
        body: formData
    });

    return await response.json();
}

// Usage
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    const result = await uploadFile(file, {
        description: 'My file',
        is_public: true
    });
    console.log('Uploaded:', result);
});
```

### React Example

```typescript
import { useState } from 'react';

interface UploadResponse {
    id: number;
    filename: string;
    file_size: number;
    file_type: string;
    url: string;
    download_url: string;
    message: string;
}

function FileUpload() {
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<UploadResponse | null>(null);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('is_public', 'true');

        try {
            const response = await fetch('http://localhost:8000/media/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error('Upload failed:', error);
        } finally {
            setUploading(false);
        }
    };

    return (
        <div>
            <input
                type="file"
                onChange={handleUpload}
                disabled={uploading}
            />
            {uploading && <p>Uploading...</p>}
            {result && (
                <div>
                    <p>File uploaded: {result.filename}</p>
                    <img src={result.url} alt={result.filename} />
                </div>
            )}
        </div>
    );
}
```

### Vue Example

```vue
<template>
  <div>
    <input
      type="file"
      @change="handleUpload"
      :disabled="uploading"
    />
    <p v-if="uploading">Uploading...</p>
    <div v-if="result">
      <p>File uploaded: {{ result.filename }}</p>
      <img :src="result.url" :alt="result.filename" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const uploading = ref(false);
const result = ref(null);

const handleUpload = async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  uploading.value = true;

  const formData = new FormData();
  formData.append('file', file);
  formData.append('is_public', 'true');

  try {
    const response = await fetch('http://localhost:8000/media/upload', {
      method: 'POST',
      body: formData
    });

    result.value = await response.json();
  } catch (error) {
    console.error('Upload failed:', error);
  } finally {
    uploading.value = false;
  }
};
</script>
```

## File Type Detection

The system automatically detects file types based on MIME type:

- **image**: image/jpeg, image/png, image/gif, etc.
- **video**: video/mp4, video/webm, etc.
- **audio**: audio/mpeg, audio/wav, etc.
- **document**: application/pdf, .docx, .xlsx, etc.
- **other**: Everything else

## Storage Organization

### Local Storage

Files are automatically organized by date:

```
media/
├── 2024/
│   ├── 01/
│   │   ├── 15/
│   │   │   ├── uuid1_image.jpg
│   │   │   └── uuid2_document.pdf
│   │   └── 16/
│   │       └── uuid3_video.mp4
│   └── 02/
│       └── 01/
│           └── uuid4_audio.mp3
```

### S3 Storage

Same structure in S3 bucket keys:

```
s3://my-bucket/
├── 2024/01/15/uuid1_image.jpg
├── 2024/01/15/uuid2_document.pdf
├── 2024/01/16/uuid3_video.mp4
└── 2024/02/01/uuid4_audio.mp3
```

## Security Considerations

### File Size Limits

Configure maximum file size in `.env`:

```env
MAX_FILE_SIZE=10485760  # 10MB
```

Requests exceeding this limit will receive a 413 error.

### File Validation

The system includes:
- Filename sanitization (prevents directory traversal)
- MIME type validation
- Size limit enforcement

### Access Control

Use the `is_public` flag:
- `true`: File accessible without authentication
- `false`: Requires authentication (implement in your app)

### S3 Pre-signed URLs

For S3 storage, pre-signed URLs expire after 1 hour by default. Configure in code if needed.

## Setting up MinIO (Local S3)

### Using Docker

```bash
docker run -p 9000:9000 -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  quay.io/minio/minio server /data --console-address ":9001"
```

Access MinIO Console at: http://localhost:9001

### Configure MinIO

1. Access console at http://localhost:9001
2. Login with `minioadmin` / `minioadmin`
3. Create a bucket named `media`
4. Update your `.env` file:

```env
USE_S3=True
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET_NAME=media
```

## Common Use Cases

### Profile Pictures

```python
# Upload profile picture
await media_service.upload_file(
    session=session,
    file=file,
    filename="profile.jpg",
    mime_type="image/jpeg",
    user_id=user.id,
    alt_text=f"Profile picture for {user.name}",
    is_public=True
)
```

### Gallery with Filtering

```python
# Get all images for a user
filters = QueryFilter(
    conditions=[
        Condition(field="user_id", operator=FilterOperator.EQ, value=user_id),
        Condition(field="file_type", operator=FilterOperator.EQ, value="image")
    ],
    order_by="created_at",
    order_direction="desc"
)

images = media_service.filter(session, filters)
```

### Public File Sharing

```python
# Upload public file
media = await media_service.upload_file(
    session=session,
    file=file,
    filename="shared_document.pdf",
    is_public=True
)

# Share URL
share_url = f"https://yourdomain.com/media/{media.id}/download"
```

## Architecture

```
┌─────────────────┐
│   Client        │
└────────┬────────┘
         │ Upload file
         ↓
┌─────────────────┐
│  Media Routes   │
│  /media/upload  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  MediaService   │
│  (BaseService)  │
└────┬────────┬───┘
     │        │
     ↓        ↓
┌────────┐  ┌────────────┐
│   DB   │  │  Storage   │
│ (Meta) │  │  Service   │
└────────┘  └──────┬─────┘
                   │
            ┌──────┴──────┐
            │             │
     ┌──────▼──────┐  ┌───▼─────┐
     │Local Storage│  │S3/MinIO │
     └─────────────┘  └─────────┘
```

## Best Practices

1. **Development**: Use local storage (`USE_S3=False`)
2. **Production**: Use S3 for scalability and reliability
3. **File Size**: Set appropriate `MAX_FILE_SIZE` based on your needs
4. **Public Files**: Only set `is_public=True` for files that should be publicly accessible
5. **Cleanup**: Implement periodic cleanup of unused files
6. **Backups**: Regularly backup your S3 bucket or local media folder
7. **CDN**: For production, consider using CloudFront or similar CDN with S3
8. **Validation**: Validate file types on client-side before upload

## Troubleshooting

### Local Storage Permission Issues

Ensure the `MEDIA_FOLDER` directory is writable:

```bash
chmod 755 ./media
```

### S3 Connection Issues

Check:
1. AWS credentials are correct
2. Bucket exists and is accessible
3. Region is correct
4. For MinIO, endpoint URL is reachable

### File Upload Fails

Common causes:
1. File too large (check `MAX_FILE_SIZE`)
2. Storage backend unavailable
3. Insufficient permissions
4. Network issues

Check server logs for detailed error messages.

## Examples

See the complete working examples in:
- Frontend upload form: `/static/media-upload-test.html` (to be created)
- API documentation: http://localhost:8000/docs
- WebSocket tester: http://localhost:8000/static/websocket-test.html

## Related Documentation

- [BASE_SERVICE_ARCHITECTURE.md](BASE_SERVICE_ARCHITECTURE.md) - BaseService documentation
- [FILTERING_GUIDE.md](FILTERING_GUIDE.md) - Advanced filtering
- [WEBSOCKET_GUIDE.md](WEBSOCKET_GUIDE.md) - WebSocket guide
- [README.md](README.md) - Main documentation
