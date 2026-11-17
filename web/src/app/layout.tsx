import type { Metadata } from "next";
import { Suspense } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { BundleProvider } from "@/lib/bundle";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { AuditSheet } from "@/components/audit/audit-sheet";
import { TooltipProvider } from "@/components/ui/tooltip";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SuisseCL Phase A — audit dashboard",
  description: "Where every number in the Swiss Phase A simulation comes from.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col bg-background text-foreground">
        <BundleProvider>
          <TooltipProvider>
            <Suspense fallback={null}>
              <SiteHeader />
              <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6">{children}</main>
              <SiteFooter />
              <AuditSheet />
            </Suspense>
          </TooltipProvider>
        </BundleProvider>
      </body>
    </html>
  );
}
