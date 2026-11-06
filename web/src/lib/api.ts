// Typed client for the PolicyDrift FastAPI backend.
// With NEXT_PUBLIC_DEMO_FIXTURES=1 every call resolves from ./fixtures instead of the network.

import {
  askFixture,
  examplesFixture,
  healthFixture,
  resultsFixture,
  schemesFixture,
} from "./fixtures";
import { todayISO } from "./format";
import type { AskRequest, AskResponse, Examples, Health, Results, Scheme } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

export const DEMO_FIXTURES = process.env.NEXT_PUBLIC_DEMO_FIXTURES === "1";

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function delay<T>(value: T, ms: number): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...(init?.body ? { "Content-Type": "application/json" } : {}) },
    });
  } catch {
    throw new ApiError(`Could not reach the PolicyDrift API at ${API_URL}.`, 0);
  }
  if (!res.ok) {
    let detail = `Request failed with HTTP ${res.status}.`;
    try {
      const body: unknown = await res.json();
      if (body && typeof body === "object" && "detail" in body) {
        const d = (body as { detail: unknown }).detail;
        if (typeof d === "string") detail = d;
        else if (Array.isArray(d)) detail = "The request was not valid. Check the question and date.";
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export function ask(body: AskRequest, signal?: AbortSignal): Promise<AskResponse> {
  if (DEMO_FIXTURES) return delay(askFixture(body, todayISO()), 700);
  return request<AskResponse>("/api/ask", { method: "POST", body: JSON.stringify(body), signal });
}

export function getSchemes(): Promise<Scheme[]> {
  if (DEMO_FIXTURES) return delay(schemesFixture, 150);
  return request<Scheme[]>("/api/schemes");
}

export function getExamples(): Promise<Examples> {
  if (DEMO_FIXTURES) return delay(examplesFixture, 100);
  return request<Examples>("/api/examples");
}

export function getResults(): Promise<Results> {
  if (DEMO_FIXTURES) return delay(resultsFixture, 150);
  return request<Results>("/api/results");
}

export function getHealth(): Promise<Health> {
  if (DEMO_FIXTURES) return delay(healthFixture, 50);
  return request<Health>("/api/health");
}
