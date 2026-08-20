"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, setToken } from "@/lib/api";
import type { User } from "@/lib/types";
import { Button, Brand } from "@/components/ui/Button";
import { IconAttempts, IconHome, IconListen, IconMock, IconProgress, IconRead, IconSettings, IconSpeak, IconWrite } from "@/components/ui/Icons";

const groups = [
  {
    label: "Practice",
    links: [
      { href: "/app", label: "Home", icon: IconHome },
      { href: "/app/listening", label: "Listening", icon: IconListen },
      { href: "/app/reading", label: "Reading", icon: IconRead },
      { href: "/app/writing", label: "Writing", icon: IconWrite },
      { href: "/app/speaking", label: "Speaking", icon: IconSpeak },
      { href: "/app/mock", label: "Full mock", icon: IconMock },
    ],
  },
  {
    label: "Review",
    links: [
      { href: "/app/attempts", label: "Attempts", icon: IconAttempts },
      { href: "/app/progress", label: "Progress", icon: IconProgress },
    ],
  },
];

const tabs = [
  { href: "/app", label: "Home", icon: IconHome },
  { href: "/app/listening", label: "Listen", icon: IconListen },
  { href: "/app/reading", label: "Read", icon: IconRead },
  { href: "/app/writing", label: "Write", icon: IconWrite },
  { href: "/app/speaking", label: "Speak", icon: IconSpeak },
];

function active(pathname: string, href: string) {
  if (href === "/app") return pathname === "/app";
  return pathname === href || pathname.startsWith(`${href}/`);
}

function initials(name?: string) {
  if (!name?.trim()) return "N";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => {
        setToken(null);
        router.replace("/login");
      });
  }, [router]);

  function logout() {
    setToken(null);
    router.replace("/");
  }

  return (
    <div className="shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="side">
        <Brand href="/app" />
        <nav aria-label="Studio">
          {groups.map((group) => (
            <div key={group.label}>
              <p className="nav-group">{group.label}</p>
              {group.links.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`nav-link${active(pathname, link.href) ? " active" : ""}`}
                  aria-current={active(pathname, link.href) ? "page" : undefined}
                >
                  <link.icon />
                  {link.label}
                </Link>
              ))}
            </div>
          ))}
          <p className="nav-group">Account</p>
          <Link
            href="/app/settings"
            className={`nav-link${active(pathname, "/app/settings") ? " active" : ""}`}
            aria-current={active(pathname, "/app/settings") ? "page" : undefined}
          >
            <IconSettings />
            Settings
          </Link>
        </nav>
        <div className="side-foot">
          <div className="user-chip">
            <span className="avatar">{initials(user?.display_name)}</span>
            <span title={user?.display_name}>{user?.display_name ?? " "}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </aside>
      <div>
        <header className="mobile-bar">
          <Brand href="/app" />
          <Link href="/app/settings" className="icon-btn" aria-label="Settings">
            <IconSettings />
          </Link>
        </header>
        <div className="main" id="main">
          <div className="canvas">{children}</div>
        </div>
      </div>
      <nav className="bottom-nav" aria-label="Primary">
        {tabs.map((tab) => (
          <Link key={tab.href} href={tab.href} className={active(pathname, tab.href) ? "active" : ""}>
            <tab.icon />
            {tab.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
