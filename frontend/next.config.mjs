/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/copilotkit/:path*",
        destination:
          process.env.BACKEND_URL
            ? `${process.env.BACKEND_URL}/copilotkit/:path*`
            : "http://localhost:8080/copilotkit/:path*",
      },
    ];
  },
};

export default nextConfig;
