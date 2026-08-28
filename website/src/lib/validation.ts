import { z } from "zod";

export const contactFormSchema = z.object({
  name: z
    .string()
    .min(2, "Name must be at least 2 characters")
    .max(100, "Name cannot exceed 100 characters")
    .trim(),
  email: z
    .string()
    .email("Please enter a valid email address")
    .max(150, "Email cannot exceed 150 characters")
    .trim(),
  subject: z
    .string()
    .min(3, "Subject must be at least 3 characters")
    .max(150, "Subject cannot exceed 150 characters")
    .trim(),
  message: z
    .string()
    .min(10, "Message must be at least 10 characters long")
    .max(3000, "Message cannot exceed 3000 characters")
    .trim(),
  honeypot: z.string().max(0, "Spam detected").optional(),
});

export type ContactFormData = z.infer<typeof contactFormSchema>;
