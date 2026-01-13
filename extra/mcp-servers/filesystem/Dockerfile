
# Use the official image as base
FROM mcp/filesystem:latest

# We need to install express for our bridge
# The official image is based on alpine, so we have npm
WORKDIR /app

# Copy our bridge script
COPY sse-bridge.js /app/

# Install dependencies for the bridge
RUN npm install express body-parser

# Override the ENTRYPOINT to run our bridge instead of the default server directly
# The bridge will spawn the original server (node /app/dist/index.js)
ENTRYPOINT ["node", "sse-bridge.js"]
# Pass default arguments to the bridge (which passes them to the server)
CMD ["/data"]
