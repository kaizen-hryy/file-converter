# Gallery-dl Express Backend

A Node.js Express backend that provides a REST API for downloading images and galleries using [gallery-dl](https://github.com/mikf/gallery-dl) as a child process.

## Features

- 🚀 REST API for gallery-dl downloads
- 📊 Real-time download status tracking
- 🔄 Progress monitoring and logging
- 🛑 Download cancellation support
- 🧹 Automatic cleanup of temporary files
- 🌐 Web interface for easy testing
- 🔐 Authentication support (username/password, cookies)
- ⚙️ Custom gallery-dl arguments support
- 📝 Comprehensive logging

## Prerequisites

1. **Node.js** (v14 or higher)
2. **gallery-dl** installed and accessible in PATH
   ```bash
   pip install gallery-dl
   # or
   brew install gallery-dl
   ```

## Installation

1. Clone or download this project
2. Install dependencies:
   ```bash
   npm install
   ```

## Usage

### Start the Server

```bash
# Development mode (with nodemon)
npm run dev

# Production mode
npm start
```

The server will start on `http://localhost:3000` by default.

### Check Installation

1. Visit `http://localhost:3000/health` to check server status
2. Visit `http://localhost:3000/gallery-dl/info` to verify gallery-dl installation
3. Open `web-interface.html` in your browser for a GUI interface

## API Endpoints

### Health Check

```
GET /health
```

Returns server status and active download count.

### Start Download

```
POST /download
Content-Type: application/json

{
  "url": "https://example.com/gallery",
  "options": {
    "language": "en",
    "username": "optional_username",
    "password": "optional_password",
    "cookies": "/path/to/cookies.txt",
    "customArgs": ["--write-thumbnail", "--no-metadata"]
  }
}
```

### Get Download Status

```
GET /download/:id
```

Returns detailed information about a specific download.

### Get All Downloads

```
GET /downloads
```

Returns information about all downloads.

### Cancel Download

```
DELETE /download/:id
```

Cancels an active download.

### Get Download Logs

```
GET /download/:id/logs
```

Returns logs for a specific download.

### Cleanup Old Downloads

```
POST /cleanup
Content-Type: application/json

{
  "olderThanHours": 24
}
```

Removes downloads older than specified hours.

### Process Existing Downloads

```
POST /process-existing
```

Processes any existing downloads in the temp directory, moving them to the output directory. This is useful for handling downloads that may have been left in the temp directory due to server restarts or unexpected shutdowns.

### Check Gallery-dl

```
GET /gallery-dl/info
```

Checks if gallery-dl is installed and returns version information.

## Example Usage

### Using JavaScript/Node.js

```javascript
const GalleryDlClient = require("./client-example");

const client = new GalleryDlClient("http://localhost:3000");

async function downloadExample() {
  // Start download
  const result = await client.startDownload(
    "https://danbooru.donmai.us/posts?tags=example",
    {
      language: "en",
    }
  );

  if (result.success) {
    console.log("Download started:", result.downloadId);

    // Wait for completion
    const completedDownload = await client.waitForDownload(result.downloadId);
    console.log("Download completed:", completedDownload);
  }
}
```

### Using cURL

```bash
# Start a download
curl -X POST http://localhost:3000/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://danbooru.donmai.us/posts?tags=example",
    "options": {
      "language": "en"
    }
  }'

# Check download status
curl http://localhost:3000/download/DOWNLOAD_ID

# Cancel download
curl -X DELETE http://localhost:3000/download/DOWNLOAD_ID
```

## Configuration

You can modify the configuration in `server.js`:

```javascript
const CONFIG = {
  tempDir: path.join(__dirname, "temp_downloads"), // Temporary download directory
  outputDir: path.join(__dirname, "gallery-dl-downloads"), // Final output directory
  maxConcurrentDownloads: 3, // Maximum concurrent downloads
};
```

## Supported Gallery-dl Options

The API supports most gallery-dl options through the `options` object:

- `language`: Language preference (e.g., "en", "jp")
- `username`/`password`: Authentication credentials
- `cookies`: Path to cookies file or browser name
- `customArgs`: Array of custom gallery-dl arguments

**Note on Metadata**: By default, the server only downloads one `info.json` file per gallery/post to avoid cluttering the download with individual JSON files for each image. If you need per-image metadata, you can add `"--write-metadata"` to the `customArgs` array:

```javascript
{
  "url": "https://example.com/gallery",
  "options": {
    "customArgs": ["--write-metadata"]
  }
}
```

## Web Interface

Open `web-interface.html` in your browser for a user-friendly interface that allows you to:

- Start downloads with a form
- Monitor download progress in real-time
- View logs and cancel downloads
- Clean up old downloads

## Integration with Python Script

This Express backend is designed to work alongside your existing Python manga downloader (`manga-dl.py`). You can:

1. Use the API to trigger downloads programmatically
2. Integrate the backend into your existing workflow
3. Build a web frontend that uses both the Node.js API and Python scripts

## Error Handling

The API provides comprehensive error handling:

- Invalid URLs are rejected
- Concurrent download limits are enforced
- Process errors are captured and logged
- Temporary files are cleaned up automatically

## Security Considerations

- The API accepts authentication credentials but stores them temporarily in memory
- Ensure your server is properly secured if exposing it publicly
- Consider using environment variables for sensitive configuration
- The cleanup endpoint helps prevent disk space issues

## Troubleshooting

### Gallery-dl not found

```bash
# Check if gallery-dl is in PATH
gallery-dl --version

# Install gallery-dl
pip install gallery-dl
```

### Permission errors

- Ensure the Node.js process has write permissions to the temp and output directories
- Check that gallery-dl can write to the specified directories

### Port conflicts

- Change the PORT environment variable: `PORT=8080 npm start`
- Update the API_BASE in client code accordingly

## File Structure

```
file-converter/
├── server.js              # Main Express server
├── client-example.js      # JavaScript client example
├── web-interface.html     # Web interface
├── package.json           # Node.js dependencies
├── manga-dl.py           # Original Python script
├── webp_to_cbz.py        # Image conversion script
├── temp_downloads/       # Temporary download directory (created automatically)
├── gallery-dl-downloads/ # Final output directory (created automatically)
└── .gitignore           # Git ignore file
```

## Future Enhancements

- WebSocket support for real-time progress updates
- Download queuing system
- Integration with CBZ conversion from your Python scripts
- User authentication and authorization
- Download scheduling
- Database storage for download history

## License

ISC License (same as your existing project)
