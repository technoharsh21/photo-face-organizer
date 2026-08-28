import Link from "next/link";
import { getLatestRelease } from "@/data/releases";

export const metadata = {
  title: "Windows Installation Guide (.exe) | Photo Face Organizer Docs",
  description: "Complete setup guide for Windows 10 and Windows 11 (64-bit).",
};

export default function WindowsInstallationPage() {
  const latestRelease = getLatestRelease();
  const winAsset = latestRelease.assets.windows.find((a) => a.type === "exe");
  const winFilename = winAsset ? winAsset.filename : "PhotoFaceOrganizer_Setup.exe";

  return (
    <div className="space-y-8 text-slate-700 dark:text-slate-300">
      <div className="border-b border-slate-200 dark:border-slate-800 pb-6 space-y-2">
        <span className="text-xs font-semibold text-brand-600 dark:text-brand-400 uppercase tracking-wider">
          Installation &rsaquo; Windows
        </span>
        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          Windows Installation Guide
        </h1>
        <p className="text-sm text-slate-500">
          Setup wizard instructions for Windows 10 and 11 (64-bit).
        </p>
      </div>

      <div className="space-y-6 text-sm leading-relaxed">
        <h2 className="text-xl font-bold text-slate-900 dark:text-white">
          Installing via Inno Setup Executable ({winFilename})
        </h2>

        <ol className="list-decimal list-inside space-y-3 font-medium text-slate-800 dark:text-slate-200">
          <li>
            <strong>Download Installer:</strong> Download <code>{winFilename}</code> from our <Link href="/download" className="text-brand-600 underline">Download Page</Link>.
          </li>
          <li>
            <strong>Run Installer:</strong> Double-click <code>{winFilename}</code> to launch the Windows Setup Wizard.
          </li>
          <li>
            <strong>SmartScreen Security Notice:</strong> If Windows Defender SmartScreen displays a warning, click <em>&quot;More info&quot;</em> and select <em>&quot;Run anyway&quot;</em>.
          </li>
          <li>
            <strong>Complete Installation:</strong> Choose your install path (default: <code>C:\Program Files\Photo Face Organizer</code>) and check &quot;Create a desktop shortcut&quot;.
          </li>
          <li>
            <strong>Launch App:</strong> Double-click the <strong>Photo Face Organizer</strong> desktop shortcut or find it in your Start Menu.
          </li>
        </ol>

        <h2 className="text-xl font-bold text-slate-900 dark:text-white pt-4">
          Updating &amp; Uninstalling on Windows
        </h2>

        <p className="font-semibold text-slate-900 dark:text-white">To Update:</p>
        <p className="text-xs text-slate-500">
          Download the latest <code>{winFilename}</code> setup wizard and run it over your existing installation.
        </p>

        <p className="font-semibold text-slate-900 dark:text-white pt-2">To Uninstall:</p>
        <p className="text-xs text-slate-500">
          Open <strong>Windows Control Panel &rsaquo; Add or Remove Programs</strong>, select <strong>Photo Face Organizer</strong>, and click <strong>Uninstall</strong>.
        </p>
      </div>
    </div>
  );
}
