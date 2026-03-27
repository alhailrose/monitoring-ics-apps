/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  transpilePackages: ['@xterm/xterm', '@xterm/addon-fit', '@xterm/addon-web-links'],
}

export default nextConfig
