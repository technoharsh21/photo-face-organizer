"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DOCS_NAV } from "@/data/docs";

export function DocsSidebar() {
  const pathname = usePathname();

  // Group by category
  const categories = Array.from(new Set(DOCS_NAV.map((d) => d.category)));

  return (
    <nav className="w-full md:w-64 flex-shrink-0 space-y-6">
      {categories.map((cat) => {
        const items = DOCS_NAV.filter((d) => d.category === cat);
        return (
          <div key={cat} className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500 px-3">
              {cat}
            </h3>
            <ul className="space-y-1">
              {items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`block px-3 py-2 rounded-lg text-sm transition-colors ${
                        isActive
                          ? "bg-brand-50 dark:bg-brand-950/50 text-brand-600 dark:text-brand-400 font-semibold"
                          : "text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-900 hover:text-slate-900 dark:hover:text-slate-200"
                      }`}
                    >
                      {item.title}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}
