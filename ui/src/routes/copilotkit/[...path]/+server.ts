import { CopilotRuntime, OpenAIAdapter, copilotRuntimeNodeHttpEndpoint } from '@copilotkit/runtime';
import OpenAI from 'openai';
import fs from 'node:fs';
import path from 'node:path';

const runtime = new CopilotRuntime();

function tryLoadEnvFile(filePath: string) {
  if (!fs.existsSync(filePath)) return;
  const raw = fs.readFileSync(filePath, 'utf8');
  for (const line of raw.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (!key) continue;
    const value = trimmed.slice(eq + 1).trim().replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

if (!process.env.OPENAI_API_KEY) {
  const repoRoot = path.resolve(process.cwd(), '..');
  tryLoadEnvFile(path.join(repoRoot, '.env.local'));
  tryLoadEnvFile(path.join(repoRoot, '.env'));
  tryLoadEnvFile(path.join(process.cwd(), '.env.local'));
  tryLoadEnvFile(path.join(process.cwd(), '.env'));
}

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const serviceAdapter = new OpenAIAdapter({
  openai,
  model: process.env.COPILOTKIT_MODEL ?? 'gpt-4o-mini'
});

const handleCopilot = copilotRuntimeNodeHttpEndpoint({
  endpoint: '/copilotkit',
  runtime,
  serviceAdapter
});

async function runCopilot(request: Request): Promise<Response> {
  const response = await handleCopilot(request);
  return response as Response;
}

export async function GET({ request }: { request: Request }): Promise<Response> {
  return runCopilot(request);
}

export async function POST({ request }: { request: Request }): Promise<Response> {
  return runCopilot(request);
}

export async function OPTIONS({ request }: { request: Request }): Promise<Response> {
  return runCopilot(request);
}
