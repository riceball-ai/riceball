
import express from 'express';
import bodyParser from 'body-parser';
import { spawn } from 'child_process';
import path from 'path';

const app = express();
const PORT = process.env.PORT || 8000;

// Path to the MCP server executable
// In mcp/filesystem docker image, the code is at /app/dist/index.js
const SERVER_SCRIPT = process.env.MCP_SERVER_SCRIPT || '/app/dist/index.js';
const SERVER_ARGS = process.argv.slice(2).length > 0 ? process.argv.slice(2) : ['/data']; // Default to /data if no args

console.log(`Starting Stdio->SSE Bridge for: ${SERVER_SCRIPT} ${SERVER_ARGS.join(' ')}`);

// Spawn the MCP server process
const child = spawn('node', [SERVER_SCRIPT, ...SERVER_ARGS], {
    stdio: ['pipe', 'pipe', 'inherit'] // Pipe stdin/stdout, inherit stderr for logs
});

child.on('error', (err) => {
    console.error('Failed to start child process:', err);
});

child.on('exit', (code, signal) => {
    console.error(`Child process exited with code ${code} signal ${signal}`);
    process.exit(code || 1);
});

// SSE clients
let sseClients = [];

// Handle stdout (MCP responses from child)
let buffer = '';
child.stdout.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line

    lines.forEach(line => {
        if (!line.trim()) return;
        try {
            // Validate JSON? Or just forward?
            // MCP spec: each line is a JSON-RPC message
            // Forward to all connected SSE clients
            sseClients.forEach(res => {
                res.write(`event: message\n`);
                res.write(`data: ${line}\n\n`);
            });
        } catch (e) {
            console.error('Error forwarding message:', e);
        }
    });
});

app.use(bodyParser.json());

// SSE Endpoint
app.get('/sse', (req, res) => {
    res.writeHead(200, {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
    });

    const clientId = Date.now();
    sseClients.push(res);
    console.log(`Client connected: ${clientId}. Total: ${sseClients.length}`);

    // Send the endpoint event as per MCP SSE spec
    // The client uses this endpoint to POST messages
    res.write(`event: endpoint\n`);
    res.write(`data: /messages?session_id=${clientId}\n\n`);

    req.on('close', () => {
        sseClients = sseClients.filter(c => c !== res);
        console.log(`Client disconnected: ${clientId}. Total: ${sseClients.length}`);
    });
});

// Messages Endpoint
app.post('/messages', (req, res) => {
    const message = req.body;
    // console.log('Received message:', JSON.stringify(message).substring(0, 50) + "...");
    
    // Forward to child process stdin
    // Must end with newline
    child.stdin.write(JSON.stringify(message) + "\n");
    
    res.status(202).send("Accepted");
});

app.listen(PORT, () => {
    console.log(`MCP Stdio-to-SSE Bridge listening on port ${PORT}`);
});
