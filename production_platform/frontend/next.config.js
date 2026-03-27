/** @type {import('next').NextConfig} */
const nextConfig = {
    // Increase the webpack chunk load timeout (default is 120s — too short
    // on slower machines when 1300+ modules are being compiled)
    webpack: (config, { dev }) => {
        if (dev) {
            config.output.chunkLoadTimeout = 300000; // 5 minutes for dev
        }
        return config;
    },
};

module.exports = nextConfig;
