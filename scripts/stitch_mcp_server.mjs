#!/usr/bin/env node

/**
 * Universal STDIO MCP Server for Google Stitch
 * Powered by Google's official @google/stitch-sdk
 */

import { Server } from '../frontend/node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js';
import { StdioServerTransport } from '../frontend/node_modules/@modelcontextprotocol/sdk/dist/esm/server/stdio.js';
import { ListToolsRequestSchema, CallToolRequestSchema } from '../frontend/node_modules/@modelcontextprotocol/sdk/dist/esm/types.js';
import { stitch } from '../frontend/node_modules/@google/stitch-sdk/dist/src/index.js';

async function main() {
  const server = new Server(
    { name: 'google-stitch', version: '1.0.0' },
    { capabilities: { tools: {} } }
  );

  // List all Stitch tools directly from Google's official API
  server.setRequestHandler(ListToolsRequestSchema, async () => {
    try {
      const { tools } = await stitch.listTools();
      return {
        tools: tools.map((t) => ({
          name: t.name,
          description: t.description || '',
          inputSchema: t.inputSchema || { type: 'object', properties: {} },
        })),
      };
    } catch (err) {
      console.error('[stitch-mcp] Error listing tools:', err);
      return { tools: [] };
    }
  });

  // Call Stitch tool
  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    try {
      const result = await stitch.callTool(name, args || {});
      return {
        content: [
          {
            type: 'text',
            text: typeof result === 'string' ? result : JSON.stringify(result, null, 2),
          },
        ],
      };
    } catch (err) {
      console.error(`[stitch-mcp] Error calling tool ${name}:`, err);
      return {
        content: [{ type: 'text', text: `Error calling ${name}: ${err.message || String(err)}` }],
        isError: true,
      };
    }
  });

  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('[stitch-mcp] Connected to Google Stitch MCP via official SDK.');
}

main().catch((err) => {
  console.error('[stitch-mcp] Fatal error:', err);
  process.exit(1);
});
