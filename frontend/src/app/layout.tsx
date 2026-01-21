import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Toaster } from "sonner";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Quant Value Dashboard",
  description: "Bloomberg Terminal style Value Investing Screen",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${jetbrainsMono.variable} dark`}
      style={{ colorScheme: "dark" }}
    >
      <body className="min-h-screen flex flex-col font-sans antialiased text-slate-100 bg-slate-950">
        <Toaster theme="dark" position="bottom-right" />
        {children}
      </body>
    </html>
  );
}
