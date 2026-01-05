import { defineConfig } from "vite";
import fs from "fs";
import path from "path";

export default defineConfig(({ command }) => {
  const config: any = {
    // 你原本的其它配置保持不变（plugins / resolve / base 等）
  };

  // ✅ 只有本地开发 (vite serve / npm run dev) 才尝试启用 https
  if (command === "serve") {
    const keyPath = path.resolve(__dirname, "certs/localhost-key.pem");
    const certPath = path.resolve(__dirname, "certs/localhost.pem");

    if (fs.existsSync(keyPath) && fs.existsSync(certPath)) {
      config.server = {
        https: {
          key: fs.readFileSync(keyPath),
          cert: fs.readFileSync(certPath),
        },
      };
    } else {
      // 没证书就退回 http（本地也能跑，只是 play.workadventure 可能跨域）
      config.server = {};
    }
  }

  return config;
});
