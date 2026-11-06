import type { Metadata } from "next";
import { SchemesClient } from "@/components/schemes-client";

export const metadata: Metadata = {
  title: "Schemes",
  description: "Every scheme in the PolicyDrift store with a timeline of its rule versions and effective dates.",
};

export default function SchemesPage() {
  return <SchemesClient />;
}
