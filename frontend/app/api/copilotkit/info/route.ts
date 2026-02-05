import { NextResponse } from "next/server";

const agentInfo = {
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
};

export async function GET() {
  return NextResponse.json(agentInfo);
}

export async function POST() {
  return NextResponse.json(agentInfo);
}
