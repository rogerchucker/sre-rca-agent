import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import "@copilotkit/react-ui/styles.css";
import { Sidebar } from "@/components/layout/sidebar";
import { CopilotProvider } from "@/components/providers/copilot-provider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "RCA Agent",
  description: "AI-powered Root Cause Analysis for Incident Investigation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <CopilotProvider>
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 ml-16">{children}</main>
          </div>
        </CopilotProvider>
      </body>
    </html>
  );
}
