import { Outlet } from "react-router-dom";
import NavBar from "@/components/Navbar";
import { Sidebar } from "./Sidebar";
import { useState } from "react";

export function Layout() {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen">
      <Sidebar 
        isCollapsed={isSidebarCollapsed} 
        onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)} 
      />
      <div className="flex-1 flex flex-col">
      <NavBar />
      <main className="flex-1 overflow-y-auto p-8">
        <Outlet />
      </main>
      </div>
    </div>
  );
} 