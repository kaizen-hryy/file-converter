// Example client code for testing the gallery-dl Express API

const API_BASE = "http://localhost:3000";

class GalleryDlClient {
  constructor(baseUrl = API_BASE) {
    this.baseUrl = baseUrl;
  }

  async checkHealth() {
    const response = await fetch(`${this.baseUrl}/health`);
    return await response.json();
  }

  async checkGalleryDl() {
    const response = await fetch(`${this.baseUrl}/gallery-dl/info`);
    return await response.json();
  }

  async startDownload(url, options = {}) {
    const response = await fetch(`${this.baseUrl}/download`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url, options }),
    });
    return await response.json();
  }

  async getDownloadStatus(downloadId) {
    const response = await fetch(`${this.baseUrl}/download/${downloadId}`);
    return await response.json();
  }

  async getAllDownloads() {
    const response = await fetch(`${this.baseUrl}/downloads`);
    return await response.json();
  }

  async cancelDownload(downloadId) {
    const response = await fetch(`${this.baseUrl}/download/${downloadId}`, {
      method: "DELETE",
    });
    return await response.json();
  }

  async getDownloadLogs(downloadId) {
    const response = await fetch(`${this.baseUrl}/download/${downloadId}/logs`);
    return await response.json();
  }

  async cleanup(olderThanHours = 24) {
    const response = await fetch(`${this.baseUrl}/cleanup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ olderThanHours }),
    });
    return await response.json();
  }

  // Utility method to poll download status until completion
  async waitForDownload(downloadId, pollInterval = 2000) {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getDownloadStatus(downloadId);

          console.log(`Download ${downloadId} status: ${status.status}`);

          if (status.status === "completed") {
            resolve(status);
          } else if (
            status.status === "failed" ||
            status.status === "cancelled"
          ) {
            reject(
              new Error(
                `Download ${status.status}: ${status.error || "Unknown error"}`
              )
            );
          } else {
            // Still downloading, continue polling
            setTimeout(poll, pollInterval);
          }
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  }
}

// Example usage
async function example() {
  const client = new GalleryDlClient();

  try {
    // Check if server is running
    console.log("Checking server health...");
    const health = await client.checkHealth();
    console.log("Server health:", health);

    // Check if gallery-dl is available
    console.log("Checking gallery-dl availability...");
    const galleryDlInfo = await client.checkGalleryDl();
    console.log("Gallery-dl info:", galleryDlInfo);

    if (!galleryDlInfo.available) {
      console.error("gallery-dl is not available. Please install it first.");
      return;
    }

    // Example URLs (replace with actual URLs you want to test)
    const testUrls = [
      "https://danbooru.donmai.us/posts?tags=bonocho",
      // Add more test URLs here
    ];

    for (const url of testUrls) {
      console.log(`\nStarting download for: ${url}`);

      // Start download
      const downloadResult = await client.startDownload(url, {
        language: "en",
        // Add more options as needed
        // username: 'your_username',
        // password: 'your_password',
      });

      if (downloadResult.success) {
        console.log(`Download started with ID: ${downloadResult.downloadId}`);

        // Wait for completion (optional)
        try {
          const completedDownload = await client.waitForDownload(
            downloadResult.downloadId
          );
          console.log("Download completed:", completedDownload);
        } catch (error) {
          console.error("Download failed:", error.message);
        }
      } else {
        console.error("Failed to start download:", downloadResult.error);
      }
    }

    // Get all downloads
    console.log("\nGetting all downloads...");
    const allDownloads = await client.getAllDownloads();
    console.log("All downloads:", allDownloads);
  } catch (error) {
    console.error("Error:", error);
  }
}

// Uncomment the line below to run the example
// example();

module.exports = GalleryDlClient;
