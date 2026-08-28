import { contactFormSchema } from "../src/lib/validation";

describe("Contact Form Validation (Zod)", () => {
  test("validates clean contact form submission", () => {
    const validData = {
      name: "Jane Doe",
      email: "jane@example.com",
      subject: "Question about Group Profiles",
      message: "Hello, I would like to know more about compulsory group profile matching.",
      honeypot: "",
    };

    const result = contactFormSchema.safeParse(validData);
    expect(result.success).toBe(true);
  });

  test("fails when email is invalid", () => {
    const invalidEmail = {
      name: "Jane Doe",
      email: "invalid-email-address",
      subject: "Subject",
      message: "This is a test message.",
      honeypot: "",
    };

    const result = contactFormSchema.safeParse(invalidEmail);
    expect(result.success).toBe(false);
  });

  test("fails when message is too short", () => {
    const shortMsg = {
      name: "Jane Doe",
      email: "jane@example.com",
      subject: "Subject",
      message: "Short",
      honeypot: "",
    };

    const result = contactFormSchema.safeParse(shortMsg);
    expect(result.success).toBe(false);
  });

  test("fails when honeypot field is filled by bot", () => {
    const botSubmission = {
      name: "Spam Bot",
      email: "bot@spam.com",
      subject: "Buy cheap products",
      message: "This is spam message content.",
      honeypot: "http://spam.link",
    };

    const result = contactFormSchema.safeParse(botSubmission);
    expect(result.success).toBe(false);
  });
});
