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

    // 5. Environment check and smart SMTP resolution
    const smtpUser = process.env.SMTP_USER;
    const smtpPass = process.env.SMTP_PASSWORD;
    let smtpHost = process.env.SMTP_HOST;
    let smtpPort = Number(process.env.SMTP_PORT) || 587;
    let smtpSecure = smtpPort === 465;

    // Automatic SMTP host inference if not explicitly provided
    if (!smtpHost && smtpUser) {
      const lowerUser = smtpUser.toLowerCase();
      if (lowerUser.includes("@gmail.com") || lowerUser.includes("@googlemail.com")) {
        smtpHost = "smtp.gmail.com";
        smtpPort = 587;
        smtpSecure = false;
      } else if (
        lowerUser.includes("@outlook.com") ||
        lowerUser.includes("@hotmail.com") ||
        lowerUser.includes("@live.com") ||
        lowerUser.includes("@office365.com")
      ) {
        smtpHost = "smtp.office365.com";
        smtpPort = 587;
        smtpSecure = false;
      } else if (lowerUser.includes("@yahoo.com")) {
        smtpHost = "smtp.mail.yahoo.com";
        smtpPort = 465;
        smtpSecure = true;
      } else if (lowerUser.includes("@icloud.com")) {
        smtpHost = "smtp.mail.me.com";
        smtpPort = 587;
        smtpSecure = false;
      }
    }

    const contactEmail = process.env.CONTACT_EMAIL || smtpUser;

    if (!smtpHost || !smtpUser || !smtpPass) {
      console.warn("SMTP configuration is missing or incomplete on server (SMTP_USER/SMTP_PASSWORD required).");
      return NextResponse.json(
        { error: "We couldn't send your message right now. Please try again later." },
        { status: 503 }
      );
    }

    // 6. Transporter creation
    const transporter = nodemailer.createTransport({
      host: smtpHost,
      port: smtpPort,
      secure: smtpSecure,
      auth: {
        user: smtpUser,
        pass: smtpPass,
      },
    });

    // 7. Send message to recipient / admin inbox
    await transporter.sendMail({
      from: `"${name}" <${smtpUser}>`,
      replyTo: email,
      to: contactEmail,
      subject: `[Photo Face Organizer Contact] ${subject}`,
      text: `Name: ${name}\nEmail: ${email}\nSubject: ${subject}\n\nMessage:\n${message}`,
      html: `
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 24px;">
          <div style="background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 24px; max-width: 600px; margin: 0 auto;">
            <div style="display: inline-block; background-color: #0284c7; color: #ffffff; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; text-transform: uppercase; margin-bottom: 12px;">
              Incoming Website Contact
            </div>
            <h2 style="color: #38bdf8; margin: 0 0 16px 0; font-size: 20px;">New Message from ${name}</h2>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 16px;">
              <tr>
                <td style="padding: 6px 0; color: #94a3b8; width: 90px; font-weight: 600;">Sender:</td>
                <td style="color: #f8fafc;">${name} &lt;<a href="mailto:${email}" style="color: #38bdf8;">${email}</a>&gt;</td>
              </tr>
              <tr>
                <td style="padding: 6px 0; color: #94a3b8; font-weight: 600;">Subject:</td>
                <td style="color: #f8fafc; font-weight: 600;">${subject}</td>
              </tr>
            </table>
            <hr style="border: none; border-top: 1px solid #1f2937; margin: 14px 0;" />
            <p style="color: #94a3b8; margin: 0 0 8px 0; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Message Content:</p>
            <div style="background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 14px; color: #e2e8f0; font-size: 13px; line-height: 1.6; white-space: pre-wrap;">${message}</div>
          </div>
        </div>
      `,
    });

    // 8. Send automated confirmation receipt back to visitor's email
    try {
      await transporter.sendMail({
        from: `"Photo Face Organizer" <${smtpUser}>`,
        to: email,
        subject: `Receipt: We received your message regarding "${subject}"`,
        text: `Hi ${name},\n\nThank you for reaching out! We have received your inquiry regarding "${subject}" and our team will get back to you soon.\n\nSummary of your message:\n${message}\n\nBest regards,\nPhoto Face Organizer Team`,
        html: `
          <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0b0f19; color: #f8fafc; padding: 24px;">
            <div style="background-color: #111827; border: 1px solid #1f2937; border-radius: 12px; padding: 24px; max-width: 580px; margin: 0 auto;">
              <div style="display: inline-block; background-color: #064e3b; color: #34d399; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; border: 1px solid #10b981; margin-bottom: 14px;">
                RECEIPT CONFIRMATION
              </div>
              <h2 style="color: #ffffff; margin: 0 0 8px 0; font-size: 20px;">We Received Your Message</h2>
              <p style="color: #94a3b8; font-size: 13px; line-height: 1.6; margin: 0 0 18px 0;">
                Hi <strong>${name}</strong>,<br/><br/>
                Thank you for contacting Photo Face Organizer. We have received your inquiry and our team will get back to you as soon as possible.
              </p>
              <div style="background-color: #0b0f19; border: 1px solid #1e293b; border-radius: 8px; padding: 16px; margin: 16px 0;">
                <p style="margin: 0 0 6px 0; font-size: 11px; color: #38bdf8; font-weight: 700; text-transform: uppercase;">Submitted Subject:</p>
                <p style="margin: 0 0 14px 0; color: #ffffff; font-size: 13px; font-weight: 600;">${subject}</p>
                <p style="margin: 0 0 6px 0; font-size: 11px; color: #38bdf8; font-weight: 700; text-transform: uppercase;">Your Message:</p>
                <p style="margin: 0; color: #cbd5e1; font-size: 13px; line-height: 1.6; white-space: pre-wrap;">${message}</p>
              </div>
              <p style="font-size: 11px; color: #64748b; border-top: 1px solid #1f2937; padding-top: 14px; margin-top: 18px; text-align: center;">
                This is an automated confirmation receipt from Photo Face Organizer.
              </p>
            </div>
          </div>
        `,
      });
    } catch (receiptErr) {
      console.warn("Could not send automated receipt email to visitor:", receiptErr);
    }

    return NextResponse.json({ success: true, message: "Your message has been sent successfully." });
  } catch (error) {
    console.error("Unhandled error in /api/contact:", error);
    return NextResponse.json(
      { error: "We couldn't send your message right now. Please try again later." },
      { status: 500 }
    );
  }
}
