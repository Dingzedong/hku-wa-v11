import { defineConfig } from "vite";
import fs from "fs";
import path from "path";

function tryLoadLocalHttpsCerts() {
  try {
    const keyPath = path.resolve(__dirname, "certs/localhost-key.pem");
    const certPath = path.resolve(__dirname, "certs/localhost.pem");

    if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
      return {
        key: fs.readFileSync(keyPath),
        cert: fs.readFileSync(certPath),
      };
    }
  } catch (e) {
    // 任何错误（包括 CI 没有文件）都忽略，保证 build 不会挂
  }
  return null;
}

export default defineConfig(({ command }) => {
  const config: any = {
    // ✅ 这里一定要保留你项目原本的其它配置（plugins / resolve / base 等）
  };

  // ✅ 只在本地开发 server 时尝试启用 https
  if (command === "serve" && !process.env.CI && !process.env.GITHUB_ACTIONS) {
    const https = tryLoadLocalHttpsCerts();
    if (https) {
      config.server = { https };
    }
  }

  return config;
});
