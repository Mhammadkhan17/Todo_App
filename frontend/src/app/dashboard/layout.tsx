import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "TodoFlow | Dashboard",
  description: "Your personal task management dashboard",
};

export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <>{children}</>;
}