const express = require("express");
const { spawn } = require("child_process");
const fs = require("fs").promises;
const path = require("path");
const cors = require("cors");
const { v4: uuidv4 } = require("uuid");

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Store active downloads
const activeDownloads = new Map();

// Configuration
const CONFIG = {
  tempDir: path.join(__dirname, "temp_downloads"),
  outputDir: path.join(__dirname, "gallery-dl-downloads"),
  maxConcurrentDownloads: 3,
};

// Ensure directories exist
async function ensureDirectories() {
  try {
    await fs.mkdir(CONFIG.tempDir, { recursive: true });
    await fs.mkdir(CONFIG.outputDir, { recursive: true });
    console.log("✓ Directories created successfully");
  } catch (error) {
    console.error("Error creating directories:", error);
  }
}

// Utility function to sanitize filename
function sanitizeFilename(filename) {
  return filename.replace(/[\\/*?:"<>|]/g, "-").trim();
}

// Utility function to validate URL
function isValidUrl(string) {
  try {
    new URL(string);
    return true;
  } catch (_) {
    return false;
  }
}

// Gallery-dl download function
async function downloadWithGalleryDl(url, options = {}) {
  const downloadId = uuidv4();
  const downloadDir = path.join(CONFIG.tempDir, downloadId);

  try {
    await fs.mkdir(downloadDir, { recursive: true });

    // Build gallery-dl command arguments
    const args = [
      "-d",
      downloadDir, // Download directory
      "--write-metadata", // Write metadata
      "--write-info-json", // Write info JSON
    ];

    // Add language option if specified
    if (options.language) {
      args.push("-o", `lang=${options.language}`);
    }

    // Add authentication if provided
    if (options.username && options.password) {
      args.push("-u", options.username, "-p", options.password);
    }

    // Add cookies if provided
    if (options.cookies) {
      args.push("--cookies", options.cookies);
    }

    // Add custom options
    if (options.customArgs && Array.isArray(options.customArgs)) {
      args.push(...options.customArgs);
    }

    // Add URL
    args.push(url);

    console.log(
      `Starting download ${downloadId} with command: gallery-dl ${args.join(
        " "
      )}`
    );

    const downloadProcess = {
      id: downloadId,
      url,
      status: "downloading",
      startTime: new Date(),
      progress: { downloaded: 0, total: 0, currentFile: "" },
      logs: [],
      error: null,
      downloadDir,
    };

    activeDownloads.set(downloadId, downloadProcess);

    const galleryDl = spawn("gallery-dl", args, {
      cwd: downloadDir,
      stdio: ["pipe", "pipe", "pipe"],
    });

    downloadProcess.process = galleryDl;

    // Handle stdout
    galleryDl.stdout.on("data", (data) => {
      const output = data.toString();
      downloadProcess.logs.push({
        type: "stdout",
        message: output,
        timestamp: new Date(),
      });

      // Parse progress information
      const lines = output.split("\n");
      lines.forEach((line) => {
        if (line.includes("downloading")) {
          downloadProcess.progress.currentFile = line.trim();
        }
        // You can add more progress parsing logic here based on gallery-dl output
      });
    });

    // Handle stderr
    galleryDl.stderr.on("data", (data) => {
      const error = data.toString();
      downloadProcess.logs.push({
        type: "stderr",
        message: error,
        timestamp: new Date(),
      });
    });

    // Handle process completion
    galleryDl.on("close", async (code) => {
      downloadProcess.endTime = new Date();

      if (code === 0) {
        downloadProcess.status = "completed";
        console.log(`Download ${downloadId} completed successfully`);

        // Move files to output directory if needed
        try {
          const outputPath = path.join(CONFIG.outputDir, downloadId);
          await fs.mkdir(path.dirname(outputPath), { recursive: true });

          // You can add post-processing logic here (like converting to CBZ)
          downloadProcess.outputPath = outputPath;
        } catch (error) {
          console.error(
            `Error processing completed download ${downloadId}:`,
            error
          );
          downloadProcess.error = error.message;
        }
      } else {
        downloadProcess.status = "failed";
        downloadProcess.error = `gallery-dl exited with code ${code}`;
        console.log(`Download ${downloadId} failed with code ${code}`);
      }
    });

    galleryDl.on("error", (error) => {
      downloadProcess.status = "failed";
      downloadProcess.error = error.message;
      downloadProcess.endTime = new Date();
      console.error(`Download ${downloadId} error:`, error);
    });

    return downloadId;
  } catch (error) {
    console.error(`Error starting download:`, error);
    if (activeDownloads.has(downloadId)) {
      const download = activeDownloads.get(downloadId);
      download.status = "failed";
      download.error = error.message;
      download.endTime = new Date();
    }
    throw error;
  }
}

// API Routes

// Health check
app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    activeDownloads: activeDownloads.size,
  });
});

// Start download
app.post("/download", async (req, res) => {
  try {
    const { url, options = {} } = req.body;

    // Validate input
    if (!url) {
      return res.status(400).json({ error: "URL is required" });
    }

    if (!isValidUrl(url)) {
      return res.status(400).json({ error: "Invalid URL format" });
    }

    // Check concurrent download limit
    const activeCount = Array.from(activeDownloads.values()).filter(
      (d) => d.status === "downloading"
    ).length;

    if (activeCount >= CONFIG.maxConcurrentDownloads) {
      return res.status(429).json({
        error: "Maximum concurrent downloads reached",
        limit: CONFIG.maxConcurrentDownloads,
        active: activeCount,
      });
    }

    // Start download
    const downloadId = await downloadWithGalleryDl(url, options);

    res.json({
      success: true,
      downloadId,
      message: "Download started successfully",
    });
  } catch (error) {
    console.error("Error starting download:", error);
    res.status(500).json({
      error: "Failed to start download",
      details: error.message,
    });
  }
});

// Get download status
app.get("/download/:id", (req, res) => {
  const { id } = req.params;
  const download = activeDownloads.get(id);

  if (!download) {
    return res.status(404).json({ error: "Download not found" });
  }

  // Return download info without the process object
  const { process, ...downloadInfo } = download;
  res.json(downloadInfo);
});

// Get all downloads
app.get("/downloads", (req, res) => {
  const downloads = Array.from(activeDownloads.entries()).map(
    ([id, download]) => {
      const { process, ...downloadInfo } = download;
      return { id, ...downloadInfo };
    }
  );

  res.json({ downloads });
});

// Cancel download
app.delete("/download/:id", (req, res) => {
  const { id } = req.params;
  const download = activeDownloads.get(id);

  if (!download) {
    return res.status(404).json({ error: "Download not found" });
  }

  if (download.process && download.status === "downloading") {
    try {
      download.process.kill("SIGTERM");
      download.status = "cancelled";
      download.endTime = new Date();

      res.json({
        success: true,
        message: "Download cancelled successfully",
      });
    } catch (error) {
      res.status(500).json({
        error: "Failed to cancel download",
        details: error.message,
      });
    }
  } else {
    res.json({
      success: true,
      message: "Download was not active",
    });
  }
});

// Get download logs
app.get("/download/:id/logs", (req, res) => {
  const { id } = req.params;
  const download = activeDownloads.get(id);

  if (!download) {
    return res.status(404).json({ error: "Download not found" });
  }

  res.json({
    downloadId: id,
    logs: download.logs,
  });
});

// Clean up completed downloads
app.post("/cleanup", async (req, res) => {
  try {
    const { olderThanHours = 24 } = req.body;
    const cutoffTime = new Date(Date.now() - olderThanHours * 60 * 60 * 1000);

    let cleaned = 0;
    for (const [id, download] of activeDownloads.entries()) {
      if (download.endTime && download.endTime < cutoffTime) {
        // Clean up temporary files
        try {
          await fs.rmdir(download.downloadDir, { recursive: true });
        } catch (error) {
          console.warn(`Failed to remove directory for download ${id}:`, error);
        }

        activeDownloads.delete(id);
        cleaned++;
      }
    }

    res.json({
      success: true,
      message: `Cleaned up ${cleaned} downloads`,
      cleaned,
    });
  } catch (error) {
    console.error("Error during cleanup:", error);
    res.status(500).json({
      error: "Cleanup failed",
      details: error.message,
    });
  }
});

// Gallery-dl info endpoint (test if gallery-dl is available)
app.get("/gallery-dl/info", (req, res) => {
  const galleryDl = spawn("gallery-dl", ["--version"]);

  let output = "";
  let error = "";

  galleryDl.stdout.on("data", (data) => {
    output += data.toString();
  });

  galleryDl.stderr.on("data", (data) => {
    error += data.toString();
  });

  galleryDl.on("close", (code) => {
    if (code === 0) {
      res.json({
        available: true,
        version: output.trim(),
        message: "gallery-dl is available",
      });
    } else {
      res.status(500).json({
        available: false,
        error: error || `gallery-dl exited with code ${code}`,
        message: "gallery-dl is not available or not installed",
      });
    }
  });

  galleryDl.on("error", (err) => {
    res.status(500).json({
      available: false,
      error: err.message,
      message: "gallery-dl is not installed or not in PATH",
    });
  });
});

// Error handler
app.use((error, req, res, next) => {
  console.error("Unhandled error:", error);
  res.status(500).json({
    error: "Internal server error",
    details: error.message,
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: "Endpoint not found" });
});

// Graceful shutdown
process.on("SIGINT", async () => {
  console.log("\nShutting down server...");

  // Cancel all active downloads
  for (const [id, download] of activeDownloads.entries()) {
    if (download.process && download.status === "downloading") {
      console.log(`Cancelling download ${id}...`);
      try {
        download.process.kill("SIGTERM");
      } catch (error) {
        console.warn(`Failed to kill process for download ${id}:`, error);
      }
    }
  }

  // Clean up temporary files
  try {
    await fs.rmdir(CONFIG.tempDir, { recursive: true });
    console.log("✓ Temporary files cleaned up");
  } catch (error) {
    console.warn("Warning: Failed to clean up temporary files:", error);
  }

  process.exit(0);
});

// Start server
async function startServer() {
  console.log("Starting server initialization...");
  await ensureDirectories();
  console.log("Directories ensured, starting express app...");

  app.listen(PORT, () => {
    console.log(`🚀 Gallery-dl Express server running on port ${PORT}`);
    console.log(`📁 Temp directory: ${CONFIG.tempDir}`);
    console.log(`📁 Output directory: ${CONFIG.outputDir}`);
    console.log(
      `⚡ Max concurrent downloads: ${CONFIG.maxConcurrentDownloads}`
    );
    console.log(`\nAPI Endpoints:`);
    console.log(`  GET  /health - Health check`);
    console.log(`  POST /download - Start download`);
    console.log(`  GET  /download/:id - Get download status`);
    console.log(`  GET  /downloads - Get all downloads`);
    console.log(`  DELETE /download/:id - Cancel download`);
    console.log(`  GET  /download/:id/logs - Get download logs`);
    console.log(`  POST /cleanup - Clean up old downloads`);
    console.log(`  GET  /gallery-dl/info - Check gallery-dl availability`);
  });
}

console.log("About to start server...");
startServer().catch(console.error);

module.exports = app;
