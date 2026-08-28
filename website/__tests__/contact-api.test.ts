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
});
