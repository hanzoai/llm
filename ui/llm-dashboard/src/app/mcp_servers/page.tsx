"use client";
import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { modelHubCall } from "@/components/networking";
import MCPServerHub from "@/components/mcp_server_hub";

export default function PublicMCPServers() {
  const searchParams = useSearchParams()!;
  const key = searchParams.get("key");
  const [accessToken, setAccessToken] = useState<string | null>(null);

  useEffect(() => {
    if (!key) {
      return;
    }
    setAccessToken(key);
  }, [key]);

  return (
    <MCPServerHub accessToken={accessToken} publicPage={true} premiumUser={false} />
  );
}