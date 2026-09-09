import React from "react";

export function DockerIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M22.5 10.8c-.3-.2-1.2-.4-2.1-.2-.1-.5-.4-1.2-.9-1.7l-.6.4c.4.4.6 1 .7 1.5-.6.1-1.6.4-2.1 1.2-.4-.2-.9-.3-1.6-.3h-3.5v-2h2v-2h-2v-1h-2v1h-2v-2h-2v2h-2v2h2v2H2.3c-.2.7-.1 1.5.1 2.3.9 3.4 3.9 6.2 8.7 6.2 6.5 0 10.9-4.1 11.4-8.9.7-.5 1.1-1.1 1.1-1.2l-1.1-.3z"
        fill="#0db7ed"
      />
      <rect x="5.5" y="8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="7.8" y="8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="10.1" y="8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="7.8" y="5.8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="10.1" y="5.8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="12.4" y="8" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
      <rect x="10.1" y="3.6" width="1.8" height="1.8" rx="0.3" fill="#0db7ed" />
    </svg>
  );
}

export function KubernetesIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="#326ce5" strokeWidth="1.5" />
      <path
        d="M12 4.5l6.5 3.8v7.4L12 19.5l-6.5-3.8V8.3L12 4.5z"
        stroke="#326ce5"
        strokeWidth="1.5"
      />
      <circle cx="12" cy="12" r="2.5" fill="#326ce5" />
      <path d="M12 6.5v3M12 14.5v3M7.2 9.2l2.6 1.5M14.2 13.3l2.6 1.5M7.2 14.8l2.6-1.5M14.2 10.7l2.6-1.5" stroke="#326ce5" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

export function AwsIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M6.5 8.5h2.2v4.8c0 .7.1 1.2.4 1.5.3.3.7.4 1.2.4.6 0 1-.2 1.4-.5.4-.4.6-.9.6-1.6V8.5h2.2v4.7c0 1.2-.4 2.1-1.1 2.8-.7.7-1.8 1-3.1 1s-2.3-.3-3-1c-.7-.7-1.1-1.6-1.1-2.8V8.5z"
        fill="#ff9900"
      />
      <path
        d="M4.5 17.5c4 2.5 10 2.5 14.5 0"
        stroke="#ff9900"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path d="M17.5 16.5l2 1-1.2 1.8" fill="#ff9900" />
    </svg>
  );
}

export function CloudflareIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M17.8 15.5c.8-.4 1.3-1.2 1.3-2.1 0-1.4-1.1-2.5-2.5-2.5-.2 0-.4 0-.6.1-.5-1.8-2.1-3-4-3-1.7 0-3.2 1-3.8 2.5-.3-.1-.7-.1-1-.1-2.2 0-4 1.8-4 4 0 .3 0 .7.1 1h14.5z"
        fill="#f38020"
      />
      <path
        d="M19.5 15.5c.3-.3.5-.8.5-1.3 0-1-.8-1.8-1.8-1.8-.1 0-.3 0-.4.1-.4-1.2-1.5-2-2.8-2-.5 0-.9.1-1.3.3.4.7.6 1.4.6 2.2 0 .4-.1.8-.2 1.2.4.2.8.6 1.1 1.1h4.3z"
        fill="#faad3f"
      />
    </svg>
  );
}

export function GitHubIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor">
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export function PythonIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M11.9 2c-3.1 0-5 1.4-5 3.3v2.2h5v.8H5c-1.9 0-3.3 1.4-3.3 3.4 0 2.2 1.4 3.3 3.3 3.3h1.7v-2.1c0-1.9 1.4-3.3 3.4-3.3h5V7.7c0-2-1.4-3.3-3.4-3.3h-.9V2h1.1zm-2 1.6a.8.8 0 110 1.6.8.8 0 010-1.6z"
        fill="#3776ab"
      />
      <path
        d="M12.1 22c3.1 0 5-1.4 5-3.3v-2.2h-5v-.8h6.9c1.9 0 3.3-1.4 3.3-3.4 0-2.2-1.4-3.3-3.3-3.3h-1.7v2.1c0 1.9-1.4 3.3-3.4 3.3h-5v1.9c0 2 1.4 3.3 3.4 3.3h.9v2.1h-1.1zm2-1.6a.8.8 0 110-1.6.8.8 0 010 1.6z"
        fill="#ffd43b"
      />
    </svg>
  );
}

export function ReactIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <ellipse cx="12" cy="12" rx="9" ry="3.5" stroke="#61dafb" strokeWidth="1.2" transform="rotate(0 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="3.5" stroke="#61dafb" strokeWidth="1.2" transform="rotate(60 12 12)" />
      <ellipse cx="12" cy="12" rx="9" ry="3.5" stroke="#61dafb" strokeWidth="1.2" transform="rotate(120 12 12)" />
      <circle cx="12" cy="12" r="1.5" fill="#61dafb" />
    </svg>
  );
}

export function NextJsIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" fill="currentColor" />
      <path d="M15.5 8.5v7l-5-7.5v7.5" stroke="#ffffff" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TypeScriptIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect x="2" y="2" width="20" height="20" rx="4" fill="#3178c6" />
      <path d="M7 9h5M9.5 9v8M14 13.5c.8.8 1.8 1.2 2.8 1.2 1 0 1.6-.4 1.6-1 0-.7-.6-1-1.8-1.4-1.6-.5-2.6-1.2-2.6-2.6 0-1.4 1.1-2.4 2.8-2.4 1 0 1.9.4 2.6 1l-.8 1.2c-.6-.5-1.2-.8-1.8-.8-.8 0-1.3.4-1.3.9 0 .6.5.9 1.6 1.3 1.7.6 2.8 1.2 2.8 2.7 0 1.5-1.2 2.5-3.1 2.5-1.2 0-2.3-.5-3.2-1.3l.8-1.3z" fill="#ffffff" />
    </svg>
  );
}

export function PostgresIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <ellipse cx="12" cy="7" rx="8" ry="3" stroke="#336791" strokeWidth="1.5" fill="#336791" fillOpacity="0.15" />
      <path d="M4 7v5c0 1.66 3.58 3 8 3s8-1.34 8-3V7" stroke="#336791" strokeWidth="1.5" />
      <path d="M4 12v5c0 1.66 3.58 3 8 3s8-1.34 8-3v-5" stroke="#336791" strokeWidth="1.5" />
    </svg>
  );
}

export function RedisIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2l9 5-9 5-9-5 9-5z" fill="#dc382d" fillOpacity="0.8" stroke="#dc382d" strokeWidth="1" />
      <path d="M3 11.5l9 5 9-5" stroke="#dc382d" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M3 16.5l9 5 9-5" stroke="#dc382d" strokeWidth="1.5" strokeLinecap="round" />
      <circle cx="12" cy="7" r="1.5" fill="#ffffff" />
    </svg>
  );
}

export function GraphQLIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2.5l8.2 4.8v9.4L12 21.5l-8.2-4.8V7.3L12 2.5z" stroke="#e10098" strokeWidth="1.4" />
      <circle cx="12" cy="2.5" r="1.5" fill="#e10098" />
      <circle cx="20.2" cy="7.3" r="1.5" fill="#e10098" />
      <circle cx="20.2" cy="16.7" r="1.5" fill="#e10098" />
      <circle cx="12" cy="21.5" r="1.5" fill="#e10098" />
      <circle cx="3.8" cy="16.7" r="1.5" fill="#e10098" />
      <circle cx="3.8" cy="7.3" r="1.5" fill="#e10098" />
      <path d="M12 2.5v19M3.8 7.3l16.4 9.4M3.8 16.7L20.2 7.3" stroke="#e10098" strokeWidth="1" strokeOpacity="0.7" />
    </svg>
  );
}

export function LinuxIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2c-3.3 0-5 2.5-5 5.5 0 1.5.5 3.5.5 4.5s-2 2-2 4.5c0 2.5 2.5 4.5 6.5 4.5s6.5-2 6.5-4.5c0-2.5-2-3.5-2-4.5s.5-3 .5-4.5C17 4.5 15.3 2 12 2z" stroke="#fcc624" strokeWidth="1.5" fill="#fcc624" fillOpacity="0.2" />
      <circle cx="10" cy="7.5" r="1" fill="#0f172a" />
      <circle cx="14" cy="7.5" r="1" fill="#0f172a" />
      <path d="M11 9.5c.5.5 1.5.5 2 0" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function CyberShieldIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path
        d="M12 2L4 5.5v6.5c0 5.2 3.4 10.1 8 11.5 4.6-1.4 8-6.3 8-11.5V5.5L12 2z"
        stroke="#10b981"
        strokeWidth="1.6"
        fill="#10b981"
        fillOpacity="0.15"
      />
      <path d="M9 12l2 2 4-4" stroke="#10b981" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function TlsLockIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect x="5" y="10" width="14" height="11" rx="3" stroke="#8b5cf6" strokeWidth="1.6" fill="#8b5cf6" fillOpacity="0.15" />
      <path d="M8 10V7a4 4 0 118 0v3" stroke="#8b5cf6" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="12" cy="15.5" r="1.5" fill="#8b5cf6" />
    </svg>
  );
}

export function DnsIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="5" r="3" stroke="#06b6d4" strokeWidth="1.5" fill="#06b6d4" fillOpacity="0.2" />
      <circle cx="6" cy="18" r="3" stroke="#06b6d4" strokeWidth="1.5" fill="#06b6d4" fillOpacity="0.2" />
      <circle cx="18" cy="18" r="3" stroke="#06b6d4" strokeWidth="1.5" fill="#06b6d4" fillOpacity="0.2" />
      <path d="M12 8v4m0 0l-6 3m6-3l6 3" stroke="#06b6d4" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function ApiNetworkIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect x="4" y="4" width="6" height="6" rx="1.5" stroke="#6366f1" strokeWidth="1.5" />
      <rect x="14" y="4" width="6" height="6" rx="1.5" stroke="#6366f1" strokeWidth="1.5" />
      <rect x="9" y="14" width="6" height="6" rx="1.5" stroke="#6366f1" strokeWidth="1.5" />
      <path d="M10 7h4M7 10v2a2 2 0 002 2h3m5-4v2a2 2 0 01-2 2h-3" stroke="#6366f1" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function BountyBugIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <ellipse cx="12" cy="13" rx="5" ry="6" stroke="#f43f5e" strokeWidth="1.5" fill="#f43f5e" fillOpacity="0.15" />
      <circle cx="12" cy="6" r="3" stroke="#f43f5e" strokeWidth="1.5" />
      <path d="M10 3.5l-2-2M14 3.5l2-2" stroke="#f43f5e" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M7 11H3M7 15l-4 2M7 9L3 7M17 11h4M17 15l4 2M17 9l4-2" stroke="#f43f5e" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}
