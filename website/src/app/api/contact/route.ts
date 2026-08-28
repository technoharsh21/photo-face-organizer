import { NextResponse } from "next/server";
import nodemailer from "nodemailer";
import { contactFormSchema } from "@/lib/validation";
import { checkRateLimit } from "@/lib/rate-limit";

export async function POST(req: Request) {
  try {
    // 1. IP Rate Limiting
    const ip = req.headers.get("x-forwarded-for") || "127.0.0.1";
    const isAllowed = checkRateLimit(ip, 5, 60 * 1000); // 5 requests per minute

    if (!isAllowed) {
      return NextResponse.json(
        { error: "Too many requests. Please wait a minute before sending another message." },
        { status: 429 }
      );
    }

    // 2. Request body JSON parsing
    const body = await req.json();

    // 3. Validation with Zod
    const validation = contactFormSchema.safeParse(body);

    if (!validation.success) {
      return NextResponse.json(
        { error: "Invalid form input. Please check the fields and try again." },
        { status: 400 }
      );
    }

    const { name, email, subject, message, honeypot } = validation.data;

    // 4. Honeypot check (Spam protection)
    if (honeypot && honeypot.length > 0) {
      // Quietly reject bots with 200 OK
      return NextResponse.json({ success: true, message: "Message sent" });
    }

    // 5. Environment check for Nodemailer
    const smtpHost = process.env.SMTP_HOST;
    const smtpPort = process.env.SMTP_PORT;
    const smtpUser = process.env.SMTP_USER;
    const smtpPass = process.env.SMTP_PASSWORD;
    const contactEmail = process.env.CONTACT_EMAIL || smtpUser;

    if (!smtpHost || !smtpUser || !smtpPass) {
      console.warn("SMTP configuration is missing or incomplete on server.");
      return NextResponse.json(
        { error: "We couldn't send your message right now. Please try again later." },
        { status: 503 }
      );
    }

    // 6. Transporter creation & sending
    const transporter = nodemailer.createTransport({
      host: smtpHost,
      port: Number(smtpPort) || 587,
      secure: Number(smtpPort) === 465,
      auth: {
        user: smtpUser,
        pass: smtpPass,
      },
    });

    await transporter.sendMail({
      from: `"${name}" <${smtpUser}>`,
      replyTo: email,
      to: contactEmail,
      subject: `[Photo Face Organizer Contact] ${subject}`,
      text: `Name: ${name}\nEmail: ${email}\nSubject: ${subject}\n\nMessage:\n${message}`,
      html: `
        <h3>New Contact Message from Photo Face Organizer Website</h3>
        <p><strong>Name:</strong> ${name}</p>
        <p><strong>Email:</strong> ${email}</p>
        <p><strong>Subject:</strong> ${subject}</p>
        <hr />
        <p><strong>Message:</strong></p>
        <p style="white-space: pre-wrap;">${message}</p>
      `,
    });

    return NextResponse.json({ success: true, message: "Your message has been sent successfully." });
  } catch (error) {
    console.error("Unhandled error in /api/contact:", error);
    return NextResponse.json(
      { error: "We couldn't send your message right now. Please try again later." },
      { status: 500 }
    );
  }
}
