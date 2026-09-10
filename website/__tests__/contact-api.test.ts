import { POST } from "../src/app/api/contact/route";

describe("Contact API Route Handler", () => {
  test("returns 400 Bad Request when JSON body is invalid", async () => {
    const req = new Request("http://localhost:3000/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "",
        email: "invalid",
      }),
    });

    const res = await POST(req);
    expect(res.status).toBe(400);

    const json = await res.json();
    expect(json.error).toBeDefined();
  });

  test("returns 503 Service Unavailable gracefully when SMTP credentials are not configured", async () => {
    delete process.env.SMTP_HOST;
    delete process.env.SMTP_USER;
    delete process.env.SMTP_PASSWORD;

    const req = new Request("http://localhost:3000/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Test User",
        email: "user@example.com",
        subject: "General Question",
        message: "This is a valid test message.",
        honeypot: "",
      }),
    });

    const res = await POST(req);
    expect(res.status).toBe(503);

    const json = await res.json();
    expect(json.error).toBe("We couldn't send your message right now. Please try again later.");
  });

  test("successfully sends email and confirmation receipt when SMTP credentials are provided", async () => {
    process.env.SMTP_USER = "support@gmail.com";
    process.env.SMTP_PASSWORD = "secret-app-password";

    const req = new Request("http://localhost:3000/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "Alice",
        email: "alice@example.com",
        subject: "Feature Request",
        message: "Can we add cloud sync?",
        honeypot: "",
      }),
    });

    // Mock nodemailer createTransport
    const nodemailer = require("nodemailer");
    const sendMailMock = jest.fn().mockResolvedValue({ messageId: "123" });
    jest.spyOn(nodemailer, "createTransport").mockReturnValue({
      sendMail: sendMailMock,
    } as any);

    const res = await POST(req);
    expect(res.status).toBe(200);

    const json = await res.json();
    expect(json.success).toBe(true);

    // Verify both admin message and receipt confirmation were sent
    expect(sendMailMock).toHaveBeenCalledTimes(2);

    delete process.env.SMTP_USER;
    delete process.env.SMTP_PASSWORD;
  });
});
