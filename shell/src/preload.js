const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("batchkit", {
  platform: process.platform,
});
