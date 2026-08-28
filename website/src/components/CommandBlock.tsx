"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CommandBlockProps {
  command: string;
  language?: string;
}

export function CommandBlock({ command, language = "bash" }: CommandBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error("Failed to copy command:", e);
    }
  };

  return (
    <div className="relative my-4 rounded-xl border border-slate-800 bg-slate-950 text-slate-100 overflow-hidden font-mono text-sm shadow-md">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-900/80 border-b border-slate-800 text-xs text-slate-400">
        <span>{language}</span>
        <button
          onClick={handleCopy}
          className="inline-flex items-center gap-1 px-2.5 py-1 rounded hover:bg-slate-800 text-slate-300 hover:text-white transition-colors focus:outline-none focus:ring-1 focus:ring-brand-500"
          aria-label="Copy code command"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-emerald-400 font-sans font-medium">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span className="font-sans">Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-4 overflow-x-auto whitespace-pre">
        <code>{command}</code>
      </div>
    </div>
  );
}
