#!/usr/bin/env node

/**
 * Cleanup script to remove excessive per-image JSON metadata files
 * while keeping the main info.json files
 */

const fs = require("fs").promises;
const path = require("path");

async function cleanupMetadata(directory) {
  let deletedCount = 0;
  let keptCount = 0;

  try {
    async function processDirectory(dir) {
      const items = await fs.readdir(dir, { withFileTypes: true });

      for (const item of items) {
        const itemPath = path.join(dir, item.name);

        if (item.isDirectory()) {
          await processDirectory(itemPath);
        } else if (item.name.endsWith(".json")) {
          // Keep info.json files, delete per-image JSON files
          if (item.name === "info.json") {
            keptCount++;
            console.log(`Keeping: ${itemPath}`);
          } else if (
            item.name.includes(".webp.json") ||
            item.name.includes(".jpg.json") ||
            item.name.includes(".png.json")
          ) {
            await fs.unlink(itemPath);
            deletedCount++;
            console.log(`Deleted: ${itemPath}`);
          } else {
            keptCount++;
            console.log(`Keeping (other): ${itemPath}`);
          }
        }
      }
    }

    await processDirectory(directory);

    console.log(`\n✅ Cleanup complete!`);
    console.log(`📁 Deleted ${deletedCount} per-image JSON files`);
    console.log(`📁 Kept ${keptCount} important JSON files`);
  } catch (error) {
    console.error("Error during cleanup:", error);
  }
}

// Main execution
const outputDir = path.join(__dirname, "gallery-dl-downloads");

console.log("🧹 Starting metadata cleanup...");
console.log(`📁 Target directory: ${outputDir}`);
console.log(
  "📝 This will remove per-image JSON files but keep info.json files\n"
);

cleanupMetadata(outputDir);
