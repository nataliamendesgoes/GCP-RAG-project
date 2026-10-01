import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Site estático (pasta out/) para o Firebase Hosting; o chat roda todo no navegador
  output: "export",
  // Evita que o Next use frontend/package-lock.json (vazio) como raiz do workspace
  turbopack: { root: __dirname },
};

export default nextConfig;
