import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8080";

const serviceAdapter = new ExperimentalEmptyAdapter();

// Create a custom agent that proxies to the FastAPI backend
class RCAAgent {
  name = "rca-agent";
  description =
    "RCA investigation agent that analyzes incidents by collecting evidence from logs, deployments, builds, and code changes.";

  async execute(request: Request): Promise<Response> {
    const body = await request.text();

    const response = await fetch(`${BACKEND_URL}/copilotkit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body,
    });

    return response;
  }
}

const runtime = new CopilotRuntime({
  agents: {
    // @ts-expect-error - type mismatch between ag-ui versions
    "rca-agent": new RCAAgent(),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};

export const GET = async () => {
  return Response.json({
    actions: [],
    agents: [
      {
        name: "rca-agent",
        description:
          "RCA investigation agent that analyzes incidents by collecting evidence from logs, deployments, builds, and code changes.",
        type: "langgraph",
      },
    ],
    sdkVersion: "1.0.0",
  });
};
