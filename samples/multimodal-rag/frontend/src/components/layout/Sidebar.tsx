import { Link, useLocation } from "react-router-dom";
import { cn } from "@/lib/utils";
import { IconMenu2, IconX } from "@tabler/icons-react";

const navigation = [
  { name: "Home", href: "/" },
  { name: "Introduction", href: "/introduction" },
  { name: "BDA Control Plane", href: "/bda-control" },
];

interface SidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ isCollapsed, onToggle }: SidebarProps) {
  const location = useLocation();

  return (
    <div 
      className={cn(
        "flex h-full flex-col bg-white border-r transition-all duration-300",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex h-14 items-center justify-end px-4 border-b">
        <button
          onClick={onToggle}
          className="p-2 rounded-md hover:bg-gray-100"
          aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {isCollapsed ? <IconMenu2 size={20} /> : <IconX size={20} />}
        </button>
      </div>
      <div className="flex flex-grow flex-col overflow-y-auto">
        <nav className="flex-1 space-y-1 px-2 py-4" aria-label="Sidebar">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  isActive
                    ? "bg-orange-100 text-gray-900"
                    : "text-gray-600 hover:bg-gray-50 hover:text-gray-900",
                  "group flex items-center rounded-md px-2 py-2 text-sm font-medium",
                  isCollapsed && "justify-center"
                )}
                title={isCollapsed ? item.name : undefined}
              >
                {!isCollapsed && item.name}
                {isCollapsed && item.name[0]}
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}