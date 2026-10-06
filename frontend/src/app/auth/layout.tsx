import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TodoFlow | Authentication",
  description: "Initialize your TodoFlow session",
  keywords: ["todo", "tasks", "productivity", "login", "authentication"],
};

export default function AuthLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="bg-[#0a0a0a] text-[#fafaf9] min-h-screen selection:bg-emerald-500/30">
      {children}
    </div>
  );
}