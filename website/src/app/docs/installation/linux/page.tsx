import { CommandBlock } from "@/components/CommandBlock";
import Link from "next/link";
import { getLatestRelease } from "@/data/releases";

export const metadata = {
  title: "Linux Installation Guide (.deb & Pip) | Photo Face Organizer Docs",
  description: "Complete Linux setup instructions for Debian, Ubuntu, Mint, Fedora, and Arch.",
};

export default function LinuxInstallationPage() {
  const latestRelease = getLatestRelease();
  const debAsset = latestRelease.assets.linux.find((a) => a.type === "deb");

  const debFilename = debAsset ? debAsset.filename : "photo-face-organizer_1.0.0_amd64.deb";

  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Installation &rsaquo; Linux
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Linux Installation Guide
        </h1>
        <p className="text-sm text-slate-500">
          Instructions for Debian/Ubuntu <code>.deb</code> packages, standalone ZIP archives, and command-line <code>pipx</code> setup.
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Method 1: Installing via Debian Package (.deb)
        </h2>
        <p>
          Recommended for Ubuntu, Debian, Linux Mint, Pop!_OS, and elementary OS users.
        </p>

        <p className="font-semibold text-slate-900 dark:text-white">1. Download the package:</p>
        <p className="text-xs text-slate-500">
          Download <code>{debFilename}</code> from our <Link href="/download" className="text-brand-600 underline">Download Page</Link>.
        </p>

        <p className="font-semibold text-slate-900 dark:text-white">2. Run package manager in terminal:</p>
        <CommandBlock
          command={`sudo dpkg -i ${debFilename}`}
          language="bash"
        />

        <p className="font-semibold text-slate-900 dark:text-white">3. Launch the app:</p>
        <p className="text-xs text-slate-500">
          Launch by clicking <strong>Photo Face Organizer</strong> in your desktop application menu or by typing in terminal:
        </p>
        <CommandBlock command="photo-face-organizer" language="bash" />

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-6">
          Method 2: Command-Line Installation via Pip / Pipx
        </h2>
        <p>
          Recommended for Arch, Fedora, openSUSE, or any Linux distribution with Python 3.10+ installed.
        </p>

        <CommandBlock
          command="pipx install git+https://github.com/technoharsh21/photo-face-organizer.git"
          language="bash"
        />

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-6">
          Updating &amp; Uninstalling
        </h2>

        <p className="font-semibold text-slate-900 dark:text-white">To Update:</p>
        <p className="text-xs text-slate-500">
          Download the latest <code>.deb</code> package and run <code>sudo dpkg -i {debFilename}</code>.
        </p>

        <p className="font-semibold text-slate-900 dark:text-white pt-2">To Uninstall:</p>
        <CommandBlock command="sudo dpkg -r photo-face-organizer" language="bash" />
      </div>
    </div>
  );
}
