import { ContactForm } from "@/components/ContactForm";
import { Mail, MessageSquare, ShieldCheck, Github } from "lucide-react";

export const metadata = {
  title: "Contact Us | Photo Face Organizer",
  description: "Get in touch with the Photo Face Organizer team for support, feature requests, or privacy inquiries.",
};

export default function ContactPage() {
  const repoUrl = process.env.NEXT_PUBLIC_GITHUB_REPO
    ? `https://github.com/${process.env.NEXT_PUBLIC_GITHUB_REPO}`
    : "https://github.com/technoharsh21/photo-face-organizer";

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 space-y-12">
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white">
          Contact Us
        </h1>
        <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg">
          Have a question, feedback, or need help with setup? Send us a message and our team will get back to you.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Side Info */}
        <div className="space-y-6 lg:col-span-1">
          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="p-3 rounded-xl bg-brand-50 dark:bg-brand-950/60 text-brand-600 w-fit">
              <Mail className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Direct Contact</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Use the contact form to reach out directly regarding feature suggestions, technical support, or installation help.
            </p>
          </div>

          <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
            <div className="p-3 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 w-fit">
              <Github className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-bold text-slate-900 dark:text-white">Open Source Community</h3>
            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              Found a bug or want to contribute code? You can open an Issue or submit a Pull Request on GitHub.
            </p>
            <a
              href={repoUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-600 hover:underline"
            >
              <span>Visit GitHub Repository &rarr;</span>
            </a>
          </div>

          <div className="p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-emerald-900 dark:text-emerald-200 space-y-2 text-xs">
            <div className="flex items-center gap-2 font-bold text-sm">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Privacy Guaranteed</span>
            </div>
            <p className="leading-relaxed text-slate-600 dark:text-slate-300">
              We never share your contact details or email address with third parties.
            </p>
          </div>
        </div>

        {/* Form Column */}
        <div className="lg:col-span-2">
          <ContactForm />
        </div>
      </div>
    </div>
  );
}
