import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer, request as httpRequest } from "node:http";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = fileURLToPath(new URL(".", import.meta.url));
const distDir = resolve(__dirname, "dist");
const indexFile = join(distDir, "index.html");
const port = Number(process.env.FRONTEND_PORT || "18011");
const host = process.env.FRONTEND_HOST || "0.0.0.0";
const backendUrl = new URL(process.env.BACKEND_URL || "http://127.0.0.1:18010");

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2"
};

function sendFile(res, filePath) {
  const ext = extname(filePath);
  res.writeHead(200, {
    "Content-Type": mimeTypes[ext] || "application/octet-stream",
    "Cache-Control": filePath === indexFile ? "no-cache" : "public, max-age=31536000, immutable"
  });
  createReadStream(filePath).pipe(res);
}

function resolveStaticPath(pathname) {
  const decodedPath = decodeURIComponent(pathname.split("?")[0]);
  const cleanPath = normalize(decodedPath).replace(/^(\.\.[/\\])+/, "");
  const candidate = resolve(distDir, `.${cleanPath}`);
  if (!candidate.startsWith(distDir)) return indexFile;
  if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  return indexFile;
}

function proxyToBackend(req, res) {
  const target = new URL(req.url || "/", backendUrl);
  const headers = { ...req.headers, host: backendUrl.host };
  delete headers.connection;

  const proxyReq = httpRequest(
    {
      protocol: backendUrl.protocol,
      hostname: backendUrl.hostname,
      port: backendUrl.port,
      method: req.method,
      path: `${target.pathname}${target.search}`,
      headers
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );

  proxyReq.on("error", (error) => {
    res.writeHead(502, { "Content-Type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ detail: `Backend proxy failed: ${error.message}` }));
  });

  req.pipe(proxyReq);
}

const server = createServer((req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (url.pathname === "/health" || url.pathname.startsWith("/api/")) {
    proxyToBackend(req, res);
    return;
  }

  sendFile(res, resolveStaticPath(url.pathname));
});

server.listen(port, host, () => {
  console.log(`Kaoyan Agent frontend listening on http://${host}:${port}`);
  console.log(`Proxying API requests to ${backendUrl.origin}`);
});
